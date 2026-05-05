#!/usr/bin/env bash

set -eu
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -d "${SCRIPT_DIR}/venv" ]]; then
  python3 -m venv "${SCRIPT_DIR}/venv"
  "${SCRIPT_DIR}/venv/bin/pip3" install -r "${SCRIPT_DIR}/requirements.txt"

  echo "Run xemu-perf-run --import-install <path_to_your_xemu_toml_file>"
  exit 1
fi

if [[ -n "${XEMU_DYLD_FALLBACK_LIBRARY_PATH-}" ]]; then
  export DYLD_FALLBACK_LIBRARY_PATH="${XEMU_DYLD_FALLBACK_LIBRARY_PATH}"
fi

"${SCRIPT_DIR}/venv/bin/xemu-perf-run" --block-list-file "${SCRIPT_DIR}/inputs/block_list.json" -U "$@"
