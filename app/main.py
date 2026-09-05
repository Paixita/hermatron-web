"""
HERMATRON v6.1 - CEREBRO AUTÓNOMO + CONTROL PC + INTERNET (Definitivo)
"""
import sys
import io
import os
import shutil
import time
import traceback
import json
from app.config import ALLOW_SYSTEM_COMMANDS, ALLOW_FILE_ACCESS
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# 1. Carga de Variables
BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")
# En algunos entornos (p.ej. ciertos runners/uvicorn) sys.stdout puede no exponer `.buffer`.
try:
    if getattr(sys.stdout, "buffer", None) is not None:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

from fastapi import FastAPI, Request, HTTPException, Form, Depends, Response, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from typing import Optional, List
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
from pydantic import BaseModel
from typing import Optional

# 2. Importes de tu proyecto
from .config import GROQ_API_KEY, GROQ_MODEL, GROQ_MODEL_VISION, GROQ_MODEL_VISION_LARGE, HOST, PORT, DEBUG, TTS_VOICE, AUDIO_DIR
from .config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODEL, LLM_PROVIDER
from .config import QWEN3_ENABLED, QWEN3_API_KEY, QWEN3_BASE_URL, QWEN3_MODEL
from .memoria import memoria
from .voz import generador_voz
from .busqueda import buscador 
from . import auth
from .video import generador_video, VideoEstado
from .modos import listar_modos
from .agente_servicios import (
    listar_carpeta, leer_archivo, escribir_archivo, crear_carpeta,
    copiar_elemento, mover_elemento, eliminar_elemento, buscar_archivos,
    info_ruta, leer_codigo_proyecto,
    github_buscar_repos, github_leer_archivo, github_listar_contenido,
    github_descargar_repo, github_buscar_codigo,
    guardar_conocimiento, buscar_conocimiento, actualizar_conocimiento_web,
    proponer_arreglo,
)
from .video_manager import pre_producir_video_task, regenerar_imagen_task, ensamblar_video_task
# from .celery_app import celery # Removido para modo gratuito

print(f"DEBUG: GROQ_API_KEY cargada? {bool(GROQ_API_KEY)}")
if GROQ_API_KEY:
    print(f"DEBUG: GROQ_API_KEY empieza con: {GROQ_API_KEY[:7]}...")

import asyncio
from fastapi import BackgroundTasks

class VideoRequest(BaseModel):
    tema: str
    prompt: str
    descripcion: Optional[str] = ""
    voz: Optional[str] = "es-MX-JorgeNeural"
    estilo: Optional[str] = "cinematic"
    formato: Optional[str] = "16:9"
    bgm_path: Optional[str] = None
    # Modo de video: "auto" | "presentacion" | "gratis" | "fal"
    modo_video: Optional[str] = "auto"

class ProbarVozRequest(BaseModel):
    voz: str

class ExportRequest(BaseModel):
    proyecto_id: str
    resolucion: str


def _ejecutar_codigo_python(codigo: str) -> dict:
    """Ejecuta código Python guardándolo en un archivo temporal"""
    import tempfile
    import subprocess
    import os
    try:
        fd, temp_path = tempfile.mkstemp(suffix=".py", text=True)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(codigo)
        
        # Ejecutar el archivo usando la misma versión de python que el servidor
        res = subprocess.run([sys.executable, temp_path], capture_output=True, text=True, timeout=30)
        
        try:
            os.remove(temp_path)
        except:
            pass
            
        if res.returncode == 0:
            return {"status": "success", "salida": res.stdout}
        else:
            return {"status": "error", "salida": res.stdout, "error": res.stderr}
    except subprocess.TimeoutExpired:
        try: os.remove(temp_path)
        except: pass
        return {"status": "error", "error": "Timeout (el código tardó más de 30 segundos en ejecutarse)"}
    except Exception as e:
        return {"status": "error", "error": str(e)}



import json
from app.config import ALLOW_SYSTEM_COMMANDS, ALLOW_FILE_ACCESS
def _extraer_tool_calls_de_texto(texto: str) -> list:
    """Extrae tool calls de un texto generado por el LLM.
    Soporta 2 formatos que algunos modelos emiten en texto plano:
      1. JSON  {"type":"function","function":{"name":"...","arguments":"{...}"}} {...}{...}
      2. XML   <tool_call><function=nombre><parameter=clave>valor</parameter></function></tool_call>
    Esto corrige el bug donde HERMATRON mostraba el comando como texto
    sin ejecutarlo (pantallazo con '<tool_call>' pegado).
    """
    objs = []
    
    # ── Formato 2: <tool_call><function=...><parameter=...>...</parameter></function></tool_call> ──
    import re
    # Primero buscar los bloques COMPLETOS con <tool_call> (si existen, no volver a
    # matchear su <function> interno en el segundo regex para no duplicar).
    bloques_completos = re.findall(
        r'<tool_call>\s*<function=([a-zA-Z0-9_]+)>(.*?)</function>\s*</tool_call>',
        texto, re.DOTALL
    )
    texto_sin_completos = re.sub(
        r'<tool_call>\s*<function=([a-zA-Z0-9_]+)>.*?</function>\s*</tool_call>',
        '', texto, flags=re.DOTALL
    )
    patron_xml = bloques_completos + re.findall(
        r'<function=([a-zA-Z0-9_]+)>(.*?)</function>',
        texto_sin_completos, re.DOTALL
    )
    for nombre_fun, cuerpo in patron_xml:
        try:
            params = {}
            for m_param in re.finditer(r'<parameter=([a-zA-Z0-9_]+)>\s*(.*?)\s*</parameter>', cuerpo, re.DOTALL):
                clave, valor = m_param.group(1), m_param.group(2).strip()
                params[clave] = valor
            # Si no usó <parameter>, asumir que el cuerpo entero es el valor de 'comando' o 'query'
            if not params:
                cuerpo_limpio = re.sub(r'<[^>]+>', '', cuerpo).strip()
                if cuerpo_limpio:
                    clave_default = "comando" if nombre_fun in ("ejecutar_comando_pc", "ejecutar_codigo_python") else "query"
                    params[clave_default] = cuerpo_limpio
            if params:
                objs.append({
                    "type": "function",
                    "function": {"name": nombre_fun, "arguments": json.dumps(params)}
                })
                print(f"[TOOL-XML] ✅ Parseada llamada <tool_call> → {nombre_fun}")
        except Exception as e:
            print(f"[TOOL-XML] Error parseando <tool_call>: {e}")
    
    # ── Formato 1: JSON concatenado {...}{...} ──
    depth = 0
    start = -1
    in_string = False
    escape = False
    
    for i, char in enumerate(texto):
        if char == '"' and not escape:
            in_string = not in_string
            
        if not in_string:
            if char == '{':
                if depth == 0: start = i
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0 and start != -1:
                    try:
                        # Limpiamos escapes innecesarios a veces generados por el LLM
                        blob = texto[start:i+1]
                        # Intento 1: tal cual
                        try:
                            obj = json.loads(blob)
                        except json.JSONDecodeError:
                            # Intento 2: quitando escapes extra
                            try:
                                obj = json.loads(blob.replace('\\"', '\"').replace('\\n', '\n'))
                            except:
                                # Intento 3: el hack original
                                obj = json.loads(blob.replace('\"', '"'))
                        if isinstance(obj, dict) and "type" in obj and obj.get("type") == "function":
                            objs.append(obj)
                    except Exception as e:
                        print(f"Error parseando posible JSON tool call: {e}")
                    start = -1
                    
        if char == '\\\\':
            escape = not escape
        else:
            escape = False
            
    return objs

