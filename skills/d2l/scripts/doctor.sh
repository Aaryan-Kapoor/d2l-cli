#!/usr/bin/env bash
set -euo pipefail

d2l --version
d2l token
d2l whoami
d2l --md courses
d2l --md dump --shallow
