## ChessCompress
[![codecov](https://codecov.io/gh/InnovativeInventor/chesscompress/branch/master/graph/badge.svg)](https://codecov.io/gh/InnovativeInventor/chesscompress)

ChessCompress uses novel, hopefully better than state-of-the-art chess compression techniques to provide an efficient way to store chess games.

**Note:** This code is slow, but could be sped up by implementing the same techniques in a faster language.

## Benchmarks
To calculate the theoretical entropy rate, I averaged the Shannon information of each move in the dataset using each prediction function, assuming that the prediction function is perfect. The entropy of each move $x$, given a prediction function p that spits out the probability of the move, is defined as:

$-log_2(p(x))$

Note that we assume that the function p is a probability mass function. The data used consists of the first 10000 Lichess games played in the year 2018.

This allows us to figure out our maximum compression rate (bits/move).

To reproduce these stats, run:
```bash
python3 stats.py
```

## Testing
There are tests written for most of the important functions/classes.

## TODO
- [ ] better markup of README and more formal language
- [ ] better explanation of calculations

## See also
https://lichess.org/blog/Wqa7GiAAAOIpBLoY/developer-update-275-improved-game-compression (previous state of the art)
