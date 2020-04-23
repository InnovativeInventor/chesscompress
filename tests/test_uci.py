from chesscompress import uci, learn
import chess

def test_predict_default():
    with uci.Uci() as predictor:
        moves = predictor.predict()

    print(moves)

    assert moves

# def test_uci():
    # engine = uci.Uci()
    # assert engine
    # engine.engine.close()

def test_pdf():
    with uci.Uci() as predictor:
        benchmarker = learn.Learn()
        for each_game in benchmarker.get_game(n=1):
            prediction = predictor.predict(chess.STARTING_FEN)
            for counter, game in enumerate(each_game.mainline()):
                assert is_pdf(prediction)
                prediction = predictor.predict(game.board().fen())


def is_pdf(prediction):
    """
    Checks if predictions add up to 1 (they must!)
    """
    probs = [y for x, y in prediction.items()]

    distance = 1 - sum(probs) 
    assert distance >= -0.001 
    if distance >= -0.001 and distance < 1:
        return True
    
# test_moves_default()
# test_pdf()
