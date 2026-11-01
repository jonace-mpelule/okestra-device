GO ?= go
VERSION ?= dev
COMMIT ?= $(shell git rev-parse --short HEAD 2>/dev/null || printf unknown)
BUILD_DATE ?= $(shell date -u +%Y-%m-%dT%H:%M:%SZ)
LDFLAGS := -s -w -X github.com/jonace-mpelule/okestra-device/internal/version.Version=$(VERSION) -X github.com/jonace-mpelule/okestra-device/internal/version.Commit=$(COMMIT) -X github.com/jonace-mpelule/okestra-device/internal/version.Date=$(BUILD_DATE)

.PHONY: build test check device dist release publish release-build release-setup release-doctor clean
build:
	mkdir -p bin
	$(GO) build -trimpath -ldflags '$(LDFLAGS)' -o bin/okestra-device ./cmd/okestra-device
	$(GO) build -trimpath -ldflags '$(LDFLAGS)' -o bin/okestra-device-service ./cmd/okestra-device-service
test:
	$(GO) test ./...
check:
	$(GO) vet ./...
	$(GO) test -race ./...
device:
	OKESTRA_LDFLAGS='$(LDFLAGS)' OKESTRA_VERSION=$(VERSION) ./scripts/build-device.sh
dist:
	VERSION=$(VERSION) LDFLAGS='$(LDFLAGS)' ./scripts/package.sh
# Desktop releases are app-only; dist remains the CLI/server package workflow.
PUBLISH_VERSION = $(if $(filter-out dev,$(VERSION)),--version $(VERSION),)
release publish:
	python3 scripts/release.py publish $(PUBLISH_VERSION) $(RELEASE_ARGS)
release-build:
	python3 scripts/release.py build $(PUBLISH_VERSION) $(RELEASE_ARGS)
release-setup:
	python3 scripts/release.py setup
release-doctor:
	python3 scripts/release.py doctor
clean:
	rm -rf bin dist
