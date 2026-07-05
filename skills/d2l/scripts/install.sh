#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$repo_root"

python -m pip install --user -e ".[login]"
user_bin="$(python -m site --user-base)/bin"
export PATH="$user_bin:$PATH"
python -m playwright install chromium

if ! command -v d2l >/dev/null 2>&1; then
  echo "d2l was installed but is not on PATH." >&2
  echo "Add this to your shell profile:" >&2
  printf 'export PATH="%s:$PATH"\n' "$user_bin" >&2
  exit 1
fi

d2l --version
d2l --help >/dev/null
