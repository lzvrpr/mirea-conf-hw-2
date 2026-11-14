#!/usr/bin/env sh
set -e
cd "$(dirname "$0")"
PY=python3
if [ -x .venv/bin/python ]; then
    PY=.venv/bin/python
fi
exec "$PY" main.py "$@"
