package client

import (
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"regexp"
)

type Project struct {
	Name    string          `json:"name"`
	Android *AndroidProject `json:"android,omitempty"`
}

var projectName = regexp.MustCompile(`^[a-z0-9][a-z0-9-]*$`)

func loadProject(path string) (Project, string, []string, error) {
	abs, e := filepath.Abs(path)
	if e != nil {
		return Project{}, "", nil, e
	}
	b, e := os.ReadFile(abs)
	if e != nil {
		return Project{}, "", nil, e
	}
	var p Project
	if e = json.Unmarshal(b, &p); e != nil {
		return p, "", nil, e
	}
	_, e = p.validate()
	return p, filepath.Dir(abs), nil, e
}
func (p Project) validate() ([]string, error) {
	if !projectName.MatchString(p.Name) || len(p.Name) > 48 || p.Name == "device" {
		return nil, errors.New("invalid project name")
	}
	if p.Android == nil {
		return nil, errors.New("android configuration required")
	}
	return nil, p.Android.validate()
}
