package client

import (
	"context"
	"fmt"
	"github.com/jonace-mpelule/okestra-device/internal/updater"
	"github.com/jonace-mpelule/okestra-device/internal/version"
	"io"
	"os"
	"os/signal"
	"syscall"
)

func RunCLI(args []string, out, errOut io.Writer) int {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	cfgPath := DefaultConfigPath()
	cfg, e := LoadConfig(cfgPath)
	if e != nil {
		fmt.Fprintln(errOut, e)
		return 1
	}
	if len(args) == 0 {
		fmt.Fprintln(out, "Usage: okestra-device <android|server|config|version>")
		return 0
	}
	switch args[0] {
	case "upgrade", "update":
		if len(args) > 2 || (len(args) == 2 && args[1] != "--check") {
			fmt.Fprintln(errOut, "Usage: okestra-device upgrade [--check]")
			return 1
		}
		if e := updater.Upgrade(ctx, "okestra-device", len(args) == 2, out); e != nil {
			fmt.Fprintln(errOut, e)
			return 1
		}
		return 0
	case "android":
		return runAndroid(ctx, cfg, args[1:], out, errOut)
	case "server":
		return runAgentCommands(cfgPath, cfg, args[1:], out, errOut)
	case "version":
		fmt.Fprintln(out, "okestra-device", version.Version)
		return 0
	case "config":
		if len(args) == 2 && args[1] == "path" {
			fmt.Fprintln(out, cfgPath)
			return 0
		}
	}
	fmt.Fprintln(errOut, "Unknown command:", args[0])
	return 1
}
