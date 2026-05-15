#!/usr/bin/env bash
# ============================================================
#  OLT Config Converter Engine — Backend (Linux/macOS)
# ============================================================
set -e
cd "$(dirname "$0")/backend"

# Escolhe o melhor python disponivel (prefere 3.13 / 3.12 sobre 3.14)
PYTHON_CMD=""
for cand in python3.13 python3.12 python3.14 python3; do
    if command -v "$cand" >/dev/null 2>&1; then
        PYTHON_CMD="$cand"
        break
    fi
done
PYTHON_CMD="${PYTHON_CMD:-python3}"
echo "Usando interpretador: $PYTHON_CMD"

# Fallback ABI3 caso o pip caia em build via Rust em Python muito novo
export PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1

if [ ! -d .venv ]; then
    echo "Criando virtualenv..."
    "$PYTHON_CMD" -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
