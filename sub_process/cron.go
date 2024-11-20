package main

import (
	"crypto/sha256"
	"fmt"
	"io"
	"net/http"
	"os"
)

func main() {
	url := "https://www.revisor.mn.gov/statutes/cite/245D/full" 
	resp, err := http.Get(url)
	if err != nil {
		fmt.Println("Error fetching website:", err)
		os.Exit(1)
	}
	defer resp.Body.Close()

	hash := sha256.New()
	_, err = io.Copy(hash, resp.Body)
	if err != nil {
		fmt.Println("Error hashing content:", err)
		os.Exit(1)
	}

	hashString := fmt.Sprintf("%x", hash.Sum(nil))
	fmt.Println("Website hash:", hashString)
}
