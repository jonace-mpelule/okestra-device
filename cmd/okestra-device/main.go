package main

import (
	"github.com/jonace-mpelule/okestra-device/internal/client"
	"os"
)

func main() { os.Exit(client.RunCLI(os.Args[1:], os.Stdout, os.Stderr)) }
