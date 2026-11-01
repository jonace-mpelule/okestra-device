package agent

import (
	"crypto/sha256"
	"crypto/subtle"
	"encoding/json"
	"github.com/gorilla/websocket"
	"github.com/jonace-mpelule/okestra-device/internal/protocol"
	"log"
	"net"
	"net/http"
	"strings"
	"time"
)

func (s *Server) auth(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if s.token == "" {
			next(w, r)
			return
		}
		header := r.Header.Get("Authorization")
		if !strings.HasPrefix(header, "Bearer ") {
			writeError(w, http.StatusUnauthorized, "auth_failed", "missing bearer token")
			return
		}
		tokenHash := sha256.Sum256([]byte(strings.TrimSpace(strings.TrimPrefix(header, "Bearer "))))
		expectedHash := sha256.Sum256([]byte(s.token))
		if subtle.ConstantTimeCompare(tokenHash[:], expectedHash[:]) != 1 {
			writeError(w, http.StatusUnauthorized, "auth_failed", "invalid agent token")
			return
		}
		next(w, r)
	}
}

func loggingMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		next.ServeHTTP(w, r)
		log.Printf("%s %s %s", r.Method, r.URL.Path, time.Since(start))
	})
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, code, msg string) {
	writeJSON(w, status, protocol.APIError{Code: code, Message: msg})
}

func pumpNetToWS(ws *websocket.Conn, src net.Conn, errCh chan<- error) {
	buf := make([]byte, 32*1024)
	for {
		n, err := src.Read(buf)
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
}

func pumpWSToNet(ws *websocket.Conn, dst net.Conn, errCh chan<- error) {
	for {
		_, data, err := ws.ReadMessage()
		if err != nil {
			errCh <- err
			return
		}
		if _, err := dst.Write(data); err != nil {
			errCh <- err
			return
		}
	}
}
