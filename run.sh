#!/usr/bin/env bash

set -eu
set -o pipefail

if [[ ! -d venv ]]; then
  python3 -m venv venv
  venv/bin/pip3 install -r requirements.txt

  echo "Run xemu-perf-run --import-install <path_to_your_xemu_toml_file>"
  exit 1
fi

if [[ -n "${XEMU_DYLD_FALLBACK_LIBRARY_PATH-}" ]]; then
  export DYLD_FALLBACK_LIBRARY_PATH="${XEMU_DYLD_FALLBACK_LIBRARY_PATH}"
fi

./venv/bin/xemu-perf-run "$@"