def _ejecutar_comando_windows_no_bloqueante(comando: str) -> dict:
    """
    Ejecuta comandos en Windows sin colgar la API.
    - Para apps GUI/long-running: lanza en background (Popen) y retorna de una.
    - Para comandos cortos: intenta capturar salida con timeout.
    """
    comando = (comando or "").strip()
    if not comando:
        return {"exito": False, "error": "Comando vacío."}

    cmd_lower = comando.lower()
    # Caso especial: Notepad con archivo -> asegurar ruta válida y comillas correctas.
    # Mucho del "no se puede encontrar la ruta" viene de rutas sin comillas o carpetas inexistentes.
    if cmd_lower.startswith("notepad"):
        # Extraer argumento (ruta) de forma tolerante
        arg = comando[len("notepad"):].strip()
        if arg:
            # Quitar comillas externas si las hay
            if (arg.startswith('"') and arg.endswith('"')) or (arg.startswith("'") and arg.endswith("'")):
                arg = arg[1:-1]
            arg = os.path.expandvars(os.path.expanduser(arg.strip()))

            try:
                p = Path(arg)
                # Si parece ruta a archivo (tiene sufijo o termina en .txt/.log/etc), intentamos crear carpeta + archivo vacío
                if p.suffix or (str(p).lower().endswith((".txt", ".md", ".log", ".json", ".py"))):
                    if p.parent and not p.parent.exists():
                        p.parent.mkdir(parents=True, exist_ok=True)
                    if not p.exists():
                        p.touch(exist_ok=True)

                # Re-armar comando con start "" para evitar el bug de START (primer string quoteado = título)
                comando = f'start "" notepad "{str(p)}"'
                cmd_lower = comando.lower()
            except Exception:
                # Si algo falla, seguimos con el comando original
                pass

    gui_keywords = ("notepad", "mspaint", "calc", "explorer", "chrome", "msedge", "firefox")
    parece_gui = cmd_lower.startswith("start ") or any(k in cmd_lower for k in gui_keywords) or cmd_lower.endswith(".exe")

    # Si es GUI o parece long-running, no bloquear: lanzar detached.
    if parece_gui:
        try:
            # Fix común de Windows: start "C:\ruta con espacios\file.txt" trata eso como título.
            # Si el comando empieza con start y el primer argumento está entre comillas, inyectamos título vacío.
            if cmd_lower.startswith("start ") and comando.strip().startswith('start "') and not comando.lower().startswith('start ""'):
                comando = 'start "" ' + comando.strip()[len("start "):]

            creationflags = 0
            if os.name == "nt":
                creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            subprocess.Popen(
                comando,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                creationflags=creationflags,
                close_fds=True,
            )
            return {"exito": True, "mensaje": "Comando lanzado en background."}
        except Exception as e:
            return {"exito": False, "error": str(e)}

    # Caso normal: comando corto con salida + timeout.
    try:
        res = subprocess.run(
            comando,
            shell=True,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        salida = (res.stdout or "").strip()
        error = (res.stderr or "").strip()
        payload = {"exito": True, "mensaje": "Comando ejecutado."}
        if salida:
            payload["stdout"] = salida
        if error:
            payload["stderr"] = error
        return payload
    except subprocess.TimeoutExpired:
        try:
            subprocess.Popen(
                comando,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                close_fds=True,
            )
            return {"exito": True, "mensaje": "Comando tardó; se dejó corriendo en background."}
        except Exception as e:
            return {"exito": False, "error": str(e)}
    except Exception as e:
        return {"exito": False, "error": str(e)}

# ==========================================
# EL LAVADO DE CEREBRO (PROMPT ESTRICTO)
# ==========================================
def _detectar_plataforma() -> str:
    """Detecta el sistema operativo REAL donde corre HERMATRON sin asumir nada.
    Soporta: Windows, macOS y CUALQUIER distribución de Linux (Ubuntu, Fedora,
    Debian, Arch, Mint, etc.) leyendo /etc/os-release cuando existe.
    """
    import platform as _platform
    
    sistema = _platform.system() or ""
    
    # ── Windows ──
    if sistema == "Windows" or sys.platform.startswith("win"):
        version = _platform.release() or ""
        return (
            f"Windows ({version}). Usa comandos CMD: ver, dir, systeminfo, whoami. "
            "NUNCA uses 'uname', 'ls', 'pwd' ni 'cat' (son de Linux/macOS). "
            "El handler ya lanza apps GUI sin bloquear."
        )
    
    # ── macOS ──
    if sistema == "Darwin" or sys.platform == "darwin":
        version = _platform.mac_ver()[0] or ""
        return (
            f"macOS ({version}). Usa comandos POSIX: uname -a, ls, pwd, cat, sw_vers, whoami. "
            "NUNCA uses 'ver', 'dir' ni 'systeminfo' (son de Windows)."
        )
    
    # ── Linux (cualquier distribución) ──
    if sistema == "Linux" or sys.platform.startswith("linux"):
        distro = ""
        # Leer /etc/os-release: identifica Ubuntu, Fedora, Debian, Arch, Mint, etc.
        try:
            with open("/etc/os-release", "r", encoding="utf-8") as f:
                for linea in f:
                    if linea.startswith("PRETTY_NAME="):
                        distro = linea.split("=", 1)[1].strip().strip('"').strip("'")
                        break
        except Exception:
            pass
        if not distro:
            distro = _platform.libc_ver()[0] or "Linux"
        return (
            f"Linux — distribución: {distro}. Usa comandos POSIX: uname -a, ls, pwd, cat, whoami, free -h. "
            "Para saber la distribución exacta ejecuta: cat /etc/os-release o lsb_release -a. "
            "NUNCA uses 'ver', 'dir' ni 'systeminfo' (son de Windows). "
            "NO asumas que es Ubuntu: comprueba /etc/os-release antes de afirmar la distribución."
        )
    
    # ── Otro / desconocido ──
    return (
        f"Sistema desconocido (platform.system()={sistema!r}). "
        "Detéctalo ANTES de responder ejecutando con la herramienta de comandos: "
        "en Windows 'ver', en macOS/Linux 'uname -a'."
    )


PLATAFORMA_ACTUAL = _detectar_plataforma()

SYSTEM_PROMPT = f"""Eres HERMATRON, un Estudio de Inteligencia Artificial Multimodal y Asistente Creativo.
PLATAFORMA DEL SISTEMA DONDE CORRES AHORA MISMO: {PLATAFORMA_ACTUAL}
Esta información es VERDADERA y actual. Úsala SIEMPRE para elegir los comandos correctos: si preguntan qué sistema operativo tiene el usuario, responde con el resultado real de 'uname -a' (Linux) o 'ver' (Windows) ejecutado con la herramienta, sin inventar.
ATENCIÓN: Tienes capacidades avanzadas tanto en la nube como en el sistema local.
TUS CAPACIDADES PRINCIPALES:
1. ERES DIRECTOR DE CINE: Puedes crear videos cinematográficos completos (múltiples escenas, guion, voz, música).
2. ERES ARTISTA VISUAL (Nano Banana): Puedes generar imágenes individuales de alta calidad instantáneamente con 'generar_imagen'.
3. DIFERENCIACIÓN CRÍTICA: Una cosa son las instrucciones para un VÍDEO (que requiere estructura de escenas y tiempo) y otra las instrucciones para una IMAGEN (que es una creación estática inmediata). No confundas los parámetros de video con los de imagen.
4. REGLA ABSOLUTA DE IMÁGENES: Si el usuario te pide una imagen o que "creas" algo visual (como una 'colegiala', un 'paisaje' o un 'Nano Banana'), DEBES llamar a la función 'generar_imagen' PRIMERO. Está PROHIBIDO describir una imagen sin haberla generado antes.
5. REGLA DE ORO DE RESPUESTA: Cuando generes una imagen con la herramienta, DEBES incluirla obligatoriamente en tu respuesta final usando el formato Markdown: ![Descripción](URL). Ejemplo: ![Colegiala](/video_files/gen_123.jpg).
6. TIENES ACCESO AL PC: Puedes usar comandos, Python, y navegar/crear/copiar/mover/eliminar carpetas y archivos del sistema (listar_carpeta, leer_archivo, escribir_archivo, buscar_archivos, etc.).
7. Búsqueda web: Datos en tiempo real.
8. ACCESO A GITHUB: Puedes buscar repositorios públicos, listar su contenido, leer código de cualquier repo y descargarlos a la PC (todo gratis vía la API pública de GitHub).
9. MEMORIA DE CONOCIMIENTO: Tienes una base de conocimiento permanente en SQLite. Aprende y guarda lo que descubras (guardar_conocimiento), consúltala (buscar_conocimiento) y actualízala desde la web (actualizar_conocimiento_web).
10. AUTO-REPARACIÓN: Si algo falla, puedes leer tu propio código (leer_codigo_proyecto) y diagnosticar el error proponiendo un parche (proponer_arreglo). NUNCA modifiques tus propios archivos sin aprobación explícita del usuario.
REGLA DE ORO (TU FORMA DE HABLAR): 
Exprésate siempre con profunda elocuencia y riqueza de vocabulario. Usa metáforas, analogías vívidas y parábolas. Tu forma de hablar debe ser poética, persuasiva y reflexiva, pero sin perder tu tono cercano, carismático y colombiano ("mi pana"). Eres sabio, creativo y magnético."""

app = FastAPI(title="HERMATRON API", version="6.1.0")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

VIDEOS_DIR = BASE_DIR / "videos"
OTROS_DIR = BASE_DIR / "otros"
AUDIO_DIR_PATH = BASE_DIR / "audio"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
if not VIDEOS_DIR.exists(): VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
if not OTROS_DIR.exists(): OTROS_DIR.mkdir(parents=True, exist_ok=True)
if not AUDIO_DIR_PATH.exists(): AUDIO_DIR_PATH.mkdir(exist_ok=True)
if not STATIC_DIR.exists(): STATIC_DIR.mkdir(exist_ok=True)
if not TEMPLATES_DIR.exists(): TEMPLATES_DIR.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/video_files", StaticFiles(directory=str(VIDEOS_DIR)), name="video_files")
app.mount("/otros_files", StaticFiles(directory=str(OTROS_DIR)), name="otros_files")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Middleware para capturar ERRORES CRÍTICOS y verlos en la consola
@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        print(f"🛑 [ERROR CRÍTICO DEL SERVIDOR] {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"detail": f"Error interno: {str(e)}"})

client = None
openrouter_client = None
qwen3_client = None

# --- Cliente Groq ---
if GROQ_API_KEY:
    try:
        client = Groq(api_key=GROQ_API_KEY)
        print("✅ Cliente Groq inicializado correctamente.")
    except Exception as e:
        print(f"❌ Error inicializando cliente Groq: {e}")
else:
    print("⚠️ GROQ_API_KEY no detectada. El sistema funcionará en modo limitado.")

# --- Cliente OpenRouter (compatible con OpenAI SDK) ---
if OPENROUTER_API_KEY:
    try:
        from openai import AsyncOpenAI
        openrouter_client = AsyncOpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url=OPENROUTER_BASE_URL,
            default_headers={
                "HTTP-Referer": "https://hermatron.onrender.com",
                "X-Title": "HERMATRON AI",
            }
        )
        print(f"✅ Cliente OpenRouter inicializado. Modelo: {OPENROUTER_MODEL}")
    except Exception as e:
        print(f"❌ Error inicializando cliente OpenRouter: {e}")
else:
    print("⚠️ OPENROUTER_API_KEY no detectada.")

# --- Cliente Qwen 3 (Agente interno GRATIS: Ollama local u OpenRouter :free) ---
# Qwen 3 tiene tool calling nativo, por lo que HERMATRON le da acceso al PC
# (ejecutar Python, mover archivos/carpetas, comandos) y a internet.
if QWEN3_ENABLED and QWEN3_BASE_URL:
    try:
        from openai import AsyncOpenAI
        qwen3_client = AsyncOpenAI(
            api_key=QWEN3_API_KEY or "ollama-local",
            base_url=QWEN3_BASE_URL,
            default_headers={
                "HTTP-Referer": "https://hermatron.onrender.com",
                "X-Title": "HERMATRON AI (Qwen3)",
            },
        )
        print(f"✅ Cliente Qwen 3 inicializado. Modelo: {QWEN3_MODEL} @ {QWEN3_BASE_URL}")
    except Exception as e:
        print(f"❌ Error inicializando cliente Qwen 3: {e}")
else:
    print("⚠️ Qwen 3 desactivado (QWEN3_ENABLED=False o sin base URL).")

# Proveedor activo para el chat
if LLM_PROVIDER == "openrouter" and openrouter_client:
    print(f"🧠 [LLM] Proveedor activo: OpenRouter ({OPENROUTER_MODEL})")
elif LLM_PROVIDER == "qwen3" and qwen3_client:
    print(f"🧠 [LLM] Proveedor activo: Qwen 3 ({QWEN3_MODEL}) — agente interno gratis")
else:
    print(f"🧠 [LLM] Proveedor activo: Groq ({GROQ_MODEL})")

# Evitar caché agresivo en desarrollo (principalmente JS/CSS)
@app.middleware("http")
async def no_cache_static(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path or ""
    if path.startswith("/static/") or path in ["/", "/videos"]:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

class ChatRequest(BaseModel):
    prompt: str
    proyecto: Optional[str] = None
    generar_audio: Optional[bool] = False
    # Calidad/engine sugerido desde la UI (ej: "edge-tts", "elevenlabs", "local")
    calidad_audio: Optional[str] = None
    voz_id: Optional[str] = None
    modo: Optional[str] = "general"
    conversacion_id: Optional[str] = "default"

class VisionChatRequest(BaseModel):
    prompt: str
    modo: Optional[str] = "general"
    conversacion_id: Optional[str] = "default"
    generar_audio: Optional[bool] = False
    imagenes: list  # Usamos list genérico para ver qué llega exactamente
    calidad_audio: Optional[str] = "edge-tts"
    voz_id: Optional[str] = None
    conversacion_id: Optional[str] = "default"

class ChatResponse(BaseModel):
    respuesta: str
    audio_generado: bool = False
    audio_id: Optional[str] = None

# ==========================================
# HERRAMIENTAS (Internet + PC)
# ==========================================
herramientas_groq = [
    {
        "type": "function",
        "function": {
            "name": "buscar_en_internet",
            "description": "Busca en Google datos, noticias o ciencia.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_suscriptores_youtube",
            "description": "Obtiene el texto de suscriptores de un canal de YouTube (sin API).",
            "parameters": {
                "type": "object",
                "properties": {"canal": {"type": "string"}},
                "required": ["canal"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "descargar_pagina_web",
            "description": "Descarga texto de una URL.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generar_imagen",
            "description": "Genera una imagen artística usando IA a partir de una descripción.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Descripción detallada de la imagen en inglés para mejor calidad."},
                    "formato": {"type": "string", "enum": ["16:9", "9:16", "1:1"], "default": "16:9"}
                },
                "required": ["prompt"]
            }
        }
    },
]

if ALLOW_SYSTEM_COMMANDS:
    herramientas_groq.extend([
        {
            "type": "function",
            "function": {
                "name": "ejecutar_codigo_python",
                "description": "Ejecuta un script de Python localmente en la máquina del usuario. Retorna la salida estándar (stdout) o el error (stderr).",
                "parameters": {
                    "type": "object",
                    "properties": {"codigo": {"type": "string", "description": "Código de Python a ejecutar."}},
                    "required": ["codigo"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "ejecutar_comando_pc",
                "description": "Ejecuta un comando en Windows. Usa 'start notepad' para bloc de notas, 'explorer' para carpetas.",
                "parameters": {
                    "type": "object",
                    "properties": {"comando": {"type": "string", "description": "Comando CMD de Windows"}},
                    "required": ["comando"]
                }
            }
        }
    ])

# ==========================================
# HERRAMIENTAS v6.2 (Servicios Avanzados — 100% gratis)
# ==========================================

def _tool(nombre, descripcion, propiedades, requeridos=None):
    """Helper para definir una herramienta (función) del agente."""
    return {
        "type": "function",
        "function": {
            "name": nombre,
            "description": descripcion,
            "parameters": {
                "type": "object",
                "properties": propiedades,
                "required": requeridos or [],
            },
        },
    }


# ── GitHub (API pública gratuita, siempre disponible) ──
herramientas_groq.extend([
    _tool("github_buscar_repos", "Busca repositorios públicos en GitHub (API gratuita, sin token).",
          {"query": {"type": "string", "description": "Términos de búsqueda (ej: 'speech to text python')"},
           "max_resultados": {"type": "integer", "default": 10}}, ["query"]),
    _tool("github_leer_archivo", "Lee el contenido de un archivo de cualquier repositorio público de GitHub.",
          {"repo": {"type": "string", "description": "Formato 'usuario/repo' (ej: 'openai/whisper')"},
           "ruta": {"type": "string", "description": "Ruta del archivo dentro del repo (ej: 'README.md')"},
           "rama": {"type": "string", "default": "main"}}, ["repo", "ruta"]),
    _tool("github_listar_contenido", "Lista archivos y carpetas de un repositorio o subcarpeta de GitHub.",
          {"repo": {"type": "string", "description": "Formato 'usuario/repo'"},
           "ruta": {"type": "string", "default": "", "description": "Carpeta dentro del repo (vacío = raíz)"},
           "rama": {"type": "string", "default": "main"}}, ["repo"]),
    _tool("github_buscar_codigo", "Busca código dentro de repositorios públicos de GitHub (requiere GITHUB_TOKEN en .env).",
          {"query": {"type": "string"}, "max_resultados": {"type": "integer", "default": 10}}, ["query"]),
])

# ── Sistema de archivos del PC (requiere ALLOW_FILE_ACCESS=True) ──
if ALLOW_FILE_ACCESS:
    herramientas_groq.extend([
        _tool("listar_carpeta", "Lista el contenido de una carpeta del PC (archivos y subcarpetas con tamaño y fecha).",
              {"ruta": {"type": "string", "description": "Ruta de la carpeta a listar"}}, ["ruta"]),
        _tool("leer_archivo", "Lee el contenido de un archivo de texto del PC.",
              {"ruta": {"type": "string"}, "max_lineas": {"type": "integer", "default": 300}}, ["ruta"]),
        _tool("escribir_archivo", "Crea o sobrescribe un archivo de texto en el PC (crea carpetas si faltan).",
              {"ruta": {"type": "string"}, "contenido": {"type": "string"}}, ["ruta", "contenido"]),
        _tool("crear_carpeta", "Crea una carpeta nueva en el PC (y sus carpetas padre si es necesario).",
              {"ruta": {"type": "string"}}, ["ruta"]),
        _tool("copiar_elemento", "Copia un archivo o carpeta a otra ubicación.",
              {"origen": {"type": "string"}, "destino": {"type": "string"}}, ["origen", "destino"]),
        _tool("mover_elemento", "Mueve o renombra un archivo o carpeta.",
              {"origen": {"type": "string"}, "destino": {"type": "string"}}, ["origen", "destino"]),
        _tool("eliminar_elemento", "Elimina un archivo o carpeta (las rutas críticas de HERMATRON están protegidas).",
              {"ruta": {"type": "string"}}, ["ruta"]),
        _tool("buscar_archivos", "Busca archivos o carpetas recursivamente por patrón (ej: '*.py', 'video*').",
              {"ruta": {"type": "string"}, "patron": {"type": "string", "default": "*"}, "max_resultados": {"type": "integer", "default": 50}}, ["ruta"]),
        _tool("info_ruta", "Muestra información detallada de un archivo o carpeta (tamaño, fechas, tipo).",
              {"ruta": {"type": "string"}}, ["ruta"]),
        _tool("github_descargar_repo", "Descarga un repositorio público de GitHub a una carpeta local del PC (ZIP, gratis).",
              {"repo": {"type": "string", "description": "Formato 'usuario/repo'"},
               "destino": {"type": "string", "description": "Carpeta local donde guardarlo"},
               "rama": {"type": "string", "default": "main"}}, ["repo", "destino"]),
    ])

# ── Base de conocimiento + Auto-reparación (siempre disponibles) ──
herramientas_groq.extend([
    _tool("guardar_conocimiento", "Guarda o actualiza una entrada en la memoria permanente de conocimiento de HERMATRON (aprende algo nuevo).",
          {"titulo": {"type": "string"}, "contenido": {"type": "string"},
           "categoria": {"type": "string", "default": "general"}, "fuente": {"type": "string", "default": ""}}, ["titulo", "contenido"]),
    _tool("buscar_conocimiento", "Busca en la base de conocimiento permanente de HERMATRON.",
          {"consulta": {"type": "string"}, "limit": {"type": "integer", "default": 10}}, ["consulta"]),
    _tool("actualizar_conocimiento_web", "Investiga un tema actual en la web y guarda lo aprendido en la memoria permanente (memoria auto-actualizable).",
          {"tema": {"type": "string"}, "num_resultados": {"type": "integer", "default": 5}}, ["tema"]),
    _tool("leer_codigo_proyecto", "Lee el código fuente del propio proyecto HERMATRON para auto-diagnóstico (ej: 'app/main.py').",
          {"archivo": {"type": "string"}}, ["archivo"]),
    _tool("proponer_arreglo", "Diagnostica un error del propio HERMATRON y PROPONE un parche. NUNCA aplica cambios sin aprobación (modo propose-only).",
          {"error": {"type": "string"}, "contexto": {"type": "string", "default": ""},
           "archivo": {"type": "string", "default": ""}}, ["error"]),
])


async def _generar_imagen_tool(argumentos: dict) -> dict:
    """Genera una imagen con Nano Banana (Gemini) — único creador de imágenes de HERMATRON.
    Si la cuota de Gemini está agotada, usa respaldo de emergencia con aviso claro."""
    prompt_img = argumentos.get("prompt", "")
    formato = argumentos.get("formato", "16:9")
    print(f"🎨 [IMAGEN] Generando con Nano Banana: {prompt_img}")
    import uuid
    img_id = f"gen_{uuid.uuid4().hex[:8]}"
    img_path = VIDEOS_DIR / f"{img_id}.jpg"
    res_map = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1024, 1024)}
    w, h = res_map.get(formato, (1920, 1080))
    try:
        from app.config import GOOGLE_API_KEY, GEMINI_SAFETY_MODE
        success = False
        if GOOGLE_API_KEY and not GEMINI_SAFETY_MODE:
            success = await generador_video._generar_imagen_gemini(prompt_img, str(img_path), w, h)
        if not success:
            print(f"⚠️ [IMAGEN] Nano Banana sin cuota — usando respaldo de emergencia para: {prompt_img[:50]}")
            success = await generador_video._generar_imagen_pollinations(prompt_img, str(img_path), w, h)
        if success:
            return {"status": "success", "url": f"/video_files/{img_id}.jpg", "mensaje": "Imagen generada con éxito."}
        return {"status": "error", "mensaje": "No se pudo generar la imagen (cuota de Gemini agotada)."}
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}


