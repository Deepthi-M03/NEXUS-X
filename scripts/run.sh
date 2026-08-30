#!/usr/bin/env bash
# NEXUS-X — one-command local launcher
set -e
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "== NEXUS-X: installing backend dependencies =="
pip install -r "$ROOT_DIR/backend/requirements.txt" --break-system-packages --quiet

echo "== NEXUS-X: generating synthetic demo dataset =="
python3 "$ROOT_DIR/backend/data_gen.py"

echo "== NEXUS-X: running backend test suite =="
(cd "$ROOT_DIR/backend" && python3 -m pytest tests/ -q)

echo "== NEXUS-X: starting backend on :8000 =="
(cd "$ROOT_DIR/backend" && python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 &)

sleep 2

echo "== NEXUS-X: starting frontend on :5173 =="
(cd "$ROOT_DIR/frontend" && python3 -m http.server 5173 &)

sleep 1
echo ""
echo "NEXUS-X is running:"
echo "  Frontend:  http://localhost:5173"
echo "  Backend:   http://localhost:8000  (docs at /docs)"
echo "  Demo login: investigator@nexusx.demo / demo123"
echo ""
echo "Press Ctrl+C in this terminal, then run 'pkill -f uvicorn; pkill -f http.server' to stop."
wait
