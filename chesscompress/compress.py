from chesscompress import learn, uci

"""
NotImplemented
"""

class Compress(learn.Learn):
    def __init__(self, loc="/Volumes/Cabinet/games/", Evaluator=uci.Uci, cache_loc="./cache/"): 
        self.loc = loc
        self.cache_loc = cache_loc
        self.Evaluator = Evaluator

        self._recursion_limit = 25000
        sys.setrecursionlimit(self._recursion_limit)

    def compress(self):
        pass
