#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
: "${VERSION:?Set VERSION}"
mkdir -p dist
stage=$(mktemp -d "$PWD/dist/package.XXXXXX")
trap 'rm -rf "$stage"' EXIT HUP INT TERM
[ "$(uname -s)" = Darwin ] || { echo 'Build release archives on a Mac.' >&2; exit 1; }
OKESTRA_VERSION=$VERSION OKESTRA_LDFLAGS=${LDFLAGS:-} ./scripts/build-device.sh
for platform in linux darwin; do
 for arch in amd64 arm64; do
  GOOS=$platform GOARCH=$arch go build -trimpath -ldflags "${LDFLAGS:-}" -o "$stage/okestra-device" ./cmd/okestra-device
  cp scripts/install-cli.sh scripts/setup-android-mac.sh scripts/install-android.sh "scripts/Install Android.command" "$stage/"
  if [ "$platform" = darwin ]; then
   [ "$(uname -s)" = Darwin ] || { echo 'Build macOS archives on a Mac.' >&2; exit 1; }
   if [ ! -d 'dist/Okestra Device.app' ]; then OKESTRA_VERSION=$VERSION OKESTRA_LDFLAGS=${LDFLAGS:-} ./scripts/build-device.sh; fi
   cp -R 'dist/Okestra Device.app' "$stage/"
  fi
  tar -C "$stage" -czf "dist/okestra-device_${VERSION}_${platform}_${arch}.tar.gz" .
 done
done
rm -rf "$stage/Okestra Device.app"
rm -f "$stage/okestra-device" "$stage/install-cli.sh" "$stage/setup-android-mac.sh"
cp scripts/install-service.sh scripts/setup-android-server.sh scripts/android-tools.py scripts/install-android.sh deploy/systemd/okestra-device-service.service "$stage/"
for arch in amd64 arm64; do
 GOOS=linux GOARCH=$arch go build -trimpath -ldflags "${LDFLAGS:-}" -o "$stage/okestra-device-service" ./cmd/okestra-device-service
 tar -C "$stage" -czf "dist/okestra-device-service_${VERSION}_linux_${arch}.tar.gz" .
done
cd dist
shasum -a 256 okestra-device_"$VERSION"_*.tar.gz okestra-device-service_"$VERSION"_*.tar.gz > SHA256SUMS
