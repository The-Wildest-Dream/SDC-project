#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
exec python -m streamlit run app.py --server.address 0.0.0.0 --server.port "${PORT:-3000}" --server.headless true --browser.gatherUsageStats false
