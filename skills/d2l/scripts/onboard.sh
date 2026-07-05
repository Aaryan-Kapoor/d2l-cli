#!/usr/bin/env bash
set -euo pipefail

d2l token
d2l --md courses
d2l onboard
test -f D2L_COURSE_SOP.md
test -f .d2l/onboarding.json
