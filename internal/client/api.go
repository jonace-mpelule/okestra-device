package client

import (
	"bytes"
	"context"
	"crypto/tls"
	"encoding/json"
	"fmt"
	"github.com/gorilla/websocket"
	"github.com/jonace-mpelule/okestra-device/internal/protocol"
	"net"
	"net/http"
	"net/url"
	"strings"
)

type API struct {
	baseURL    string
	token      string
	httpClient *http.Client
}

func NewAPI(profile protocol.AgentProfile) *API {
	transport := http.DefaultTransport.(*http.Transport).Clone()
	transport.TLSClientConfig = &tls.Config{MinVersion: tls.VersionTLS12}
	if profile.InsecureSkipVerify {
		transport.TLSClientConfig.InsecureSkipVerify = true // Explicit opt-in for a self-signed private endpoint.
	}
	return &API{
		baseURL: strings.TrimRight(profile.URL, "/"),
		token:   profile.Token,
		httpClient: &http.Client{
			Transport: transport,
			Timeout:   0,
		},
	}
}

func (a *API) Health(ctx context.Context) error {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, a.baseURL+"/healthz", nil)
	if err != nil {
		return err
	}
	resp, err := a.do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 300 {
		return decodeAPIError(resp)
	}
	return nil
}

func bridgeConnToWebsocket(conn net.Conn, ws *websocket.Conn) {
	errCh := make(chan error, 2)
	go func() {
		buf := make([]byte, 32*1024)
		for {
			n, err := conn.Read(buf)
			if n > 0 {
				if werr := ws.WriteMessage(websocket.BinaryMessage, buf[:n]); werr != nil {
					errCh <- werr
					return
				}
			}
			if err != nil {
				errCh <- err
				return
			}
		}
	}()
	go func() {
		for {
			_, data, err := ws.ReadMessage()
			if err != nil {
				errCh <- err
				return
			}
			if _, err := conn.Write(data); err != nil {
				errCh <- err
				return
			}
		}
	}()
	<-errCh
}

func (a *API) do(req *http.Request) (*http.Response, error) {
	if a.token != "" {
		req.Header.Set("Authorization", "Bearer "+a.token)
	}
	return a.httpClient.Do(req)
}

func (a *API) getJSON(ctx context.Context, path string, out any) error {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, a.baseURL+path, nil)
	if err != nil {
		return err
	}
	resp, err := a.do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 300 {
		return decodeAPIError(resp)
	}
	return json.NewDecoder(resp.Body).Decode(out)
}

func (a *API) postJSON(ctx context.Context, path string, body any, out any) error {
	data, err := json.Marshal(body)
	if err != nil {
		return err
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, a.baseURL+path, bytes.NewReader(data))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := a.do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 300 {
		return decodeAPIError(resp)
	}
	if out == nil {
		return nil
	}
	return json.NewDecoder(resp.Body).Decode(out)
}

func closeWebSocketOnCancel(ctx context.Context, conn *websocket.Conn, done <-chan struct{}) {
	select {
	case <-ctx.Done():
		_ = conn.Close()
	case <-done:
	}
}

func (a *API) webSocketDialer() *websocket.Dialer {
	dialer := *websocket.DefaultDialer
	if transport, ok := a.httpClient.Transport.(*http.Transport); ok && transport.TLSClientConfig != nil {
		dialer.TLSClientConfig = transport.TLSClientConfig.Clone()
	}
	return &dialer
}

func wsURL(base, path string) string {
	u, _ := url.Parse(base)
	switch u.Scheme {
	case "https":
		u.Scheme = "wss"
	default:
		u.Scheme = "ws"
	}
	u.Path, u.RawQuery, _ = strings.Cut(path, "?")
	return u.String()
}

func decodeAPIError(resp *http.Response) error {
	var apiErr protocol.APIError
	if err := json.NewDecoder(resp.Body).Decode(&apiErr); err == nil && apiErr.Code != "" {
		return fmt.Errorf("%s: %s", humanizeErrorCode(apiErr.Code), apiErr.Message)
	}
	return fmt.Errorf("unexpected server response (HTTP %d)", resp.StatusCode)
}

func humanizeErrorCode(code string) string {
	words := strings.Fields(strings.ReplaceAll(code, "_", " "))
	if len(words) == 0 {
		return "Server error"
	}
	label := strings.Join(words, " ")
	return strings.ToUpper(label[:1]) + label[1:]
}
