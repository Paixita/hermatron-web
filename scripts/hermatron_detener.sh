#!/usr/bin/env bash
# ============================================================
#  HERMATRON — Detener servidor
# ============================================================
if pgrep -f "uvicorn app.main:app" > /dev/null 2>&1; then
    pkill -f "uvicorn app.main:app"
    sleep 1
    if pgrep -f "uvicorn app.main:app" > /dev/null 2>&1; then
        echo "⚠️ HERMATRON sigue corriendo. Intenta cerrarlo manualmente."
        exit 1
    fi
    echo "🛑 HERMATRON detenido correctamente."
else
    echo "ℹ️ HERMATRON no estaba corriendo."
fi