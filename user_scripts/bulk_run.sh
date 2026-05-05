#!/usr/bin/env bash

set -eu

VERSIONS=(v0.8.132 v0.8.133 v0.8.134)
OS_NAME=$(uname -s)

for VER in "${VERSIONS[@]}"; do
  ./run.sh --xemu-tag "${VER}"
  if [[ "${OS_NAME}" != "Darwin" ]]; then
    ./run.sh --xemu-tag "${VER}" --use-vulkan
  fi
done
