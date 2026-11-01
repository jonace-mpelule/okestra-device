#!/bin/sh
# Compile native Liquid Glass renditions and an ICNS fallback from one vector source.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
OUTPUT=${1:-"$ROOT/dist/Okestra Device.app/Contents/Resources"}
mkdir -p "$OUTPUT"
OUTPUT=$(CDPATH= cd -- "$OUTPUT" && pwd)
BUILD_DIR=$(mktemp -d "${TMPDIR:-/tmp}/okestra-icon.XXXXXX")
trap 'rm -rf "$BUILD_DIR"' EXIT HUP INT TERM
xcrun actool "$ROOT/apps/okestra-device/AppIcon.icon" \
 --compile "$BUILD_DIR" --output-format human-readable-text \
 --platform macosx --minimum-deployment-target 13.0 --app-icon AppIcon \
 --output-partial-info-plist "$BUILD_DIR/icon-info.plist"
for resource in AppIcon.icns Assets.car; do
 [ -s "$BUILD_DIR/$resource" ] || { printf 'Missing icon output: %s\n' "$resource" >&2; exit 1; }
 install -m 0644 "$BUILD_DIR/$resource" "$OUTPUT/$resource"
done
