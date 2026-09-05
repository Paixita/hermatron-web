#!/usr/bin/env bash
# ============================================================
#  HERMATRON — Lanzador del Estudio de Video
#  Inicia el servidor (si no está corriendo) y abre el navegador
# ============================================================
set -e

PROYECTO="/home/paicita/Descargas/Hermatron"
PUERTO=5001
URL="http://127.0.0.1:${PUERTO}/videos"
LOG="${PROYECTO}/hermatron.log"

cd "$PROYECTO"

# ¿Ya está corriendo? Solo abrimos el navegador.
if pgrep -f "uvicorn app.main:app" > /dev/null 2>&1; then
    echo "HERMATRON ya está en marcha. Abriendo el Estudio..."
    xdg-open "$URL" > /dev/null 2>&1 || true
    exit 0
fi

# Arrancar el servidor en segundo plano (detached)
nohup .venv/bin/python -u -m uvicorn app.main:app --host 127.0.0.1 --port "$PUERTO" \
    > "$LOG" 2>&1 < /dev/null &
PID=$!
disown "$PID" 2>/dev/null || true

# Esperar a que el servidor responda (máx. 90 s)
echo "🚀 Iniciando HERMATRON (pid $PID)..."
for i in $(seq 1 90); do
    if curl -s -m 2 "http://127.0.0.1:${PUERTO}/api/health" > /dev/null 2>&1; then
        echo "✅ ¡HERMATRON listo! Abriendo el Estudio de Video..."
        xdg-open "$URL" > /dev/null 2>&1 || true
        exit 0
    fi
    sleep 1
done

echo "⚠️ El servidor no respondió a tiempo. Revisa el log: $LOG"
exit 1