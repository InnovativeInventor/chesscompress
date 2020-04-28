Teaching FastText to play Chess
===============================

FastChess is a chess engine predicting the next move using the http://fastText.cc text classification library.
In other words, it is a simple one-layer + soft-max model, taking the board state as a vector and outputting a vector of probabilities for each possible move.

The project also contains a Monte Carlo Tree Search, following by Alpha Zero, which combines with the simple linear model to provide a higher quality of play.

You can play against FastChess on Lichess: https://lichess.org/@/fastchess-engine (requires log-in).

Screenshot
==========

![Screenshot](https://raw.githubusercontent.com/thomasahle/fastchess/master/static/screenshot.png)

Run it!
=======

You'll need the following libraries:

    pip install git+https://github.com/facebookresearch/fastText.git
    pip install git+https://github.com/niklasf/python-chess.git
    pip install numpy

Afterwards you can play by

    $ python play_chess.py
    Do you want to be white or black? white
      8 ♜ ♞ ♝ ♛ ♚ ♝ ♞ ♜
      7 ♟ ♟ ♟ ♟ ♟ ♟ ♟ ♟
      6
      5
      4
      3
      2 ♙ ♙ ♙ ♙ ♙ ♙ ♙ ♙
      1 ♖ ♘ ♗ ♕ ♔ ♗ ♘ ♖
        a b c d e f g h

    Your move (e.g. Nf3 or d2d4): e4

To disable MCTS and play directly against the fastText model, add the `-no-mcts` argument.
See `python play_chess.py --help` for more options. 

Train the model
===============

There are two ways to train the model.
The first one is to download a set of pgn files, like http://data.lczero.org/files/ and run

    python proc.py 'cclr/**/*.pgn' -test proc.test -train proc.train
    fasttext supervised -input proc.train -output proc.model -t 0 -neg 0 -epoch 1
    fasttext test proc.model.bin proc.test 1
    mv proc.model.bin model.bin
    python play_chess.py -selfplay

The other way is to generate your own data, e.g. using stockfish.
You can train your own model as:

    python make_data.py -games 1000 | shuf > g1000
    /opt/fastText/fasttext supervised -input g1000 -output model -t 0 -neg 0 -epoch 4

And then run the program as:

    python play_chess.py model.bin

You can also generate more data by self-play (as default games are generated by stockfish)

    python make_data.py -games 1000 -selfplay model.bin > games