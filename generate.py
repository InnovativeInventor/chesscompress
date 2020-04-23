from chesscompress import learn

if __name__ == '__main__':
    benchmarker = learn.Learn()

    # print("Printing average bitrate per move:")
    # print("Done:", benchmarker.evaluate())

    # print("Getting centipawn distribution")
    print("Generating training data")
    benchmarker.generate(n=100000)
    # benchmarker.generate(n=20000)
    # benchmarker.generate(n=8145)
    # benchmarker.generate(n=8100)
    # benchmarker.generate(n=100)
