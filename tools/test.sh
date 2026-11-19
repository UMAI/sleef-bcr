#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$repo_root/tools/prepare.py"
export USE_BAZEL_VERSION="${USE_BAZEL_VERSION:-$(cat "$repo_root/.bazelversion")}"
cd -- "$repo_root/.work/sleef"
exec "${BAZEL:-bazel}" test -c opt //src/dft-tester:all "$@"
