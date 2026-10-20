#!/usr/bin/env bash

# Runs the benchmarks against the CI build of one or more xemu pull requests and submits the results.
#
# Usage: run_pr.sh <pr_url_or_number> [<pr_url_or_number> ...] [-- <extra run.sh arguments>]
#   e.g., run_pr.sh https://github.com/xemu-project/xemu/pull/3088
#         run_pr.sh 3088 3090 -- --just-suites FillRate

set -eu

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OS_NAME=$(uname -s)

PRS=()
while [[ $# -gt 0 ]]; do
  if [[ "$1" == "--" ]]; then
    shift
    break
  fi
  if [[ "$1" =~ ^#?([0-9]+)$ ]]; then
    PRS+=("https://github.com/xemu-project/xemu/pull/${BASH_REMATCH[1]}")
  elif [[ "$1" =~ ^https://github\.com/[^/]+/[^/]+/(pull/[0-9]+|actions/runs/[0-9]+) ]]; then
    PRS+=("$1")
  else
    echo "Unrecognized PR '$1'. Expected a PR number or URL like https://github.com/xemu-project/xemu/pull/3088" >&2
    exit 1
  fi
  shift
done

if [[ ${#PRS[@]} -eq 0 ]]; then
  echo "Usage: $0 <pr_url_or_number> [...] [-- <extra run.sh arguments>]" >&2
  exit 1
fi

# PR support requires a newer xemu-perf-tester than older installs may have.
if [[ -d "${SCRIPT_DIR}/venv" ]]; then
  "${SCRIPT_DIR}/venv/bin/pip3" install -q --upgrade -r "${SCRIPT_DIR}/requirements.txt"
fi

for PR in "${PRS[@]}"; do
  echo "Testing ${PR}"
  "${SCRIPT_DIR}/run.sh" --xemu-tag "${PR}" "$@"
  if [[ "${OS_NAME}" != "Darwin" ]]; then
    "${SCRIPT_DIR}/run.sh" --xemu-tag "${PR}" --use-vulkan "$@"
  fi
done
