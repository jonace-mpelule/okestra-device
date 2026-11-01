package agent

import (
	"net/http/httptest"
	"testing"
)

func TestStandaloneServiceHasNoDockerRoutes(t *testing.T) {
	t.Setenv("OKESTRA_DEVICE_ANDROID_ENABLED", "1")
	s := NewServer("", "secret", t.TempDir())
	for _, tc := range []struct {
		path, token string
		want        int
	}{
		{"/healthz", "", 200}, {"/readyz", "", 401}, {"/readyz", "secret", 200},
		{"/v1/android/status", "secret", 200}, {"/v1/containers", "secret", 404},
		{"/v1/build", "secret", 404}, {"/v1/images", "secret", 404},
	} {
		r := httptest.NewRequest("GET", tc.path, nil)
		if tc.token != "" {
			r.Header.Set("Authorization", "Bearer "+tc.token)
		}
		w := httptest.NewRecorder()
		s.Handler().ServeHTTP(w, r)
		if w.Code != tc.want {
			t.Errorf("%s: got %d, want %d", tc.path, w.Code, tc.want)
		}
	}
}
