package main

import "fmt"
import "path/filepath"
import "bufio"
import "os"
import "github.com/notnil/chess"

func main() {
	location := "/Volumes/Cabinet/games/"
	pgns, err := filepath.Glob(location + "*.pgn")
	if err != nil {
		fmt.Println("Error!")
		fmt.Println(err)
	}

	for _, pgnloc := range pgns {
		/*fmt.Println(pgn)*/
		f, err := os.Open(pgnloc)
		if err != nil {
			fmt.Println("Error!")
			fmt.Println(err)
			continue
		}
		pgnreader, err := chess.PGN(f)
		game := chess.NewGame(pgnreader)
		fmt.Println(pgn, game.Moves())
		f.Close()
	}

}
