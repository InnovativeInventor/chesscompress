cd fastchess
python proc.py '/Volumes/Cabinet/games/lichess*.pgn' -test proc.test -train proc.train

fasttext supervised -input proc.train -output proc.model -t 0 -neg 0 -epoch 1
fasttext test proc.model.bin proc.test 1

cd ..
