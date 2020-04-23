from chesscompress import learn 

def test_get_datasets():
    file_list = learn.Learn().get_datasets()

    assert file_list
    assert len(file_list) > 0

def test_get_game():
    game_list = learn.Learn().get_game(n=1)

    for count, game in enumerate(game_list):
        assert game
        print(count, game)

    assert game_list
    assert count > 0

# def test_iter_moves():
    # results = benchmark.Benchmark().evaluate(n=1)
    # print(results)

# test_iter_moves()
