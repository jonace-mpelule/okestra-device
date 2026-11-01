package client

import (
	"errors"
	"flag"
	"fmt"
	"github.com/jonace-mpelule/okestra-device/internal/protocol"
	"io"
	"net/url"
	"os"
	"strings"
)

func runAgentCommands(cfgPath string, cfg *Config, args []string, stdout, stderr io.Writer) int {
	if len(args) == 0 {
		fmt.Fprintln(stderr, "Usage: okestra-device server <add|use|list|remove>")
		return 1
	}
	switch args[0] {
	case "add":
		fs := flag.NewFlagSet("server add", flag.ContinueOnError)
		fs.SetOutput(stderr)
		var name, endpoint, token, workspace string
		var insecureSkipVerify bool
		fs.StringVar(&name, "name", "", "profile name")
		fs.StringVar(&endpoint, "url", "", "Okestra endpoint URL")
		fs.StringVar(&token, "token", "", "service access token")
		fs.StringVar(&workspace, "workspace", "", "default remote workspace root")
		fs.BoolVar(&insecureSkipVerify, "insecure-skip-verify", false, "allow a self-signed HTTPS certificate")
		if err := fs.Parse(args[1:]); err != nil {
			return 1
		}
		if token == "" {
			token = os.Getenv("OKESTRA_DEVICE_TOKEN")
		}
		if name == "" || endpoint == "" || token == "" {
			fmt.Fprintln(stderr, "--name, --url and --token are required (token may also use OKESTRA_DEVICE_TOKEN)")
			return 1
		}
		endpoint, err := validateEndpointURL(endpoint)
		if err != nil {
			fmt.Fprintf(stderr, "invalid server URL: %v\n", err)
			return 1
		}
		if len(token) < 32 {
			fmt.Fprintln(stderr, "token must be at least 32 characters")
			return 1
		}
		cfg.Agents[name] = protocol.AgentProfile{Name: name, URL: endpoint, Token: token, DefaultWorkspace: workspace, InsecureSkipVerify: insecureSkipVerify}
		if cfg.ActiveAgent == "" {
			cfg.ActiveAgent = name
		}
		if err := SaveConfig(cfgPath, cfg); err != nil {
			fmt.Fprintf(stderr, "save config: %v\n", err)
			return 1
		}
		fmt.Fprintf(stdout, "Server %s added (%s).\n", name, endpoint)
		if strings.HasPrefix(endpoint, "http://") {
			fmt.Fprintln(stderr, "Warning: Use HTTP only on an encrypted or otherwise trusted private network.")
		}
		return 0
	case "use":
		if len(args) < 2 {
			fmt.Fprintln(stderr, "Usage: okestra-device server use <name>")
			return 1
		}
		if _, ok := cfg.Agents[args[1]]; !ok {
			fmt.Fprintf(stderr, "Server %s was not found.\n", args[1])
			return 1
		}
		cfg.ActiveAgent = args[1]
		if err := SaveConfig(cfgPath, cfg); err != nil {
			fmt.Fprintf(stderr, "save config: %v\n", err)
			return 1
		}
		fmt.Fprintf(stdout, "Active server set to %s.\n", args[1])
		return 0
	case "list":
		for name, agent := range cfg.Agents {
			active := ""
			if cfg.ActiveAgent == name {
				active = " *"
			}
			fmt.Fprintf(stdout, "%s\t%s%s\n", name, agent.URL, active)
		}
		return 0
	case "remove":
		if len(args) != 2 {
			fmt.Fprintln(stderr, "Usage: okestra-device server remove <name>")
			return 1
		}
		if _, ok := cfg.Agents[args[1]]; !ok {
			fmt.Fprintf(stderr, "server %s not found\n", args[1])
			return 1
		}
		delete(cfg.Agents, args[1])
		if cfg.ActiveAgent == args[1] {
			cfg.ActiveAgent = ""
		}
		if err := SaveConfig(cfgPath, cfg); err != nil {
			fmt.Fprintf(stderr, "save config: %v\n", err)
			return 1
		}
		fmt.Fprintf(stdout, "Server %s removed.\n", args[1])
		return 0
	default:
		fmt.Fprintln(stderr, "Usage: okestra-device server <add|use|list|remove>")
		return 1
	}
}

func activeAPI(cfg *Config, stderr io.Writer) (protocol.AgentProfile, *API, bool) {
	profile, err := cfg.ActiveProfile()
	if err != nil {
		fmt.Fprintf(stderr, "active agent: %v\n", err)
		return protocol.AgentProfile{}, nil, false
	}
	return profile, NewAPI(profile), true
}

func validateEndpointURL(raw string) (string, error) {
	u, err := url.Parse(strings.TrimSpace(raw))
	if err != nil {
		return "", err
	}
	if u.Scheme != "http" && u.Scheme != "https" {
		return "", errors.New("scheme must be http or https")
	}
	if u.Host == "" {
		return "", errors.New("host is required")
	}
	if u.User != nil || u.RawQuery != "" || u.Fragment != "" || (u.Path != "" && u.Path != "/") {
		return "", errors.New("URL must not contain credentials, a path, query, or fragment")
	}
	u.Path = ""
	return strings.TrimRight(u.String(), "/"), nil
}