async def ejecutar_herramienta(nombre_funcion: str, argumentos: dict) -> str:
    """
    Ejecuta CUALQUIER herramienta del agente HERMATRON (nativas + v6.2)
    y devuelve el resultado como JSON string listo para el LLM.
    """
    argumentos = argumentos or {}
    try:
        # ── Herramientas nativas ──
        if nombre_funcion == "buscar_en_internet":
            return json.dumps(buscador.buscar(argumentos.get("query", "")))
        elif nombre_funcion == "obtener_suscriptores_youtube":
            return json.dumps(buscador.obtener_suscriptores_youtube(argumentos.get("canal", "")))
        elif nombre_funcion == "descargar_pagina_web":
            return json.dumps(buscador.descargar_contenido(argumentos.get("url", "")))
        elif nombre_funcion == "ejecutar_codigo_python":
            codigo = argumentos.get("codigo", "")
            print(f"🐍 [PYTHON] Ejecutando código de {len(codigo)} bytes")
            return json.dumps(_ejecutar_codigo_python(codigo))
        elif nombre_funcion == "ejecutar_comando_pc":
            comando = argumentos.get("comando", "")
            print(f"💻 [PC] Ejecutando: {comando}")
            return json.dumps(_ejecutar_comando_windows_no_bloqueante(comando))
        elif nombre_funcion == "generar_imagen":
            return json.dumps(await _generar_imagen_tool(argumentos))

        # ── v6.2: Sistema de archivos ──
        elif nombre_funcion == "listar_carpeta":
            return json.dumps(listar_carpeta(argumentos.get("ruta") or str(BASE_DIR)))
        elif nombre_funcion == "leer_archivo":
            return json.dumps(leer_archivo(argumentos.get("ruta", ""), argumentos.get("max_lineas", 300)))
        elif nombre_funcion == "escribir_archivo":
            return json.dumps(escribir_archivo(argumentos.get("ruta", ""), argumentos.get("contenido", "")))
        elif nombre_funcion == "crear_carpeta":
            return json.dumps(crear_carpeta(argumentos.get("ruta", "")))
        elif nombre_funcion == "copiar_elemento":
            return json.dumps(copiar_elemento(argumentos.get("origen", ""), argumentos.get("destino", "")))
        elif nombre_funcion == "mover_elemento":
            return json.dumps(mover_elemento(argumentos.get("origen", ""), argumentos.get("destino", "")))
        elif nombre_funcion == "eliminar_elemento":
            return json.dumps(eliminar_elemento(argumentos.get("ruta", "")))
        elif nombre_funcion == "buscar_archivos":
            return json.dumps(buscar_archivos(argumentos.get("ruta") or str(BASE_DIR), argumentos.get("patron", "*"), argumentos.get("max_resultados", 50)))
        elif nombre_funcion == "info_ruta":
            return json.dumps(info_ruta(argumentos.get("ruta", "")))

        # ── v6.2: GitHub ──
        elif nombre_funcion == "github_buscar_repos":
            return json.dumps(await github_buscar_repos(argumentos.get("query", ""), argumentos.get("max_resultados", 10)))
        elif nombre_funcion == "github_leer_archivo":
            return json.dumps(await github_leer_archivo(argumentos.get("repo", ""), argumentos.get("ruta", ""), argumentos.get("rama", "main")))
        elif nombre_funcion == "github_listar_contenido":
            return json.dumps(await github_listar_contenido(argumentos.get("repo", ""), argumentos.get("ruta", ""), argumentos.get("rama", "main")))
        elif nombre_funcion == "github_descargar_repo":
            return json.dumps(await github_descargar_repo(argumentos.get("repo", ""), argumentos.get("destino", ""), argumentos.get("rama", "main")))
        elif nombre_funcion == "github_buscar_codigo":
            return json.dumps(await github_buscar_codigo(argumentos.get("query", ""), argumentos.get("max_resultados", 10)))

        # ── v6.2: Base de conocimiento ──
        elif nombre_funcion == "guardar_conocimiento":
            return json.dumps(await guardar_conocimiento(argumentos.get("titulo", ""), argumentos.get("contenido", ""), argumentos.get("categoria", "general"), argumentos.get("fuente", "")))
        elif nombre_funcion == "buscar_conocimiento":
            return json.dumps(await buscar_conocimiento(argumentos.get("consulta", ""), argumentos.get("limit", 10)))
        elif nombre_funcion == "actualizar_conocimiento_web":
            return json.dumps(await actualizar_conocimiento_web(argumentos.get("tema", ""), argumentos.get("num_resultados", 5)))

        # ── v6.2: Auto-reparación (propose-only) ──
        elif nombre_funcion == "leer_codigo_proyecto":
            return json.dumps(leer_codigo_proyecto(argumentos.get("archivo", "")))
        elif nombre_funcion == "proponer_arreglo":
            return json.dumps(await proponer_arreglo(argumentos.get("error", ""), argumentos.get("contexto", ""), argumentos.get("archivo", ""), client))

        else:
            return json.dumps({"status": "error", "mensaje": f"Herramienta desconocida: {nombre_funcion}"})
    except Exception as e:
        print(f"❌ [HERRAMIENTA ERROR] {nombre_funcion}: {e}")
        return json.dumps({"status": "error", "mensaje": str(e)})


