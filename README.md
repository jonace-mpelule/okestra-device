# Okestra Device

A standalone Android device workspace for macOS, with its own optional Linux emulator server. Use a physical phone over USB/Wi-Fi without a server, or connect to a KVM-accelerated remote emulator. Docker is not required.

The native Mac app includes live video and controls, local ADB access, saved hardware profiles, APK installation, Logcat, deep links, network inspection, audio playback, recording and review, screenshot editing, and diagnostic exports. Archived Flutter/Expo server build workflows are retained behind explicit opt-in.

## Build

Requirements: Go 1.26.2+, macOS/Xcode for the Mac app. Android emulator hosting requires x86_64 Linux, KVM, Java and the Android SDK.

```sh
make build                  # standalone helper and server in bin/
make device                 # universal Mac app in dist/
make VERSION=0.1.0 dist      # six archives and SHA256SUMS; run on macOS
make check
swift test --package-path apps/okestra-device
python3 -m unittest discover -s scripts -p 'test_*.py'
```

The app bundles `okestra-device`; it never invokes the Docker product's CLI. Pinned scrcpy artifacts and license notices are in `third_party/scrcpy`. The network monitor JAR is checked against its Java source at build time; rebuild it with `scripts/build-network-monitor.sh` after changing the source.

## Install

On an x86_64 Ubuntu/Debian emulator host, extract the Linux server archive and run:

```sh
sudo ./install-android.sh
```

From a source checkout, first cross-build the server if needed:

```sh
GOOS=linux GOARCH=amd64 go build -o bin/okestra-device-service ./cmd/okestra-device-service
sudo ./scripts/setup-android-server.sh --install
```

On the Mac, extract the matching client archive and run `./install-android.sh`, or double-click `Install Android.command`. From source, run `make build device` followed by `./scripts/install-android.sh`.

```sh
okestra-device server add --name devbox --url http://PRIVATE_SERVER:8089
# Supply the new server token through OKESTRA_DEVICE_TOKEN, or --token.
okestra-device android doctor
okestra-device android profiles
```

Use an encrypted private network, or HTTPS. Server management uses a bearer token; access to it grants control of the managed emulator.

## Independent runtime

| Setting | Device |
|---|---|
| Helper / server | `okestra-device` / `okestra-device-service` |
| Default listener | `127.0.0.1:8089` (installer configures a reachable address) |
| Client profiles | `~/.okestra-device/config.json` |
| Server configuration | `/etc/okestra-device/okestra-device.env` |
| Server account and data | `okestra-device`, `/var/lib/okestra-device` |
| Server settings | `OKESTRA_DEVICE_SERVICE_ADDR`, `OKESTRA_DEVICE_SERVICE_TOKEN`, `OKESTRA_DEVICE_SERVICE_WORKDIR` |
| Android runtime | `OKESTRA_DEVICE_ANDROID_ENABLED=1`, `ANDROID_HOME`, `ANDROID_USER_HOME` |

`/healthz` reports process liveness. Authenticated `/readyz` reports whether the Android runtime is enabled; inspect `/v1/android/status` or `android doctor` for SDK/KVM/device diagnostics. Existing Android routes remain under `/v1/android/`. There are no container/build/image endpoints.

See [device setup and features](docs/android.md), [migration from combined Okestra](docs/migration.md), and the [archived workflows](docs/archive/README.md). Updates use this repository's releases: `okestra-device upgrade` or `sudo okestra-device-service upgrade`. `make release` tests, packages and publishes the next release; it requires GitHub authentication. No release is published by building locally.

Extracted from `jonace-mpelule/okestra` at checkpoint `1aa5a3c`, including all Device work present at extraction. The Docker CLI, service and menu app remain in that repository.
