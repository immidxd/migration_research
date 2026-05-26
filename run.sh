#!/bin/bash
set -e

cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv venv
fi

source venv/bin/activate

if [ ! -f "venv/.requirements_installed" ]; then
  echo "Installing Python dependencies..."
  pip install -U pip
  pip install -r requirements.txt
  touch venv/.requirements_installed
fi

if [ ! -d "frontend/node_modules" ]; then
  echo "Installing frontend dependencies..."
  pushd frontend >/dev/null
  npm install
  popd >/dev/null
fi

MODE="${1:-dev}"

if [ "$MODE" = "build" ]; then
  pushd frontend >/dev/null
  npm run build
  popd >/dev/null
  echo "Frontend built. Launch with: ./run.sh"
  exit 0
fi

if [ "$MODE" = "migrate" ]; then
  alembic upgrade head
  exit 0
fi

# Default: launch desktop app
python main.py