# ==========================================
# ENDPOINTS PRINCIPALES
# ==========================================

@app.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    from .config import HERMATRON_ADMIN_MODE
    if HERMATRON_ADMIN_MODE:
        return RedirectResponse(url="/chat")
    return templates.TemplateResponse(
        request=request,
        name="landing.html",
        context={"request": request, "title": "HERMATRON - Inteligencia Artificial Multimodal"},
    )

@app.get("/legales", response_class=HTMLResponse)
async def legales(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="legales.html",
        context={"request": request, "title": "HERMATRON - Legales y Políticas"}
    )

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    from .config import HERMATRON_ADMIN_MODE
    if HERMATRON_ADMIN_MODE:
        return RedirectResponse(url="/chat")
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"request": request, "title": "HERMATRON - Iniciar Sesión"}
    )

@app.post("/api/register")
async def api_register(username: str = Form(...), password: str = Form(...)):
    # username is used for email
    success = await memoria.crear_usuario(username, auth.hash_password(password))
    if not success:
        raise HTTPException(status_code=400, detail="El correo ya está registrado.")
    
    # Log in automatically
    response = JSONResponse(content={"success": True})
    await auth.login_user(response, username, password)
    return response

@app.post("/api/login")
async def api_login(username: str = Form(...), password: str = Form(...)):
    response = JSONResponse(content={"success": True})
    success = await auth.login_user(response, username, password)
    if not success:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas.")
    return response

@app.post("/api/logout")
async def api_logout(request: Request):
    response = JSONResponse(content={"success": True})
    await auth.logout_user(response, request)
    return response

from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, RedirectResponse

@app.get("/chat")
async def chat_app(request: Request, current_user: dict = Depends(auth.get_current_user())):
    if not current_user:
        return RedirectResponse(url="/login")
        
    try:
        static_version = int((BASE_DIR / "static" / "app.js").stat().st_mtime)
    except Exception:
        static_version = int(time.time())
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request, 
            "title": "HERMATRON - Chat Multiusos", 
            "static_version": static_version,
            "user": current_user
        },
    )

@app.get("/videos")
async def video_studio(request: Request, current_user: dict = Depends(auth.get_current_user())):
    if not current_user:
        return RedirectResponse(url="/login")
        
    return templates.TemplateResponse(
        request=request, 
        name="video-studio.html", 
        context={"request": request, "title": "HERMATRON - Estudio de Video", "user": current_user}
    )

@app.get("/escenografias")
async def escenografias_page(request: Request, current_user: dict = Depends(auth.get_current_user())):
    if not current_user:
        return RedirectResponse(url="/login")
        
    return RedirectResponse(url="/videos#scenographyManagerContainer")

