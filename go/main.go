package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strconv"
)

type addRequest struct {
	A int64 `json:"a"`
	B int64 `json:"b"`
}

type addResponse struct {
	Result int64 `json:"result"`
}

func main() {
	a, b, err := operands(os.Args[1:])
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}

	baseURL := os.Getenv("API_URL")
	if baseURL == "" {
		baseURL = "http://localhost:3000"
	}

	payload, err := json.Marshal(addRequest{A: a, B: b})
	if err != nil {
		fatal(err)
	}

	response, err := http.Post(baseURL+"/add", "application/json", bytes.NewReader(payload))
	if err != nil {
		fatal(err)
	}
	defer response.Body.Close()

	if response.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(response.Body)
		fatal(fmt.Errorf("server returned %s: %s", response.Status, bytes.TrimSpace(body)))
	}

	var result addResponse
	if err := json.NewDecoder(response.Body).Decode(&result); err != nil {
		fatal(err)
	}
	fmt.Println(result.Result)
}

func operands(args []string) (int64, int64, error) {
	if len(args) == 0 {
		return 1, 2, nil
	}
	if len(args) != 2 {
		return 0, 0, fmt.Errorf("usage: go run . [a b]")
	}

	a, err := strconv.ParseInt(args[0], 10, 64)
	if err != nil {
		return 0, 0, fmt.Errorf("invalid a: %w", err)
	}
	b, err := strconv.ParseInt(args[1], 10, 64)
	if err != nil {
		return 0, 0, fmt.Errorf("invalid b: %w", err)
	}
	return a, b, nil
}

func fatal(err error) {
	fmt.Fprintln(os.Stderr, err)
	os.Exit(1)
}
