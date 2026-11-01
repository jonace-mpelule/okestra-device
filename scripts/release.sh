#!/bin/sh
# Compatibility entry point. make publish is the recommended desktop release workflow.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
exec python3 "$ROOT/scripts/release.py" publish "$@"