@app.post("/api/chat", response_model=ChatResponse)
async def chat(chat_request: ChatRequest):
    # Proveedores disponibles: Groq (principal) + Qwen 3 (agente interno gratis) + OpenRouter (respaldo).
    if not client and not openrouter_client and not qwen3_client:
        raise HTTPException(status_code=500, detail="Ningún proveedor LLM configurado (Groq/Qwen3/OpenRouter)")
    print(f"[CHAT] generar_audio={chat_request.generar_audio} calidad_audio={chat_request.calidad_audio} voz_id={chat_request.voz_id}")
    
    if chat_request.conversacion_id != "default":
        conversaciones = await memoria.obtener_conversaciones()
        if not any(c['id'] == chat_request.conversacion_id for c in conversaciones):
            titulo = chat_request.prompt[:30] + ("..." if len(chat_request.prompt) > 30 else "")
            await memoria.crear_conversacion(chat_request.conversacion_id, titulo)
            
    await memoria.agregar_mensaje("user", chat_request.prompt, conversacion_id=chat_request.conversacion_id)
    historial = await memoria.obtener_historial(limit=10, conversacion_id=chat_request.conversacion_id)
    
    mensajes_groq = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in historial: mensajes_groq.append({"role": m["role"], "content": m["content"]})
    
    try:
        # Forzamos un formato estricto en el prompt para evitar que Llama 3.3 alucine etiquetas HTML
        mensajes_groq.append({
            "role": "system", 
            "content": "IMPORTANTE: NUNCA uses etiquetas como <function=...>. Si necesitas usar una herramienta, usa SOLO el formato JSON nativo de tool_calls que te provee la API."
        })
        
        # ---- Llamada al LLM: Qwen3 (si es el principal) → Groq → Qwen3 (respaldo) → OpenRouter ----
        mensaje_respuesta = None
        proveedor_usado = "ninguno"

        async def _intentar_qwen3():
            """Llama a Qwen 3 (agente interno gratis) con las mismas herramientas."""
            if not qwen3_client:
                return None
            try:
                completion_q3 = await qwen3_client.chat.completions.create(
                    messages=mensajes_groq, model=QWEN3_MODEL, temperature=0.2, max_tokens=2048,
                    tools=herramientas_groq, tool_choice="auto"
                )
                return completion_q3.choices[0].message
            except Exception as e_q3:
                print(f"⚠️ [QWEN3 FALLÓ] {e_q3}")
                return None

        # 1) Si el proveedor configurado es Qwen 3, intentarlo primero
        if LLM_PROVIDER == "qwen3":
            mensaje_respuesta = await _intentar_qwen3()
            if mensaje_respuesta is not None:
                proveedor_usado = f"Qwen3({QWEN3_MODEL})"

        # 2) Groq (principal por defecto)
        if mensaje_respuesta is None and client:
            try:
                chat_completion = client.chat.completions.create(
                    messages=mensajes_groq, model=GROQ_MODEL, temperature=0.2, max_tokens=2048,
                    tools=herramientas_groq, tool_choice="auto"
                )
                mensaje_respuesta = chat_completion.choices[0].message
                proveedor_usado = "Groq"
            except Exception as e_groq:
                print(f"⚠️ [GROQ FALLÓ] {e_groq} — activando Qwen3/OpenRouter como respaldo...")

        # 3) Qwen 3 como respaldo si Groq no respondió
        if mensaje_respuesta is None and qwen3_client and LLM_PROVIDER != "qwen3":
            mensaje_respuesta = await _intentar_qwen3()
            if mensaje_respuesta is not None:
                proveedor_usado = f"Qwen3({QWEN3_MODEL})"

        # 4) Respaldo final: OpenRouter
        if mensaje_respuesta is None and openrouter_client:
            try:
                completion_or = await openrouter_client.chat.completions.create(
                    messages=mensajes_groq,
                    model=OPENROUTER_MODEL,
                    temperature=0.2,
                    max_tokens=2048,
                )
                mensaje_respuesta = completion_or.choices[0].message
                proveedor_usado = f"OpenRouter({OPENROUTER_MODEL})"
            except Exception as e_or:
                print(f"❌ [OPENROUTER FALLÓ] {e_or}")

        if mensaje_respuesta is None:
            raise HTTPException(status_code=503, detail="Todos los proveedores LLM fallaron. Intenta de nuevo.")

        print(f"🧠 [LLM] Respuesta generada por: {proveedor_usado}")

        if getattr(mensaje_respuesta, 'tool_calls', None):
            print("🧠 [CEREBRO AUTÓNOMO] Activando herramientas...")
            
            assistant_msg = {
                "role": "assistant",
                "content": mensaje_respuesta.content or "",
                "tool_calls": [{"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}} for tc in mensaje_respuesta.tool_calls]
            }
            mensajes_groq.append(assistant_msg)
            
            for tool_call in mensaje_respuesta.tool_calls:
                nombre_funcion = tool_call.function.name
                try: argumentos = json.loads(tool_call.function.arguments)
                except: argumentos = {}
                
                print(f"🧰 [HERRAMIENTA] {nombre_funcion}: {json.dumps(argumentos)[:150]}")
                resultado_datos = await ejecutar_herramienta(nombre_funcion, argumentos)

                mensajes_groq.append({"role": "tool", "tool_call_id": tool_call.id, "name": nombre_funcion, "content": resultado_datos})
            
            # Síntesis post-tool: Qwen3 (si es principal) → Groq → Qwen3 → OpenRouter
            respuesta = ""
            if LLM_PROVIDER == "qwen3" and qwen3_client:
                try:
                    comp_q3 = await qwen3_client.chat.completions.create(
                        messages=mensajes_groq, model=QWEN3_MODEL, temperature=0.7, max_tokens=2048
                    )
                    respuesta = comp_q3.choices[0].message.content
                except Exception as e_q3:
                    print(f"⚠️ [QWEN3 FALLÓ-TOOLS] {e_q3}")
            if not respuesta and client:
                try:
                    chat_completion_final = client.chat.completions.create(messages=mensajes_groq, model=GROQ_MODEL, temperature=0.7, max_tokens=2048)
                    respuesta = chat_completion_final.choices[0].message.content
                except Exception as e_g:
                    print(f"⚠️ [GROQ FALLÓ-TOOLS] {e_g} — usando Qwen3/OpenRouter...")
            if not respuesta and qwen3_client and LLM_PROVIDER != "qwen3":
                comp_q3 = await qwen3_client.chat.completions.create(
                    messages=mensajes_groq, model=QWEN3_MODEL, temperature=0.7, max_tokens=2048
                )
                respuesta = comp_q3.choices[0].message.content
            if not respuesta and openrouter_client:
                comp_final = await openrouter_client.chat.completions.create(
                    messages=mensajes_groq, model=OPENROUTER_MODEL, temperature=0.7, max_tokens=2048
                )
                respuesta = comp_final.choices[0].message.content
        else:
            # Fallback: a veces el modelo devuelve un "tool call" en texto.
            # Si detectamos JSON tipo {"type":"function","name":"...","parameters":{...}},
            # lo ejecutamos manualmente y luego pedimos la respuesta final.
            contenido = mensaje_respuesta.content or ""
            respuesta = contenido
            try:
                # 1) Detectar tool calls en TEXTO (formato <tool_call> XML o JSON) —
                #    corrige el bug donde HERMATRON pegaba el comando sin ejecutarlo.
                tool_calls_texto = _extraer_tool_calls_de_texto(contenido)
                ejecutadas = []
                if tool_calls_texto:
                    for tc in tool_calls_texto:
                        nombre = tc.get("function", {}).get("name")
                        try:
                            params = json.loads(tc.get("function", {}).get("arguments", "{}"))
                        except:
                            params = {}
                        nombres_conocidos = [
                            "buscar_en_internet", "descargar_pagina_web", "ejecutar_comando_pc",
                            "obtener_suscriptores_youtube", "ejecutar_codigo_python", "generar_imagen",
                            "listar_carpeta", "leer_archivo", "escribir_archivo", "crear_carpeta",
                            "copiar_elemento", "mover_elemento", "eliminar_elemento", "buscar_archivos",
                            "info_ruta", "leer_codigo_proyecto",
                            "github_buscar_repos", "github_leer_archivo", "github_listar_contenido",
                            "github_descargar_repo", "github_buscar_codigo",
                            "guardar_conocimiento", "buscar_conocimiento", "actualizar_conocimiento_web",
                            "proponer_arreglo",
                        ]
                        if nombre in nombres_conocidos:
                            print(f"🧰 [TOOL-FALLBACK] Ejecutando {nombre} desde texto")
                            tool_res = json.loads(await ejecutar_herramienta(nombre, params))
                            ejecutadas.append((nombre, tool_res))
                
                if ejecutadas:
                    mensajes_groq.append({"role": "assistant", "content": contenido})
                    resumen_tools = "\n".join(
                        f"[{n}] {json.dumps(r)}" for n, r in ejecutadas
                    )
                    mensajes_groq.append({"role": "user", "content": f"[SISTEMA] Resultados de las herramientas ejecutadas:\n{resumen_tools}\n\nUsa esta información para responder a mi pregunta anterior de forma natural."})
                    resp_fb = ""
                    if LLM_PROVIDER == "qwen3" and qwen3_client:
                        try:
                            comp_q3 = await qwen3_client.chat.completions.create(
                                messages=mensajes_groq, model=QWEN3_MODEL, temperature=0.7, max_tokens=2048
                            )
                            resp_fb = comp_q3.choices[0].message.content
                        except Exception as e_q3:
                            print(f"⚠️ [QWEN3 FALLÓ-FB] {e_q3}")
                    if not resp_fb and client:
                        try:
                            chat_completion_final = client.chat.completions.create(
                                messages=mensajes_groq, model=GROQ_MODEL, temperature=0.7, max_tokens=2048
                            )
                            resp_fb = chat_completion_final.choices[0].message.content
                        except Exception as e_g:
                            print(f"⚠️ [GROQ FALLÓ-FB] {e_g} — usando Qwen3/OpenRouter...")
                    if not resp_fb and qwen3_client and LLM_PROVIDER != "qwen3":
                        comp_q3 = await qwen3_client.chat.completions.create(
                            messages=mensajes_groq, model=QWEN3_MODEL, temperature=0.7, max_tokens=2048
                        )
                        resp_fb = comp_q3.choices[0].message.content
                    if not resp_fb and openrouter_client:
                        comp_fb = await openrouter_client.chat.completions.create(
                            messages=mensajes_groq, model=OPENROUTER_MODEL, temperature=0.7, max_tokens=2048
                        )
                        resp_fb = comp_fb.choices[0].message.content
                    respuesta = resp_fb
                else:
                    # 2) Fallback anterior: JSON suelto con 'name' + 'parameters'
                    start = contenido.find("{")
                    end = contenido.rfind("}")
                    if start != -1 and end != -1:
                        blob = contenido[start:end+1].replace('\\"', '"')
                        tool_obj = json.loads(blob)
                        nombre = tool_obj.get("name")
                        params = tool_obj.get("parameters") or {}
                        
                        # Heurística: si el modelo envía un JSON con 'prompt' pero sin 'name', asumimos que es generar_imagen
                        if not nombre and "prompt" in tool_obj:
                            nombre = "generar_imagen"
                            params = tool_obj
                        
                        nombres_conocidos = [
                            "buscar_en_internet", "descargar_pagina_web", "ejecutar_comando_pc",
                            "obtener_suscriptores_youtube", "ejecutar_codigo_python", "generar_imagen",
                            "listar_carpeta", "leer_archivo", "escribir_archivo", "crear_carpeta",
                            "copiar_elemento", "mover_elemento", "eliminar_elemento", "buscar_archivos",
                            "info_ruta", "leer_codigo_proyecto",
                            "github_buscar_repos", "github_leer_archivo", "github_listar_contenido",
                            "github_descargar_repo", "github_buscar_codigo",
                            "guardar_conocimiento", "buscar_conocimiento", "actualizar_conocimiento_web",
                            "proponer_arreglo",
                        ]
                        if nombre in nombres_conocidos:
                            print(f"🧰 [TOOL-FALLBACK] Ejecutando {nombre} desde texto")
                            tool_res = json.loads(await ejecutar_herramienta(nombre, params))

                            mensajes_groq.append({"role": "assistant", "content": contenido})
                            mensajes_groq.append({"role": "user", "content": f"[SISTEMA] El resultado de la herramienta '{nombre}' fue:\n{json.dumps(tool_res)}\n\nUsa esta información para responder a mi pregunta anterior de forma natural."})
                            resp_fb = ""
                            if LLM_PROVIDER == "qwen3" and qwen3_client:
                                try:
                                    comp_q3 = await qwen3_client.chat.completions.create(
                                        messages=mensajes_groq, model=QWEN3_MODEL, temperature=0.7, max_tokens=2048
                                    )
                                    resp_fb = comp_q3.choices[0].message.content
                                except Exception as e_q3:
                                    print(f"⚠️ [QWEN3 FALLÓ-FB] {e_q3}")
                            if not resp_fb and client:
                                try:
                                    chat_completion_final = client.chat.completions.create(
                                        messages=mensajes_groq, model=GROQ_MODEL, temperature=0.7, max_tokens=2048
                                    )
                                    resp_fb = chat_completion_final.choices[0].message.content
                                except Exception as e_g:
                                    print(f"⚠️ [GROQ FALLÓ-FB] {e_g} — usando Qwen3/OpenRouter...")
                            if not resp_fb and qwen3_client and LLM_PROVIDER != "qwen3":
                                comp_q3 = await qwen3_client.chat.completions.create(
                                    messages=mensajes_groq, model=QWEN3_MODEL, temperature=0.7, max_tokens=2048
                                )
                                resp_fb = comp_q3.choices[0].message.content
                            if not resp_fb and openrouter_client:
                                comp_fb = await openrouter_client.chat.completions.create(
                                    messages=mensajes_groq, model=OPENROUTER_MODEL, temperature=0.7, max_tokens=2048
                                )
                                resp_fb = comp_fb.choices[0].message.content
                            respuesta = resp_fb
            except Exception as e:
                print(f"❌ [TOOL-FALLBACK ERROR] {e}")

        audio_id, audio_gen = None, False
        if chat_request.generar_audio:
            try:
                timestamp = int(time.time())
                nombre_archivo = f"respuesta_{timestamp}.mp3"
                archivo_audio = await generador_voz.generar(
                    respuesta,
                    nombre_archivo,
                    calidad=chat_request.calidad_audio or "edge-tts",
                    voz_id=chat_request.voz_id,
                )
                # Solo reportar audio si el archivo realmente existe:
                # generar() devuelve False cuando TODOS los motores de voz fallan.
                if archivo_audio and Path(str(archivo_audio)).exists():
                    audio_gen, audio_id = True, Path(str(archivo_audio)).name
                else:
                    print("❌ [AUDIO] Ningún motor de voz disponible — respuesta sin audio")
            except Exception as e: print(f"❌ [AUDIO ERROR]: {e}")

        # Guardar la respuesta junto con su audio_id para poder volver a escucharla
        await memoria.agregar_mensaje("assistant", respuesta, conversacion_id=chat_request.conversacion_id, audio_id=audio_id)

        return ChatResponse(respuesta=respuesta, audio_generado=audio_gen, audio_id=audio_id)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error en chat: {str(e)}")

# ==========================================
# MOTOR DE VISIÓN HERMATRON v4.3 (Con Llama 4 Scout)
# ==========================================
@app.post("/api/chat-con-imagenes")
async def chat_con_imagenes(
    prompt: str = Form(...),
    modo: str = Form("general"),
    generar_audio: str = Form("false"),
    calidad_audio: str = Form("edge-tts"),
    voz_id: str = Form(None),
    imagenes: List[str] = Form(...),
    conversacion_id: str = Form("default")
):
    """
    Función de visión usando Llama 4 Scout (modelo actual de Groq).
    """
    print(f"👁️ [VISIÓN v4.3] Reconociendo {len(imagenes)} imágenes...")
    
    gen_audio_bool = str(generar_audio).lower() == "true"
    
    if not client: 
        raise HTTPException(status_code=500, detail="El cerebro de Groq no está listo.")

    # MODELO DE VISIÓN - Usar Llama 4 Scout (multimodal, soporta imágenes)
    MODELO_VISION = GROQ_MODEL_VISION  # meta-llama/llama-4-scout-17b-16e-instruct

    try:
        # Analizar resoluciones
        print("📊 [VISIÓN] Analizando...")
        for i, img in enumerate(imagenes):
            tamano = len(img)
            res = "SD" if tamano < 500000 else "HD" if tamano < 2000000 else "FullHD" if tamano < 4000000 else "2K+" if tamano < 8000000 else "4K"
            print(f"   📷 Imagen {i+1}: {res}")

        # Preparar contenido para Llama 4 Scout
        content = [{"type": "text", "text": f"Analiza esta imagen y describe TODO lo que ves. Sé muy detallado. Pregunta: {prompt}"}]
        
        for img in imagenes:
            if not img.startswith("data:image/"):
                img = f"data:image/jpeg;base64,{img}"
            content.append({"type": "image_url", "image_url": {"url": img}})

        # Usar Llama 4 Scout
        print(f"🧠 [VISIÓN] Usando {MODELO_VISION}...")
        
        try:
            completion = client.chat.completions.create(
                model=MODELO_VISION, 
                messages=[{"role": "user", "content": content}],
                temperature=0.3,
                max_tokens=2048
            )
            respuesta = completion.choices[0].message.content
            print(f"✅ [VISIÓN] Análisis completado")
        except Exception as e:
            error_msg = str(e).lower()
            print(f"⚠️ Error visión: {error_msg[:100]}")
            
            # Si falla, dar mensaje de error claro
            if ("does not support image" in error_msg or "not support vision" in error_msg
                    or "must be a string" in error_msg or "model_not_found" in error_msg):
                respuesta = """El modelo de visión actual no está disponible o tu clave no tiene acceso a él.

Para usar análisis de imágenes, necesitas:
1. Verificar que tu cuenta de Groq tenga acceso a un modelo de visión (ej: Llama 4 Scout o similar)
2. Ir a https://console.groq.com/settings/permissions
3. Habilitar el modelo de visión correspondiente

Mientras tanto, puedo ayudarte si me describes la imagen."""
            else:
                respuesta = f"Error al procesar imagen: {str(e)[:200]}"

        # Memoria
        if conversacion_id != "default":
            conversaciones = await memoria.obtener_conversaciones()
            if not any(c['id'] == conversacion_id for c in conversaciones):
                titulo = prompt[:30] + ("..." if len(prompt) > 30 else "")
                await memoria.crear_conversacion(conversacion_id, titulo)
                
        await memoria.agregar_mensaje("user", f"[VISIÓN] {prompt}", modo, conversacion_id=conversacion_id)

        # Audio
        audio_id = None
        if gen_audio_bool:
            try:
                voz_a_usar = voz_id or TTS_VOICE
                archivo_audio = await generador_voz.generar(
                    texto=respuesta, 
                    calidad=calidad_audio,
                    voz_id=voz_a_usar
                )
                if archivo_audio:
                    audio_id = Path(archivo_audio).name
            except Exception as e:
                print(f"⚠️ Error voz: {e}")

        # Guardar la respuesta junto con su audio_id para poder volver a escucharla
        await memoria.agregar_mensaje("assistant", respuesta, modo, conversacion_id=conversacion_id, audio_id=audio_id)

        return ChatResponse(respuesta=respuesta, audio_generado=bool(audio_id), audio_id=audio_id)

    except Exception as e:
        print(f"🛑 [ERROR VISIÓN] {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error en visión: {str(e)}")

@app.get("/api/audio/{nombre_archivo}")
async def obtener_audio(nombre_archivo: str):
    # 1. Probar en carpeta principal
    ruta = AUDIO_DIR / nombre_archivo
    if ruta.exists():
        return FileResponse(str(ruta), media_type="audio/mpeg", filename=nombre_archivo)
    
    # 2. Probar en carpeta de cache (.cache_voz)
    ruta_cache = AUDIO_DIR / ".cache_voz" / nombre_archivo
    if ruta_cache.exists():
        return FileResponse(str(ruta_cache), media_type="audio/mpeg", filename=nombre_archivo)
        
    raise HTTPException(status_code=404, detail="Audio no encontrado")


@app.get("/api/conversaciones")
async def listar_conversaciones():
    return {"conversaciones": await memoria.obtener_conversaciones()}

@app.delete("/api/conversaciones/{id}")
async def borrar_conversacion(id: str):
    await memoria.eliminar_conversacion(id)
    return {"status": "success"}

@app.get("/api/conversaciones/{id}/mensajes")
async def obtener_mensajes_conversacion(id: str):
    return {"mensajes": await memoria.obtener_historial(limit=100, conversacion_id=id)}


@app.post("/api/limpiar")
async def limpiar_memoria():
    await memoria.limpiar_historial()
    return {"status": "success"}

@app.get("/api/memoria")
async def obtener_memoria(): 
    return {"total_mensajes": await memoria.contar_mensajes(), "ultimos_mensajes": await memoria.obtener_historial(limit=5), "proyectos": await memoria.obtener_todos_proyectos()}

@app.get("/api/voces")
async def listar_voces(): 
    return {"voces": generador_voz.obtener_voces_disponibles()}

# --- AQUÍ ESTÁ LA CORRECCIÓN DEL LETRERO ROJO ---
@app.get("/api/health")
async def health_check(): 
    # Intentar obtener uso de memoria (Linux/Render)
    mem_info = {}
    try:
        if os.name == "posix": # Linux/Render
            # Intentar Cgroups v2 (lo más común ahora)
            if os.path.exists("/sys/fs/cgroup/memory.max"):
                with open("/sys/fs/cgroup/memory.max", "r") as f:
                    mem_info["total"] = f"{int(f.read().strip()) // (1024*1024)} MB"
                with open("/sys/fs/cgroup/memory.current", "r") as f:
                    mem_info["uso_actual"] = f"{int(f.read().strip()) // (1024*1024)} MB"
            elif os.path.exists("/sys/fs/cgroup/memory/memory.limit_in_bytes"):
                # Cgroups v1 (antiguo)
                with open("/sys/fs/cgroup/memory/memory.limit_in_bytes", "r") as f:
                    mem_info["total"] = f"{int(f.read().strip()) // (1024*1024)} MB"
                with open("/sys/fs/cgroup/memory/memory.usage_in_bytes", "r") as f:
                    mem_info["uso_actual"] = f"{int(f.read().strip()) // (1024*1024)} MB"
        else:
            # Fallback para Windows (requiere psutil)
            try:
                import psutil
                vm = psutil.virtual_memory()
                mem_info["total"] = f"{vm.total // (1024*1024)} MB"
                mem_info["disponible"] = f"{vm.available // (1024*1024)} MB"
                mem_info["porcentaje"] = f"{vm.percent}%"
            except ImportError:
                mem_info["status"] = "psutil no instalado (usado para monitoreo local)"
    except Exception as e:
        mem_info["error"] = str(e)

    return {
        "status": "healthy", 
        "groq_configured": bool(GROQ_API_KEY), 
        "model": GROQ_MODEL,
        "vision_model": GROQ_MODEL_VISION,
        "qwen3_configured": bool(qwen3_client is not None),
        "qwen3_model": QWEN3_MODEL if qwen3_client else None,
        "llm_provider": LLM_PROVIDER,
        "sistema": {
            "plataforma": sys.platform,
            "memoria": mem_info
        }
    }

@app.get("/api/modos")
async def obtener_modos():
    """Lista de modos disponibles"""
    return {"modos": listar_modos()}

@app.get("/api/personajes")
async def api_obtener_todos_personajes():
    personajes = await memoria.obtener_todos_personajes()
    return {"personajes": personajes}

@app.post("/api/personajes")
async def api_guardar_personaje(
    nombre: str = Form(...),
    descripcion_fisica: str = Form(...),
    prompt_referencia: str = Form(...),
    imagen: Optional[UploadFile] = File(None)
):
    imagen_path = None
    if imagen and imagen.filename:
        ext = Path(imagen.filename).suffix
        safe_name = "".join(c for c in nombre if c.isalnum() or c in ("-", "_")).rstrip()
        filename = f"{safe_name}{ext}"
        save_path = Path("static/personajes") / filename
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(imagen.file, buffer)
        imagen_path = f"/static/personajes/{filename}"
    else:
        existente = await memoria.obtener_personaje(nombre)
        if existente:
            imagen_path = existente.get("imagen_path")
            
    await memoria.guardar_personaje(nombre, descripcion_fisica, prompt_referencia, imagen_path)
    return {"status": "success", "message": f"Personaje {nombre} guardado correctamente"}

@app.delete("/api/personajes/{nombre}")
async def api_eliminar_personaje(nombre: str):
    existente = await memoria.obtener_personaje(nombre)
    if existente and existente.get("imagen_path"):
        img_path = Path(existente.get("imagen_path").lstrip("/"))
        if img_path.exists():
            try:
                img_path.unlink()
            except:
                pass
    await memoria.eliminar_personaje(nombre)
    return {"status": "success", "message": f"Personaje {nombre} eliminado correctamente"}

@app.put("/api/personajes/{nombre}/voz")
async def api_actualizar_voz_personaje(nombre: str, datos: dict):
    """Actualiza la voz edge-tts asignada a un personaje."""
    nueva_voz = datos.get("voz_edge_tts", "").strip()
    if not nueva_voz:
        return {"status": "error", "message": "Voz no especificada"}
    existente = await memoria.obtener_personaje(nombre)
    if not existente:
        return {"status": "error", "message": f"Personaje '{nombre}' no encontrado"}
    await memoria.actualizar_voz_personaje(nombre, nueva_voz)
    return {"status": "success", "message": f"Voz de {nombre} actualizada a {nueva_voz}"}

@app.get("/api/voces")
async def api_listar_voces():
    """Lista todas las voces edge-tts disponibles en español para los personajes."""
    voces = [
        # 🇨🇴 Colombia
        {"id": "es-CO-GonzaloNeural", "nombre": "Gonzalo (Colombia ♂️ Joven)", "genero": "masculino", "pais": "Colombia"},
        {"id": "es-CO-SalomeNeural",  "nombre": "Salome (Colombia ♀️ Adulta)", "genero": "femenino",  "pais": "Colombia"},
        # 🇲🇽 México
        {"id": "es-MX-JorgeNeural",   "nombre": "Jorge (México ♂️ Joven)",   "genero": "masculino", "pais": "México"},
        {"id": "es-MX-DaliaNeural",   "nombre": "Dalia (México ♀️ Joven)",   "genero": "femenino",  "pais": "México"},
        {"id": "es-MX-LupeNeural",    "nombre": "Lupe (México ♀️ Adulta)",   "genero": "femenino",  "pais": "México"},
        {"id": "es-MX-BeatrizNeural", "nombre": "Beatriz (México ♀️ Adulta)", "genero": "femenino",  "pais": "México"},
        # 🇪🇸 España
        {"id": "es-ES-AlvaroNeural",  "nombre": "Alvaro (España ♂️ Maduro)",  "genero": "masculino", "pais": "España"},
        {"id": "es-ES-LuciaNeural",   "nombre": "Lucia (España ♀️ Joven)",   "genero": "femenino",  "pais": "España"},
        {"id": "es-ES-ElviraNeural",  "nombre": "Elvira (España ♀️ Adulta)",  "genero": "femenino",  "pais": "España"},
        # 🇺🇸 EE.UU (Español Latino)
        {"id": "es-US-AlonsoNeural",  "nombre": "Alonso (EEUU ♂️ Urbano)",    "genero": "masculino", "pais": "EEUU"},
        {"id": "es-US-PalomaNeural",  "nombre": "Paloma (EEUU ♀️ Joven)",     "genero": "femenino",  "pais": "EEUU"},
        # 🇦🇷 Argentina
        {"id": "es-AR-ElenaNeural",   "nombre": "Elena (Argentina ♀️)",       "genero": "femenino",  "pais": "Argentina"},
        {"id": "es-AR-TomasNeural",   "nombre": "Tomás (Argentina ♂️)",      "genero": "masculino", "pais": "Argentina"},
    ]
    return {"voces": voces}

# ── Endpoints de Escenografías (CRUD + Gestión visual) ───────────────────────

@app.get("/api/escenografias")
async def api_obtener_todas_escenografias():
    escenografias = await memoria.obtener_todas_escenografias()
    return {"escenografias": escenografias}

@app.post("/api/escenografias")
async def api_guardar_escenografia(
    nombre: str = Form(...),
    descripcion: str = Form(...),
    clima: str = Form("despejado"),
    hora_dia: str = Form("dia"),
    material_suelo: str = Form("asfalto"),
    imagen: Optional[UploadFile] = File(None)
):
    imagen_path = None
    if imagen and imagen.filename:
        ext = Path(imagen.filename).suffix
        safe_name = "".join(c for c in nombre if c.isalnum() or c in ("-", "_")).rstrip()
        filename = f"{safe_name}{ext}"
        save_path = Path("static/escenografias") / filename
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(imagen.file, buffer)
        imagen_path = f"/static/escenografias/{filename}"
    else:
        # Si ya existe, mantener la ruta de la imagen existente
        existente = await memoria.obtener_escenografia(nombre)
        if existente:
            imagen_path = existente.get("imagen_path")
            
    await memoria.guardar_escenografia(nombre, descripcion, clima, hora_dia, material_suelo, imagen_path)
    return {"status": "success", "message": f"Escenografía '{nombre}' guardada correctamente"}

@app.delete("/api/escenografias/{nombre}")
async def api_eliminar_escenografia(nombre: str):
    existente = await memoria.obtener_escenografia(nombre)
    if existente and existente.get("imagen_path"):
        # No eliminar las imágenes por defecto sembradas
        if "static/escenografias" in existente.get("imagen_path") and not any(p in existente.get("imagen_path") for p in ["esquina.png", "tienda.png", "taller.png"]):
            img_path = Path(existente.get("imagen_path").lstrip("/"))
            if img_path.exists():
                try:
                    img_path.unlink()
                except:
                    pass
    await memoria.eliminar_escenografia(nombre)
    return {"status": "success", "message": f"Escenografía '{nombre}' eliminada correctamente"}

@app.get("/api/video/proyectos")
async def listar_videos(): 
    if not VIDEOS_DIR.exists(): return {"creaciones": [], "importados": [], "otros": []}
    
    creaciones = []
    importados = []
    otros = []
    proyectos_ids = set()
    
    # 1. Buscar creaciones con metadata JSON
    print(f"DEBUG: Buscando JSON en {VIDEOS_DIR}")
    for f in VIDEOS_DIR.glob("*.json"):
        print(f"DEBUG: Encontrado archivo JSON: {f.name}")
        try:
            with open(f, "r", encoding="utf-8") as file:
                data = json.load(file)
                if data.get("archivo_final"):
                    proyectos_ids.add(data.get("id"))
                    archivo_path = VIDEOS_DIR / data.get("archivo_final")
                    creaciones.append({
                        "id": data.get("id"),
                        "tema": data.get("tema", "Sin título"),
                        "estado": data.get("estado", "completado"),
                        "creado_en": data.get("creado_en", "Reciente"),
                        "tamano": data.get("tamano", "-"),
                        "duracion": data.get("duracion", 0),
                        "archivo": data.get("archivo_final"),
                        "existe": archivo_path.exists()
                    })
        except Exception as e:
            print(f"Error cargando metadata de {f.name}: {e}")
            
    # 2. Buscar archivos MP4 que NO tengan JSON asociado (Importados)
    for f in VIDEOS_DIR.glob("*.mp4"):
        video_id = f.stem
        if video_id not in proyectos_ids:
            try:
                stats = f.stat()
                importados.append({
                    "id": video_id,
                    "tema": f.name,
                    "estado": "importado",
                    "creado_en": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stats.st_mtime)),
                    "tamano": f"{stats.st_size / (1024*1024):.2f} MB",
                    "duracion": None,
                    "archivo": f.name,
                    "tipo": "mp4",
                    "es_importado": True
                })
            except Exception:
                pass
    
