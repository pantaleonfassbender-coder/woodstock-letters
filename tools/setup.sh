#!/usr/bin/env bash
# Setup script for a Claude Code cloud environment (paste into the
# environment's "Setup script" field, or run by hand in a fresh checkout).
set -euo pipefail
python3 -m pip install --quiet -r requirements.txt
