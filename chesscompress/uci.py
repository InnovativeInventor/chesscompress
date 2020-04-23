import chess
import hashlib
# from diskcache import Cache
# from joblib import Memory
import chess.engine
import pickle
import os

class Uci:
    """
    Implements the UCI wrapper for consumption by benchmark.py using Stockfish
    """
    def __init__(self, loc="/usr/local/bin/stockfish", depth = 5, limit = 0.1, cache_loc="/Volumes/Cabinet/cache/stockfish-3-cache/"):
    # def __init__(self, loc="/usr/local/bin/stockfish", depth = 15, limit = 0.5):
        """
        Args:
            loc - the location of the stockfish executable
            limit - the default limit of the engine, in seconds
        """
        self.loc = loc
        self.cache_loc = cache_loc 
        # Note: for a big batch conversion, try LRU

        self.limit = limit
        self.depth = depth
        self.mate_score = 1010101 # unlikely for stockfish to produce, janky solution
        self.floor = 0.001

        self.engine = chess.engine.SimpleEngine.popen_uci(self.loc)


        # memory = Memory(cache_loc, verbose=1)
        # self.analyze = memory.cache(self.analyze, ignore=['self'])

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.engine.close()

    # def predict(self, fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", huffman=False):
        # """
        # Smartly caches self.moves's output using joblib.Memory
        # """
        # prediction = self.memory.cache(self.moves)
        # return prediction(fen=fen, huffman=huffman)

    def save_cache(self, args, output):
        filename = self.cache_loc + hashlib.sha256(str(args).encode()).hexdigest() + ".pickle"
        with open(filename, "wb") as c:
            c.write(pickle.dumps(output))

    def get_cache(self, args):
        filename = self.cache_loc + hashlib.sha256(str(args).encode()).hexdigest() + ".pickle"
        if os.path.isfile(filename):
            with open(filename, "rb") as f:
                result = pickle.load(f)
                return result
        return False


    def analyze(self, fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", huffman=False) -> list:
        """
        Generates a normalized ordering of the most likely moves

        Args:
            fen - the board state in FEN notation

        Returns:
            (legal_moves, move_results)
        """
        # if result := self.get_cache((str(fen), huffman)):
            # return result

        board = chess.Board(fen) # setup board

        # Getting and iterating through legal moves
        move_results = []
        for each_move in board.legal_moves:
            analysis_results = self.engine.analyse(board, chess.engine.Limit(depth=self.depth, time=self.limit))
            if analysis_results and analysis_results.score:
                # move_results.append(analysis_results.score.white().score(mate_score = self.mate_score))
                move_results.append(analysis_results.score.relative.score(mate_score = self.mate_score))

        # self.save_cache((str(fen), huffman), (board.legal_moves, move_results))
        # print(board.legal_moves, move_results)
        return board.legal_moves, move_results

    def predict(self, fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", huffman=False):
        legal_moves, move_results = self.analyze(fen=fen, huffman=huffman)
        move_shifted = [move + self.floor - min(move_results) for move in move_results] # shift up, no negatives
        move_total = sum(move_shifted) # for normalizing

        if move_total:
            moves = dict(zip(legal_moves, [move/move_total for move in move_shifted])) # combine 
        else:
            moves = dict(zip(legal_moves, move_shifted)) # combine 

        # Credit: sorting from StackOverflow: https://stackoverflow.com/questions/613183/how-do-i-sort-a-dictionary-by-value
        if huffman:
            moves_sorted = sorted(moves.items(), key=lambda x: x[1], reverse=True)
            moves_huffman = dict([(move, pow(0.5, count+1)) for count, (move, _) in enumerate(moves_sorted)])
            return moves_huffman

        else:
            moves_sorted = dict(sorted(moves.items(), key=lambda x: x[1], reverse=True))
            return moves_sorted

        # TODO: Optimize speed