# 3. Buscar otros formatos de video en carpeta OTROS y VIDEOS
    formatos_otros = ['*.mov', '*.avi', '*.mkv', '*.webm', '*.flv', '*.wmv']
    for ext in formatos_otros:
        for f in list(VIDEOS_DIR.glob(ext)) + list(OTROS_DIR.glob(ext)):
            video_id = f.stem
            try:
                stats = f.stat()
                otros.append({
                    "id": video_id,
                    "tema": f.name,
                    "estado": "otro",
                    "creado_en": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stats.st_mtime)),
                    "tamano": f"{stats.st_size / (1024*1024):.2f} MB",
                    "duracion": None,
                    "archivo": f.name,
                    "tipo": f.suffix[1:].lower(),
                    "carpeta": "otros" if "otros" in str(f) else "videos"
                })
            except Exception:
                pass
    
    return {
        "creaciones": sorted(creaciones, key=lambda x: x['creado_en'], reverse=True),
        "importados": sorted(importados, key=lambda x: x['creado_en'], reverse=True),
        "otros": sorted(otros, key=lambda x: x['creado_en'], reverse=True)
    }

@app.post("/api/video/limpiar-cache")
async def limpiar_cache(): 
    try:
        count = 0
        for item in VIDEOS_DIR.iterdir():
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
                count += 1
        return {"status": "success", "message": f"Carpetas limpiadas: {count}"}
    except Exception as e: return {"status": "error", "message": str(e)}

