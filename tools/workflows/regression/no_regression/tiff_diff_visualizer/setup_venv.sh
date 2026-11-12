#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 -m venv "$HERE/.venv"
"$HERE/.venv/bin/python" -m pip install --upgrade pip
"$HERE/.venv/bin/pip" install -r "$HERE/requirements.txt"

echo "Created $HERE/.venv"
echo "Run with: $HERE/.venv/bin/python $HERE/compare_tiffs_visual.py --help"
