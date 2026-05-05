#!/usr/bin/env bash

set -eu

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

VERSIONS=(v0.8.132 v0.8.133 v0.8.134)
OS_NAME=$(uname -s)

for VER in "${VERSIONS[@]}"; do
  "${SCRIPT_DIR}/run.sh" --xemu-tag "${VER}"
  if [[ "${OS_NAME}" != "Darwin" ]]; then
    "${SCRIPT_DIR}/run.sh" --xemu-tag "${VER}" --use-vulkan
  fi
done