# Cola Global para evitar colapsos por falta de memoria (Solo 1 render a la vez)
video_semaphore = asyncio.Semaphore(1)

async def _proceso_crear_video(proyecto_id: str, tema: str, prompt: str, voz: str, modo_video: str = "auto"):
    try:
        # Notificar que está en cola si hay alguien más renderizando
        if video_semaphore.locked():
            generador_video._actualizar_estado(proyecto_id, VideoEstado.EN_COLA)
            generador_video._actualizar_progreso(proyecto_id, 2)
            
        async with video_semaphore:
            # Una vez es su turno, comienza
            generador_video._actualizar_estado(proyecto_id, VideoEstado.ANALIZANDO)
            generador_video._actualizar_progreso(proyecto_id, 5)
            
            await generador_video.analizar_tema(tema, prompt, client, proyecto_id=proyecto_id)
            await generador_video.disenar_escenas(proyecto_id, client)
            
            # Guardar la voz elegida en el proyecto
            proyecto = generador_video.obtener_proyecto(proyecto_id)
            if hasattr(generador_video, '_cargar_proyecto'):
                proj_obj = generador_video._cargar_proyecto(proyecto_id)
                if proj_obj:
                    proj_obj.voz = voz
                    proj_obj.modo_video = modo_video or "auto"
                    generador_video._guardar_proyecto(proj_obj)
            
            # Aprobar todas por defecto para el flujo automatizado
            for escena in proyecto.get('escenas_disenadas', []):
                generador_video.aprobar_escena(proyecto_id, escena['numero'])
        
            await generador_video.producir_video(
                proyecto_id=proyecto_id, 
                groq_client=client, 
                generar_voz_func=None
            )
    except Exception as e:
        print(f"Error en video background: {e}")
        generador_video._actualizar_estado(proyecto_id, VideoEstado.ERROR, str(e))

# Funciones de background delegadas a Celery
# Se mantienen los wrappers si es necesario, pero los endpoints llamarán directamente a .delay()

# _proceso_ensamblar removido a favor de ensamblar_video_task.delay()

@app.post("/api/video/crear")
async def crear_video_endpoint(req: VideoRequest, background_tasks: BackgroundTasks):
    proyecto_id = f"proyecto_{int(time.time())}"
    generador_video.videos_dir.mkdir(exist_ok=True)
    tema_con_formato = f"{req.tema} ({req.formato})"
    
    # INICIALIZACIÓN INMEDIATA (Evita 404 en el primer polling)
    from .video import VideoProyecto, VideoEstado
    from datetime import datetime
    proyecto = VideoProyecto(
        id=proyecto_id,
        tema=tema_con_formato,
        prompt=req.prompt,
        prompt_original=req.prompt,
        estado=VideoEstado.ANALIZANDO,
        creado_en=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        modo_video=req.modo_video or "auto"
    )
    generador_video._guardar_proyecto(proyecto)
    
    background_tasks.add_task(_proceso_crear_video, proyecto_id, tema_con_formato, req.prompt + f" Estilo: {req.estilo}", req.voz, req.modo_video or "auto")
    return {"video_id": proyecto_id, "estado": "analizando"}
@app.post("/api/video/pre-produccion")
async def pre_produccion_endpoint(req: VideoRequest, background_tasks: BackgroundTasks):
    proyecto_id = f"proyecto_{int(time.time())}"
    generador_video.videos_dir.mkdir(exist_ok=True)
    tema_con_formato = f"{req.tema} ({req.formato})"
    
    payload = {
        "proyecto_id": proyecto_id,
        "tema": tema_con_formato,
        "prompt": req.prompt + f" Estilo: {req.estilo}",
        "voz": req.voz,
        "bgm_path": req.bgm_path,
        "modo_video": req.modo_video or "auto"
    }
    
    # Lanzar tarea en background (GRATIS)
    background_tasks.add_task(pre_producir_video_task, payload)
    
    return {"video_id": proyecto_id, "estado": "analizando"}

class ReescribirRequest(BaseModel):
    proyecto_id: str
    cambios: str = ""

