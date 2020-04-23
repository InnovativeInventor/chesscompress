from chesscompress import learn

if __name__ == '__main__':
    tepid = 0.01

    benchmarker = learn.Learn(tepid=tepid)

    print("Printing average bitrate per move:")
    entropy, avg, stdev = benchmarker.evaluate(n=100)

    print("Tepid", tepid)
    print("Entropy", entropy)
    print("Avg", avg)
    print("Stdev", stdev)

