#!/bin/bash
echo "🤖 Iniciando HERMATRON v6.1..."
cd "$(dirname "$0")"
if [ -d ".venv" ]; then
    echo "Usando el entorno virtual (.venv)..."
    .venv/bin/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 5001
else
    echo "Usando python3 global del sistema..."
    python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 5001
fi
