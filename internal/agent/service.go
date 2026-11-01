package agent

import (
	"context"
	"github.com/gorilla/websocket"
	"github.com/jonace-mpelule/okestra-device/internal/android"
	"net/http"
	"net/url"
	"os"
	"time"
)

type Server struct {
	android              *android.Manager
	addr, token, workDir string
	upgrader             websocket.Upgrader
}

func NewServer(addr, token, workDir string) *Server {
	return &Server{android: android.New(workDir), addr: addr, token: token, workDir: workDir, upgrader: websocket.Upgrader{CheckOrigin: func(r *http.Request) bool {
		origin := r.Header.Get("Origin")
		if origin == "" {
			return true
		}
		u, e := url.Parse(origin)
		return e == nil && (u.Scheme == "http" || u.Scheme == "https") && u.Host == r.Host
	}}}
}
func (s *Server) Handler() http.Handler {
	m := http.NewServeMux()
	m.HandleFunc("/healthz", func(w http.ResponseWriter, r *http.Request) { writeJSON(w, 200, map[string]string{"status": "ok"}) })
	m.HandleFunc("/readyz", s.auth(func(w http.ResponseWriter, r *http.Request) {
		status := s.android.Status(r.Context())
		if !status.Enabled {
			writeError(w, 503, "android_disabled", "Android runtime disabled")
			return
		}
		writeJSON(w, 200, status)
	}))
	m.HandleFunc("/v1/android/", s.auth(s.handleAndroid))
	return loggingMiddleware(m)
}
func (s *Server) ListenAndServe(ctx context.Context) error {
	defer s.android.Close()
	if e := os.MkdirAll(s.workDir, 0700); e != nil {
		return e
	}
	srv := &http.Server{Addr: s.addr, Handler: s.Handler(), ReadHeaderTimeout: 15 * time.Second, IdleTimeout: 90 * time.Second}
	go func() {
		<-ctx.Done()
		c, stop := context.WithTimeout(context.Background(), 5*time.Second)
		defer stop()
		_ = srv.Shutdown(c)
	}()
	e := srv.ListenAndServe()
	if e == http.ErrServerClosed {
		return nil
	}
	return e
}
