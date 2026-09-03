"""
Configuración del Agente HERMATRON
"""
import os
from dotenv import load_dotenv
from pathlib import Path

# Cargar variables de entorno
# Ruta base del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent

# Cargar variables de entorno desde el archivo .env en la raíz
load_dotenv(BASE_DIR / ".env")

# Configuración de Groq
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_SAFETY_MODE = os.getenv("GEMINI_SAFETY_MODE", "True").lower() == "true"

# fal.ai — generación de video con Mochi 1 / WAN / LTX-Video
FAL_KEY = os.getenv("FAL_KEY", "")

# Configuración de OpenRouter (proveedor alternativo con +200 modelos)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
# Indica qué proveedor usa el chat principal: "groq" | "openrouter" | "qwen3"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")

# ── Agente interno Qwen 3 (GRATIS: Ollama local / OpenRouter :free) ────────────
# Qwen 3 es un agente open-source con tool calling nativo (puede ejecutar
# Python, comandos del PC, HTTP y búsqueda web a través de las herramientas).
QWEN3_ENABLED = os.getenv("QWEN3_ENABLED", "True").lower() == "true"
QWEN3_API_KEY = os.getenv("QWEN3_API_KEY", "")
# Por defecto apunta a Ollama local (100%% gratis, sin nube):
#   ollama run qwen3:8b
# Para usar la nube (gratis con límites diarios) cambia a:
#   https://openrouter.ai/api/v1  y  QWEN3_MODEL=qwen/qwen3-235b-a22b-instruct:free
QWEN3_BASE_URL = os.getenv("QWEN3_BASE_URL", "http://localhost:11434/v1")
QWEN3_MODEL = os.getenv("QWEN3_MODEL", "qwen3:8b")

# Modelos de visión disponibles en Groq
# NOTA: Los modelos llama-3.2-*-vision fueron DECOMISIONADOS por Groq.
# Llama 4 Scout es el modelo multimodal actual que soporta imágenes.
GROQ_MODEL_VISION = os.getenv("GROQ_MODEL_VISION", "meta-llama/llama-4-scout-17b-16e-instruct")
GROQ_MODEL_VISION_LARGE = os.getenv("GROQ_MODEL_VISION_LARGE", "meta-llama/llama-4-scout-17b-16e-instruct")

# Configuración del servidor
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", 5001))
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

# Configuración de TTS
# Default alineado con el backend/UI: Jorge (edge-tts) gratis.
TTS_VOICE = os.getenv("TTS_VOICE", "es-MX-JorgeNeural")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "")

# Rutas
AUDIO_DIR = BASE_DIR / "audio"
AUDIO_DIR.mkdir(exist_ok=True)

DATABASE_PATH = BASE_DIR / "hermatron.db"

# Directorio de exportaciones
EXPORTS_DIR = BASE_DIR / "exports"
EXPORTS_DIR.mkdir(exist_ok=True)

# Directorio de videos
VIDEOS_DIR = BASE_DIR / "videos"
VIDEOS_DIR.mkdir(exist_ok=True)

# API de Pexels (imágenes/videos reales gratis)
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")

# API de ElevenLabs (voces naturales gratis - 10,000 chars/mes)
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")

# Directorio de imágenes subidas
IMAGENES_DIR = BASE_DIR / "imagenes_subidas"
IMAGENES_DIR.mkdir(exist_ok=True)

#Configuración de video
# Opciones: "1920x1080" (HD), "2560x1440" (2K), "3840x2160" (4K)
IMAGEN_RESOLUTION = os.getenv("IMAGEN_RESOLUTION", "2560x1440")  # Default 2K para mejor calidad
TRANSLATION_CACHE_TTL = int(os.getenv("TRANSLATION_CACHE_TTL", "86400"))   # 24 h
MAX_IN_MEMORY_DURATION = int(os.getenv("MAX_IN_MEMORY_DURATION", "120"))  # secs
IMAGE_RESOLUTIONS = {
    "16:9": (1920, 1080),
    "9:16": (1080, 1920),
    "1080p": (1920, 1080),
}
TRANSLATION_CACHE_PATH = BASE_DIR / "videos" / "translation_cache.json"

# Opciones adicionales
VIDEO_FPS = int(os.getenv("VIDEO_FPS", "30"))

# ── Duración objetivo del video (segundos) ────────────────────────────────────
# HERMATRON asegura que cada video dure entre estos límites:
#  - Si la narración es más corta, se añade silencio final (apad).
#  - Los clips de fal.ai se solicitan en 1080p.
VIDEO_MIN_DURATION = int(os.getenv("VIDEO_MIN_DURATION", "5"))
VIDEO_MAX_DURATION = int(os.getenv("VIDEO_MAX_DURATION", "300"))

# Seguridad y Permisos
ALLOW_SYSTEM_COMMANDS = os.getenv("ALLOW_SYSTEM_COMMANDS", "False").lower() == "true"
HERMATRON_ADMIN_MODE = os.getenv("HERMATRON_ADMIN_MODE", "False").lower() == "true"

# ── Servicios Avanzados del Agente (v6.2, 100% gratis) ────────────────────────
# Acceso al sistema de archivos del PC (listar, leer, escribir, crear, copiar,
# mover, eliminar y buscar carpetas/archivos). True por defecto porque ya
# existe ALLOW_SYSTEM_COMMANDS; poner en False para desactivar solo esto.
ALLOW_FILE_ACCESS = os.getenv("ALLOW_FILE_ACCESS", "True").lower() == "true"
# Token de GitHub OPCIONAL (gratis, Settings > Developer settings > Tokens).
# Sin token funciona con la API pública (límites: 10 búsquedas/min, 60 req/h).
# Con token se desbloquean búsqueda de código y límites más altos.
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
