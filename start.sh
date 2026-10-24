#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
PYTHON=".pythonlibs/bin/python"
if [ ! -x "$PYTHON" ]; then
  PYTHON="python"
fi
exec "$PYTHON" -m streamlit run app.py --server.address 0.0.0.0 --server.port "${PORT:-3000}" --server.headless true --browser.gatherUsageStats false
