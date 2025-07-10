#!/usr/bin/env bash

set -eu

VERSIONS=(v0.8.53 v0.8.54 v0.8.92)

for VER in "${VERSIONS[@]}"; do
  ./run.sh --xemu-tag "${VER}"
done
