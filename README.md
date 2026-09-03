# 🤖 HERMATRON v6.1 - Agente Creativo Profesional

Un asistente de IA profesional con voz, memoria persistente, **video 1080p de 8 a 15 segundos** y **agente interno Qwen 3 gratis**, construido con **FastAPI**.

## ✨ Características

- 🎯 **Chat inteligente** con Groq + **agente interno Qwen 3** (gratis: Ollama local u OpenRouter `:free`) + OpenRouter como respaldo
- 🗣️ **Voz neuronal** con Edge TTS (gratis) y ElevenLabs (premium)
- 🎬 **Video 1080p Full HD de 8 a 15 segundos**: pipeline "Director de Cine" (guion → escenas → imágenes con consistencia de personajes → voz → subtítulos → ensamblado FFmpeg), con clips de movimiento real vía fal.ai (WAN 2.2 / LTX) en 1080p
- 🖼️ **Imágenes** con Gemini Nano Banana y Pollinations
- 💻 **Acceso al PC**: ejecuta Python, comandos, mueve archivos y consulta HTTP desde el chat
- 👁️ **Visión multimodal** (Llama 4 Scout)
- 💾 **Memoria persistente** con SQLite
- 👥 **Multi-agentes creativos**: Guionista, Casting, Inspector de Arte, LipSync, Calidad

## 📁 Estructura del Proyecto

```
HERMATRON/
├── app/                  # Backend FastAPI
│   ├── main.py           # Aplicación y endpoints
│   ├── config.py         # Configuración (.env)
│   ├── video.py          # Motor de video (Director de Cine)
│   ├── video_manager.py  # Tareas de producción
│   ├── memoria.py        # SQLite
│   ├── voz.py            # TTS
│   ├── agents/           # Multi-agentes creativos
│   └── busqueda.py       # Búsqueda web
├── templates/            # Frontend (landing, chat, estudio de video)
├── static/               # CSS, JS, personajes, escenografías
├── videos/               # Videos y proyectos generados
├── audio/                # Audios generados
├── scripts/              # Utilidades y pruebas (scratch/ incluido)
├── docs/                 # Documentación y notas
├── utils/                # Helpers (ffmpeg)
├── .env                  # Variables de entorno (NO committear)
├── requirements.txt
└── README.md
```

## 🚀 Instalación

### 1. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 2. (Opcional pero recomendado) Activar el agente Qwen 3 local gratis

```bash
# Instala Ollama y baja el modelo Qwen 3 (100% gratis, local)
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen3:8b
```

> Sin Ollama, HERMATRON usa Groq (gratis con límites). Para usar Qwen 3 por nube gratis, pon en `.env`: `QWEN3_BASE_URL=https://openrouter.ai/api/v1` y `QWEN3_MODEL=qwen/qwen3-235b-a22b-instruct:free`.

### 3. Configurar `.env`

Copia las claves en `.env` (ver `.env.example`): `GROQ_API_KEY`, `GOOGLE_API_KEY`, `OPENROUTER_API_KEY`, `FAL_KEY`, etc.

### 4. Ejecutar el servidor

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 5001
```

O en Windows: doble clic en `iniciar.bat`.

### 5. Abrir en el navegador

Ve a: **http://localhost:5001**

## ⚙️ Configuración clave del `.env`

```bash
# Proveedor LLM: "groq" | "qwen3" | "openrouter"
LLM_PROVIDER=groq

# Agente interno Qwen 3 (gratis)
QWEN3_ENABLED=True
QWEN3_BASE_URL=http://localhost:11434/v1
QWEN3_MODEL=qwen3:8b

# Duración objetivo del video (segundos)
VIDEO_MIN_DURATION=8
VIDEO_MAX_DURATION=15
```

## 🔌 API Endpoints principales

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/` | GET | Landing |
| `/chat` | GET | Chat multiusos |
| `/videos` | GET | Estudio de video |
| `/api/chat` | POST | Enviar mensaje (LLM + herramientas) |
| `/api/video/pre-produccion` | POST | Crear video 1080p (8-15s) |
| `/api/health` | GET | Estado del sistema |

---

**Hecho con ❤️ por tu pana desarrollador · HERMATRON v6.1 © 2026**
