package main

import (
	"context"
	"fmt"
	"github.com/jonace-mpelule/okestra-device/internal/agent"
	"github.com/jonace-mpelule/okestra-device/internal/updater"
	"log"
	"os"
	"os/signal"
	"syscall"
)

func main() {
	if len(os.Args) > 1 && (os.Args[1] == "upgrade" || os.Args[1] == "update") {
		if len(os.Args) > 3 || (len(os.Args) == 3 && os.Args[2] != "--check") {
			log.Fatal("usage: okestra-device-service upgrade [--check]")
		}
		if e := updater.Upgrade(context.Background(), "okestra-device-service", len(os.Args) == 3, os.Stdout); e != nil {
			fmt.Fprintln(os.Stderr, e)
			os.Exit(1)
		}
		return
	}

	addr := getenv("OKESTRA_DEVICE_SERVICE_ADDR", getenv("OKESTRA_DEVICE_AGENT_ADDR", "127.0.0.1:8089"))
	token := getenv("OKESTRA_DEVICE_SERVICE_TOKEN", os.Getenv("OKESTRA_DEVICE_AGENT_TOKEN"))
	if token == "" {
		log.Fatal("OKESTRA_DEVICE_SERVICE_TOKEN is required; generate one with: openssl rand -hex 32")
	}
	if len(token) < 32 {
		log.Fatal("OKESTRA_DEVICE_SERVICE_TOKEN must be at least 32 characters")
	}
	workDir := getenv("OKESTRA_DEVICE_SERVICE_WORKDIR", getenv("OKESTRA_DEVICE_AGENT_WORKDIR", "/tmp/okestra-device-service"))
	srv := agent.NewServer(addr, token, workDir)
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	if err := srv.ListenAndServe(ctx); err != nil {
		log.Fatal(err)
	}
}

func getenv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
