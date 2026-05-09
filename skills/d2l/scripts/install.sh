#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$repo_root"

python -m venv .venv
# shellcheck source=/dev/null
source .venv/bin/activate
pip install -e ".[login]"
playwright install chromium

d2l --version
d2l --help >/dev/null
