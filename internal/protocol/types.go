package protocol

type AgentProfile struct {
	Name               string            `json:"name"`
	URL                string            `json:"url"`
	Token              string            `json:"token"`
	DefaultWorkspace   string            `json:"default_workspace,omitempty"`
	NamedPortForwards  map[string]string `json:"named_port_forwards,omitempty"`
	InsecureSkipVerify bool              `json:"insecure_skip_verify,omitempty"`
}

type APIError struct {
	Code    string `json:"code"`
	Message string `json:"message"`
}