@app.post("/api/video/reescribir")
async def reescribir_video_endpoint(req: ReescribirRequest, background_tasks: BackgroundTasks):
    """Crea una NUEVA versión del video aplicando los cambios que pide el usuario.
    Reutiliza tema, prompt original, voz, música y modo del proyecto de origen."""
    try:
        proyecto = generador_video.obtener_proyecto(req.proyecto_id)
        if not proyecto:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")
        if not (proyecto.get("prompt_original") or proyecto.get("prompt") or proyecto.get("tema")):
            raise HTTPException(status_code=400, detail="Este proyecto no tiene un prompt editable")

        prompt_base = proyecto.get("prompt_original") or proyecto.get("prompt") or ""
        prompt_base = str(prompt_base).replace(" Estilo: cinematic", "").strip()
        cambios = (req.cambios or "").strip()
        prompt_nuevo = prompt_base
        if cambios:
            prompt_nuevo = f"{prompt_base}\n\nCAMBIOS SOLICITADOS POR EL USUARIO: {cambios}"

        nuevo_id = f"proyecto_{int(time.time())}"
        payload = {
            "proyecto_id": nuevo_id,
            "tema": proyecto.get("tema", ""),
            "prompt": prompt_nuevo,
            "voz": proyecto.get("voz") or "es-CO-GonzaloNeural",
            "bgm_path": proyecto.get("bgm_path"),
            "modo_video": proyecto.get("modo_video") or "auto",
        }
        background_tasks.add_task(pre_producir_video_task, payload)
        return {"video_id": nuevo_id, "estado": "analizando", "reescrito_de": req.proyecto_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class RegenerarImagenRequest(BaseModel):
    proyecto_id: str
    escena_num: int
    prompt_visual: Optional[str] = None
    cantidad: Optional[int] = 1

@app.post("/api/video/regenerar-imagen")
async def regenerar_imagen_endpoint(req: RegenerarImagenRequest, background_tasks: BackgroundTasks):
    try:
        resultado = await regenerar_imagen_task(req.proyecto_id, req.escena_num, req.prompt_visual, req.cantidad)
        # Una vez regenerada, disparamos el re-ensamblado automático en background
        background_tasks.add_task(ensamblar_video_task, req.proyecto_id)
        return {"success": True, "result": resultado}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class SeleccionarImagenRequest(BaseModel):
    proyecto_id: str
    escena_num: int
    imagen_path: str

@app.post("/api/video/seleccionar-imagen")
async def seleccionar_imagen_endpoint(req: SeleccionarImagenRequest, background_tasks: BackgroundTasks):
    try:
        # Actualizar el proyecto con la ruta de la imagen seleccionada
        proj_obj = generador_video._cargar_proyecto(req.proyecto_id)
        if not proj_obj:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")
        
        # Mover la imagen seleccionada al path principal 'imagen.png' si es una alternativa
        dest_path = generador_video._get_proyecto_dir(req.proyecto_id) / f"escena_{req.escena_num}" / "imagen.png"
        if req.imagen_path != str(dest_path):
            import shutil
            shutil.copy2(req.imagen_path, dest_path)
        
        for e in proj_obj.escenas_disenadas:
            if e["numero"] == req.escena_num:
                e["imagen_path"] = str(dest_path)
                break
        
        generador_video._guardar_proyecto(proj_obj)
        
        # Disparar re-ensamblado automático
        background_tasks.add_task(ensamblar_video_task, req.proyecto_id)
        
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class AsignarReferenciasRequest(BaseModel):
    proyecto_id: str
    escena_num: int
    personaje_ref: Optional[str] = None
    escenografia_ref: Optional[str] = None

@app.post("/api/video/asignar-referencias")
async def api_asignar_referencias(req: AsignarReferenciasRequest):
    try:
        proj_obj = generador_video._cargar_proyecto(req.proyecto_id)
        if not proj_obj:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")
            
        for e in proj_obj.escenas_disenadas:
            if e["numero"] == req.escena_num:
                e["personaje_ref"] = req.personaje_ref
                e["escenografia_ref"] = req.escenografia_ref
                break
                
        generador_video._guardar_proyecto(proj_obj)
        return {"success": True, "message": "Referencias asignadas correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/video/subir-imagen-escena")
async def api_subir_imagen_escena(
    proyecto_id: str = Form(...),
    escena_num: int = Form(...),
    imagen: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    try:
        proj_obj = generador_video._cargar_proyecto(proyecto_id)
        if not proj_obj:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")
            
        dest_dir = generador_video._get_proyecto_dir(proyecto_id) / f"escena_{escena_num}"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / "imagen.png"
        
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(imagen.file, buffer)
            
        # Actualizar en el modelo del proyecto
        for e in proj_obj.escenas_disenadas:
            if e["numero"] == escena_num:
                e["imagen_path"] = str(dest_path)
                break
                
        generador_video._guardar_proyecto(proj_obj)
        
        # Disparar re-ensamblado automático en background para reflejar la imagen subida en el video final
        if background_tasks:
            background_tasks.add_task(ensamblar_video_task, proyecto_id)
            
        return {"success": True, "imagen_path": f"/video_files/{proyecto_id}/escena_{escena_num}/imagen.png"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/video/subir-musica")
async def api_subir_musica(archivo: UploadFile = File(...)):
    ext = Path(archivo.filename).suffix
    if ext.lower() not in (".mp3", ".wav", ".m4a", ".ogg"):
        raise HTTPException(status_code=400, detail="Formato de audio no soportado")
    
    save_dir = Path("static/bgm")
    save_dir.mkdir(parents=True, exist_ok=True)
    
    # Nombre de archivo único y seguro
    filename = f"musica_usuario_{int(time.time())}{ext}"
    save_path = save_dir / filename
    
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(archivo.file, buffer)
        
    return {"status": "success", "bgm_path": f"/static/bgm/{filename}", "nombre": archivo.filename}

@app.get("/api/video/celery-status/{task_id}")
async def celery_status(task_id: str):
    """Consulta el estado de una tarea de Celery genérica."""
    from celery.result import AsyncResult
    res = AsyncResult(task_id, app=celery)
    return {
        "task_id": task_id,
        "status": res.status,
        "result": res.result if res.ready() else None,
        "info": res.info if isinstance(res.info, dict) else {"msg": str(res.info)}
    }

class EnsamblarRequest(BaseModel):
    proyecto_id: str
    resolucion: Optional[str] = "1080"

@app.post("/api/video/ensamblar")
async def ensamblar_video_endpoint(req: EnsamblarRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(ensamblar_video_task, req.proyecto_id, req.resolucion)
    return {"success": True, "estado": "ensamblando"}

class ExportarPCRequest(BaseModel):
    proyecto_id: str
    resolucion: Optional[str] = "1080"

@app.post("/api/video/exportar-pc")
async def exportar_pc_endpoint(req: ExportarPCRequest):
    try:
        proyecto = generador_video.obtener_proyecto(req.proyecto_id)
        if not proyecto or not proyecto.get("archivo_final"):
            return {"status": "error", "message": "Video no encontrado o no finalizado."}
        
        archivo_origen = generador_video.videos_dir / proyecto["archivo_final"]
        if not archivo_origen.exists():
            return {"status": "error", "message": "El archivo físico no existe."}
            
        # Intentar detectar el escritorio del usuario en Windows
        try:
            escritorio = Path(os.path.join(os.environ['USERPROFILE'], 'Desktop'))
            if not escritorio.exists():
                escritorio = Path(os.path.expanduser("~/Desktop"))
        except:
            escritorio = Path(os.path.expanduser("~/Desktop"))
            
        archivo_destino = escritorio / proyecto["archivo_final"]
        
        import shutil
        shutil.copy2(archivo_origen, archivo_destino)
        
        # Opcional: Abrir la carpeta del escritorio
        if os.name == 'nt':
            os.startfile(escritorio)
            
        return {"status": "success", "ruta": str(archivo_destino)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- Fases del pipeline para el temporizador visual (estilo creadores de video) ---
ORDEN_FASES = ["leyendo", "analisis", "escenas", "imagenes", "voz", "subtitulos", "ensamblado", "listo"]


def _fase_actual_id(estado: str, pct: int, mensaje: str) -> str:
    estado = (estado or "").lower()
    m = (mensaje or "").lower()
    pct = pct or 0
    if estado == "completado":
        return "listo"
    if estado == "error":
        return "error"
    # El tramo final (92-100%) corresponde a subtítulos + ensamblado con FFmpeg,
    # aunque el estado interno siga siendo generando_voz / en_review.
    if pct >= 92:
        if any(k in m for k in ("subtitul", "whisper", "srt", "transcrib")):
            return "subtitulos"
        return "ensamblado"
    if estado == "en_cola":
        return "leyendo"
    if estado == "analizando":
        return "leyendo" if pct < 10 else "analisis"
    if estado == "disenando":
        return "escenas"
    if estado == "generando_imagenes":
        return "imagenes"
    if estado == "generando_voz":
        return "voz"
    if estado == "en_review":
        # Tras diseñar (60) o tras imágenes (80) el motor pasa por en_review
        return "escenas" if pct <= 70 else "imagenes"
    # Respaldo por porcentaje
    if pct < 10:
        return "leyendo"
    if pct < 30:
        return "analisis"
    if pct < 60:
        return "escenas"
    if pct < 85:
        return "imagenes"
    if pct < 92:
        return "voz"
    return "ensamblado"


def _detalle_fase(estado: str, pct: int, mensaje: str) -> str:
    """Extrae un sub-paso legible, p. ej. 'Imagen 3 de 5'."""
    import re
    m = (mensaje or "")
    # Patrón tipo "3 de 5" / "X de Y" presente en los mensajes del motor
    pat = re.search(r"(\d+)\s*de\s*(\d+)", m)
    if pat:
        a, b = pat.group(1), pat.group(2)
        bajo = m.lower()
        if "imagen" in bajo or "escena" in bajo:
            return f"{a} de {b}"
    return ""


def _calcular_fases_pipeline(estado: str, pct: int, mensaje: str) -> dict:
    actual = _fase_actual_id(estado, pct, mensaje)
    fases = []
    for f in ORDEN_FASES:
        if actual == "error":
            est = "pendiente"
        elif f == "listo":
            est = "hecha" if estado == "completado" else "pendiente"
        else:
            idx_act = ORDEN_FASES.index(actual) if actual in ORDEN_FASES else -1
            idx_f = ORDEN_FASES.index(f)
            if idx_act == -1:
                est = "pendiente"
            elif idx_f < idx_act:
                est = "hecha"
            elif idx_f == idx_act:
                est = "activa"
            else:
                est = "pendiente"
        fases.append({"id": f, "estado": est})
    return {"fase_actual": actual, "fases": fases}


@app.get("/api/video/progreso/{video_id}")
async def progreso_video(video_id: str):
    progreso = generador_video.obtener_progreso(video_id)
    proyecto = generador_video.obtener_proyecto(video_id)
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    estado = proyecto.get("estado", "desconocido")
    mensaje = proyecto.get("mensaje_estado", "Procesando...")
    fases_data = _calcular_fases_pipeline(estado, progreso, mensaje)
    return {
        "video_id": video_id,
        "progreso": progreso,
        "estado": estado,
        "mensaje_estado": mensaje,
        "error": proyecto.get("error"),
        "fase_actual": fases_data["fase_actual"],
        "fases": fases_data["fases"],
        "detalle_fase": _detalle_fase(estado, progreso, mensaje),
    }

@app.get("/api/video/estado/{video_id}")
async def estado_video(video_id: str):
    proyecto = generador_video.obtener_proyecto(video_id)
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return proyecto

@app.get("/api/video/descargar/{archivo}")
async def descargar_video(archivo: str):
    # Buscar en videos
    ruta = VIDEOS_DIR / archivo
    if ruta.exists():
        return FileResponse(str(ruta), media_type="video/mp4", filename=archivo)
    
    # Buscar en otros
    ruta_otros = OTROS_DIR / archivo
    if ruta_otros.exists():
        return FileResponse(str(ruta_otros), media_type="video/mp4", filename=archivo)
    
    raise HTTPException(status_code=404, detail="Archivo no encontrado")

@app.post("/api/otros/subir")
async def subir_otro_archivo(file):
    try:
        contenido = await file.read()
        nombre_archivo = file.filename or f"video_{int(time.time())}.mp4"
        
        # Determinar carpeta por extensión
        ext = Path(nombre_archivo).suffix.lower()
        if ext in ['.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv']:
            ruta = OTROS_DIR / nombre_archivo
        else:
            ruta = OTROS_DIR / nombre_archivo
        
        with open(ruta, "wb") as f:
            f.write(contenido)
        
        return {"status": "success", "archivo": nombre_archivo, "ruta": str(ruta)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.delete("/api/video/eliminar/{video_id}")
async def eliminar_video(video_id: str):
    exito = generador_video.eliminar_proyecto(video_id)
    if exito:
        return {"status": "success"}
    raise HTTPException(status_code=404, detail="Proyecto no encontrado o error al eliminar")

@app.post("/api/video/exportar-pc")
async def exportar_pc(req: ExportRequest):
    import tkinter as tk
    from tkinter import filedialog
    
    proyecto = generador_video.obtener_proyecto(req.proyecto_id)
    if not proyecto or not proyecto.get("archivo_final"):
        return {"status": "error", "message": "Video no encontrado"}
    
    video_orig = VIDEOS_DIR / proyecto["archivo_final"]
    if not video_orig.exists():
        return {"status": "error", "message": "Archivo de video no existe físicamente"}
    
    # 1. Abrir diálogo de guardado (esto bloquea, pero es lo que el usuario quiere)
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    
    # Sugerir nombre basado en tema
    sugerencia = (proyecto.get("tema", "video_hermatron")).replace(" ", "_")[:30] + f"_{req.resolucion}p.mp4"
    
    # Definir extensiones
    file_path = filedialog.asksaveasfilename(
        defaultextension=".mp4",
        initialfile=sugerencia,
        title="Escoge dónde guardar tu video profesional",
        filetypes=[("Video MP4", "*.mp4"), ("Todos los archivos", "*.*")]
    )
    root.destroy()
    
    if not file_path:
        return {"status": "error", "message": "Exportación cancelada por el usuario"}
    
    # 2. Procesar con FFmpeg para cambiar resolución si es necesario
    try:
        res_h = int(req.resolucion)
        # 1920 es especial porque el usuario puso 1920 (2K)
        if res_h == 1920:
             scale_filter = "scale=1920:1080" # Ya es 1080p usualmente, pero forzamos 1920 de ancho
        elif res_h == 2160:
             scale_filter = "scale=3840:2160" # 4K
        else:
             scale_filter = f"scale=-2:{res_h}" # Proporcional
             
        print(f"[EXPORT] Escalando a {scale_filter}...")
        
        # Comando FFmpeg
        comando = [
            "ffmpeg", "-y", "-i", str(video_orig),
            "-vf", scale_filter,
            "-c:v", "libx264", "-crf", "18", "-preset", "slow",
            "-c:a", "copy",
            file_path
        ]
        
        res = subprocess.run(comando, capture_output=True, text=True)
        if res.returncode == 0:
            return {"status": "success", "ruta": file_path}
        else:
            return {"status": "error", "message": f"FFmpeg error: {res.stderr}"}
            
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/video/probar-voz")
async def probar_voz(req: ProbarVozRequest):
    try:
        texto_prueba = "Hola, así sonará mi voz en tus videos profesionales."
        archivo_salida = await generador_voz.generar(texto=texto_prueba, voz_id=req.voz)
        if not archivo_salida:
            raise HTTPException(status_code=500, detail="No se pudo generar la prueba de voz")
        # El archivo devuelto es la ruta absoluta, necesitamos devolver el endpoint
        nombre_archivo = Path(archivo_salida).name
        return {"audio_url": f"/api/audio/{nombre_archivo}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/debug/latest-project")
async def debug_latest_project():
    try:
        import os
        import json
        from pathlib import Path
        videos_dir = generador_video.videos_dir
        json_files = list(videos_dir.glob("proyecto_*.json"))
        if not json_files:
            return {"error": "No projects found in videos_dir", "videos_dir": str(videos_dir)}
            
        latest_file = max(json_files, key=lambda p: p.stat().st_mtime)
        
        with open(latest_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        proyecto_id = data.get("id")
        project_dir = videos_dir / proyecto_id
        
        dir_structure = {}
        if project_dir.exists():
            for p in project_dir.rglob("*"):
                rel = p.relative_to(project_dir)
                dir_structure[str(rel)] = {
                    "is_file": p.is_file(),
                    "size": p.stat().st_size if p.is_file() else 0
                }
        else:
            dir_structure = "Directory does not exist"
            
        return {
            "latest_project_file": latest_file.name,
            "project_data": {
                "id": data.get("id"),
                "tema": data.get("tema"),
                "estado": data.get("estado"),
                "progreso": data.get("progreso"),
                "error": data.get("error"),
                "escenas_disenadas": [
                    {
                        "numero": e.get("numero"),
                        "imagen_path": e.get("imagen_path"),
                        "lipsync_path": e.get("lipsync_path")
                    } for e in data.get("escenas_disenadas", [])
                ]
            },
            "dir_structure": dir_structure,
            "videos_dir_exists": videos_dir.exists(),
            "videos_dir_contents": [p.name for p in videos_dir.iterdir() if p.name.startswith("proyecto_")]
        }
    except Exception as e:
        return {"error": str(e)}

# ==========================================
# v6.2: BASE DE CONOCIMIENTO (API)
# ==========================================

@app.get("/api/conocimiento")
async def api_obtener_conocimiento(categoria: Optional[str] = None, limit: int = 50):
    """Lista las entradas de la base de conocimiento de HERMATRON."""
    conocimiento = await memoria.obtener_conocimientos(categoria=categoria, limit=limit)
    return {"conocimiento": conocimiento, "total": await memoria.contar_conocimientos()}


@app.post("/api/conocimiento")
async def api_guardar_conocimiento(
    titulo: str = Form(...),
    contenido: str = Form(...),
    categoria: str = Form("general"),
    fuente: str = Form(""),
):
    """Guarda o actualiza una entrada de conocimiento."""
    await memoria.guardar_conocimiento(titulo, contenido, categoria, fuente)
    return {"status": "success", "mensaje": f"Conocimiento '{titulo}' guardado."}


@app.delete("/api/conocimiento/{titulo}")
async def api_eliminar_conocimiento(titulo: str):
    """Elimina una entrada de conocimiento por título."""
    await memoria.eliminar_conocimiento(titulo)
    return {"status": "success"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=DEBUG)