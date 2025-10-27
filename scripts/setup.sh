#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

# Python venv
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt

# Frontend deps
cd frontend
if ! command -v yarn >/dev/null 2>&1; then
  echo "Please install yarn (https://yarnpkg.com)." && exit 1
fi
yarn install
cd ..

# Prepare backend .env if missing
if [ ! -f backend/.env ]; then
  cp backend/.env.example backend/.env
fi

# Create a desktop shortcut (Linux) to open http://localhost:3000
if command -v xdg-desktop-menu >/dev/null 2>&1; then
  DESKTOP_FILE="$HOME/Desktop/Fetch Saúde.desktop"
  cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=Fetch Saúde
Exec=xdg-open http://localhost:3000
Terminal=false
EOF
  chmod +x "$DESKTOP_FILE"
fi

echo "Setup complete. To run locally:"
echo "1) Backend: source .venv/bin/activate && uvicorn backend.server:app --host 0.0.0.0 --port 8001"
echo "2) Frontend: cd frontend && yarn dev -- --host"
