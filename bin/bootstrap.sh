#!/usr/bin/env bash
# Nonprivileged setup from a reviewed checkout. Does not authenticate or change GitHub settings.
set -euo pipefail
TK="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
if [[ $# -gt 1 || ( $# -eq 1 && "$1" != --dev ) ]]; then
  echo "usage: bash bin/bootstrap.sh [--dev]" >&2; exit 2
fi
PY="${ACCI_PYTHON:-python3}"
"$PY" -c 'import sys; assert sys.version_info >= (3, 10), "Python 3.10+ required"'
"$PY" -m venv "$TK/.venv"
TARGET="$TK"
if [[ "${1:-}" == --dev ]]; then TARGET="$TK[dev]"; fi
"$TK/.venv/bin/python" -m pip install -e "$TARGET"
echo "Installed. Run: $TK/.venv/bin/acci --help"
echo "Optional: source \"$TK/.venv/bin/activate\""