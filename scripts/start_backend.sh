#!/bin/bash
#
# Start Agent Board Backend API Server
# 
# Usage: ./scripts/start_backend.sh [--port PORT] [--host HOST]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CD="${AGENT_BOARD_API_URL:-}"

# Parse arguments
PORT=8001
HOST="localhost"

while [[ $# -gt 0 ]]; do
    case $1 in
        --port) PORT="$2"; shift 2 ;;
        --host) HOST="$2"; shift 2 ;;
        --help)
            echo "Usage: $0 [--port PORT] [--host HOST]"
            exit 0
            ;;
        *) shift ;;
    esac
done

# Change to project root
cd "$PROJECT_ROOT"

# Check dependencies
if [ ! -f backend/requirements.txt ]; then
    echo "❌ requirements.txt not found in backend/"
    exit 1
fi

# Check if venv exists, create if not
if [ ! -d ".venv-backend" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv .venv-backend
fi

# Activate venv
source .venv-backend/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install -q -r backend/requirements.txt

# Start server
echo ""
echo "🚀 Starting Agent Board Backend API"
echo "==================================="
echo "URL: http://$HOST:$PORT"
echo "Docs: http://$HOST:$PORT/docs"
echo "==================================="
echo ""

uvicorn backend.main:app \
    --host "$HOST" \
    --port "$PORT" \
    --reload
