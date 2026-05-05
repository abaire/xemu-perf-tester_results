#!/usr/bin/env bash

set -eu
set -o pipefail

if ! git remote show upstream 2> /dev/null ; then
  git remote add upstream https://github.com/abaire/xemu-perf-tester_results.git
fi

git checkout main
git pull upstream main
git push origin main

if [[ ! -d venv ]]; then
  exec ./run.sh
fi

./venv/bin/pip3 install -r requirements.txt
