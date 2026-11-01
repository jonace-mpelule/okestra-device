package client

import (
	"encoding/json"
	"io"
	"net"
	"time"
)

type forwardStatus struct {
	Project  string   `json:"project"`
	Endpoint string   `json:"endpoint"`
	Ports    []string `json:"ports"`
	PID      int      `json:"pid"`
}

func queryForward(socket, command string) (forwardStatus, error) {
	conn, err := net.DialTimeout("unix", socket, 500*time.Millisecond)
	if err != nil {
		return forwardStatus{}, err
	}
	defer conn.Close()
	_ = conn.SetDeadline(time.Now().Add(time.Second))
	if _, err := io.WriteString(conn, command+"\n"); err != nil {
		return forwardStatus{}, err
	}
	var status forwardStatus
	if err := json.NewDecoder(conn).Decode(&status); err != nil {
		return forwardStatus{}, err
	}
	return status, nil
}
