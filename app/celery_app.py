# app/celery_app.py
"""Configuración de Celery para la arquitectura de colas de Hermatron.
Utiliza Redis como broker y backend. La variable de entorno REDIS_URL permite
sobreescribir la URL del servidor Redis (por defecto localhost:6379/0).
"""
import os
from celery import Celery

# URL del broker Redis (puede ser proporcionada por Render en una variable de entorno)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Creación de la instancia de Celery
celery = Celery(
    "hermatron",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.video_manager"],
)

# Opciones de configuración recomendadas
celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,  # Re‑intentar tareas si el worker muere
    worker_prefetch_multiplier=1,  # Evita que un worker tome muchas tareas simultáneamente
)

# Exportar la instancia para que pueda ser importada desde otros módulos
__all__ = ["celery"]
