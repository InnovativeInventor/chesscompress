import chess
import numpy as np
from tensorflow import keras
import tensorflow as tf
import functools
import hashlib
import sys
from multiprocessing import Pool
import statistics
import pickle
import math
from typing import Iterable
import chess.pgn
from tqdm import tqdm
# from joblib import Memory
import glob
from chesscompress import uci
import os

class Learn:
    """
    Benchmarks a prediction class against the given dataset.

    Usage:
        results = Benchmark(loc)
    """
    # def __init__(self, loc="/Volumes/Cabinet/games/", Evaluator=uci.Uci): 
    def __init__(self, loc="/Volumes/Cabinet/games/", Evaluator=uci.Uci, cache_loc="./cache/", tepid = 0.01): 
        self.loc = loc
        self.tepidness = tepid
        self.cache_loc = cache_loc
        self.Evaluator = Evaluator

        self.size = 64

        self._recursion_limit = 25000
        sys.setrecursionlimit(self._recursion_limit)
        # self.memory = Memory(cache_loc, verbose=3)

    def save_cache(self, args, output):
        filename = self.cache_loc + hashlib.sha256(str(args).encode()).hexdigest() + ".pickle"
        with open(filename, "wb") as c:
            print("Cache saved!")
            c.write(pickle.dumps(output))

    def get_cache(self, args):
        filename = self.cache_loc + hashlib.sha256(str(args).encode()).hexdigest() + ".pickle"
        if os.path.isfile(filename):
            with open(filename, "rb") as f:
                result = pickle.load(f)
                # print(result)
                # if any(result[1][0]):
                    # print("Cache used!")
                return result
        return False

    def combine_reduce(self, a, b):
        # print(a, b)
        # for index, value in enumerate(a):
            # if value:
                # b[index].extend(value)
        # return b
        # print(a,b)
        # if isinstance(a, tuple):
        print(np.array(a).shape, np.array(b).shape)
        if a and b:
            # print("Success")
            return b.extend(a)
        elif a:
            return a
        elif b:
            return b
        return b
        # return b

    # def distribution(self, n=10):
        # """
        # Graphs the distribution
        # """
        # true_probabilities = [] # for debugging
        # false_probabilities = [] # for debugging

        # with Pool(os.cpu_count()) as p:
            # true_probabilities, false_probabilities = functools.reduce(self.combine_reduce, tqdm(p.imap(self.distribution_analyze, self.get_game(n=n)), total=n))

        # with open("models/distribution.pickle", "wb") as f:
            # pickle.dump((true_probabilities, false_probabilities), f)

        # return true_probabilities, false_probabilities
    def generate(self, n=10):
        """
        Generates training data, etc.
        """
        with Pool(os.cpu_count()) as p:
            data = list(tqdm(p.imap(self.analyze_dataset, self.get_game(n=n)), total=n))

        print(len(data))
        with open("models/dataset.pickle", "wb") as f:
            pickle.dump(data, f)

        return data

    def analyze_dataset(self, each_game):
        """
        Analyzer function that will return an analysis of the game along with some metadata
        Returns:
            list of moves - (index_of_move_taken, (legal_moves_evals, rating, win), [moves])
        """
        if precomputed := self.get_cache(each_game.headers.get('Site')):
            return precomputed

        # true_probabilities = [] # for debugging
        # false_probabilities = [] # for debugging

        data = []

        with self.Evaluator() as evaluator:
            white_elo = int(each_game.headers.get("WhiteElo"))
            black_elo = int(each_game.headers.get("BlackElo"))

            game_end = each_game.headers.get("Result")
            if game_end == "0-1":
                game_result = 0
            elif game_end == "1-0":
                game_result = 1
            elif game_end == "1/2-1/2" or game_end == "*":
                game_result = 0.5
            else:
                raise ValueError(game_end)


            legal_moves, move_results = evaluator.analyze(str(chess.STARTING_FEN))
            for counter, game in enumerate(each_game.mainline()):
                if game.board().turn == chess.WHITE:
                    game_mod_result = game_result
                elif game.board().turn == chess.BLACK:
                    game_mod_result = game_result*(-1) + 1
                else:
                    raise ValueError()
                # should assert len(legal_moves) == len(move_results)

                # avg_move = sum(move_results)/len(move_results)
                min_move = min(move_results)
                move_centered = [x - min_move + 0.001 for x in move_results] #  shifted

                total = sum([abs(x) for x in move_centered])
                if not total:
                    total = 1
                    move_results = [1 if x == 1010101 else x/total for x in move_centered] # normalized, except for mates

                index = list(legal_moves).index(game.move) 

                # move_results = [(result, game_end, white_elo, black_elo) for result in move_results]
                # true_probabilities.append(move_results[index])
                # move_results.pop(index)
                # false_probabilities.extend(move_results)
                data.append((index, (move_results, game_mod_result, (black_elo + white_elo)/2)))

                # setup for next move
                legal_moves, move_results = evaluator.analyze(str(game.board().fen()))

        self.save_cache(each_game.headers.get('Site'), data)
        return data
    
    def evaluate(self, n=100):
        """
        Evaluates prediction function according to the dataset. Each prediction function is expected to take two inputs, the board state and the player to move.
        Args:
            n - the number of games to analyze
        """

        entropy = []
        game_counter = 0
        # model.summary()
        # probability_model = keras.Sequential([model, tf.keras.layers.Softmax()])

        with Pool(os.cpu_count()) as p:
            entropy = functools.reduce(self.combine_reduce, tqdm(p.imap(self.evaluate_game, self.get_game(n=n)), total=n))

        return entropy, statistics.mean(entropy), statistics.stdev(entropy)

    def evaluate_game(self, each_game):
        entropy = []
        model = keras.models.load_model("models/no-flip-model.h5")
        model.add(keras.layers.Softmax()) # to normalize
        
        for each_score in self.analyze_dataset(each_game):
            # preparing for consumption
            index = each_score[0]
            data = ([each_score[1][2]/3500]) # roughly normalized avg rating
            move_evals = each_score[1][0]

            data.extend(move_evals)

            if len(data) < self.size:
                data.extend([0]*(self.size-len(data)))

            data_arr = np.array([data[:self.size]])
            # tf.expand_dims(model, axis=-1)

            # prediction = list(model.predict(data_arr))[0]
            prediction = list(model.predict(data_arr)[0])
            if len(data) > self.size:
                prediction.extend([0]*(len(data)-self.size))
            # prediction = prediction / prediction.sum() # TODO: fix normalization

            prediction_filtered = [max(x, self.tepidness) if index <= len(move_evals) + 1 else 0 for index, x in enumerate(prediction)]
            # prediction_filtered = [(x + self.tepidness*5)/6 if index <= len(move_evals) + 1 else 0 for index, x in enumerate(prediction)]
            prediction_normalized = [x/sum(prediction_filtered) for x in prediction_filtered]

            # probabilities.append(prediction[game.move]) # for debugging
            # print(prediction_normalized[index], index, prediction)

            bitrate = -math.log(prediction_normalized[index], 2) # Shannon entropy
            print(bitrate)
            entropy.append(bitrate)

        return entropy
    # def predict(fen, huffman):

        # # Smartly caches
        # self.memory.cache(


    def get_game(self, n=1000) -> Iterable:
        """
        Iterates over each game in the PGN file up to n, the parse limit

        TODO: figure out proper pythonic file reading
        """
        # for each_file in tqdm(self.get_datasets()):
        count = 0
        pgn = True

        for each_file in self.get_datasets():
            # with open(each_file) as f:
            f = open(each_file)
            while pgn and count <= n:
                count += 1

                pgn = chess.pgn.read_game(f)
                if pgn:
                    yield pgn
            f.close()

    def get_datasets(self) -> list:
        results = glob.glob(self.loc + "lichess_db_standard_rated_2018*.pgn")
        return results


