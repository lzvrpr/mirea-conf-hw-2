#!/usr/bin/env sh
set -e
cd "$(dirname "$0")"
PY=python3
if [ -x .venv/bin/python ]; then
    PY=.venv/bin/python
fi
if ! "$PY" -c "import aiohttp" 2>/dev/null; then
    echo "aiohttp не установлен для $PY" >&2
    echo "Установите: $PY -m pip install -r requirements.txt" >&2
    exit 1
fi
exec "$PY" main.py "$@"
