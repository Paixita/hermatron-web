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
from app.config import ALLOW_SYSTEM_COMMANDS
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

from fastapi import FastAPI, Request, HTTPException, Form
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
from .memoria import memoria
from .voz import generador_voz
from .busqueda import buscador 
from .video import generador_video, VideoEstado
from .modos import listar_modos

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
from app.config import ALLOW_SYSTEM_COMMANDS
def _extraer_tool_calls_de_texto(texto: str) -> list:
    """Extrae múltiples objetos JSON concatenados de un texto (ej: {...}{...})"""
    objs = []
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
SYSTEM_PROMPT = """Eres HERMATRON, un agente creativo profesional. 
ATENCIÓN: TIENES ACCESO TOTAL AL ORDENADOR DEL USUARIO mediante tus herramientas. Tu cuerpo de Python se ejecuta localmente.
REGLAS ESTRICTAS:
1. Si el usuario te pide abrir un programa (como el Bloc de Notas), usar Windows o mover carpetas, DEBES usar OBLIGATORIAMENTE la herramienta 'ejecutar_comando_pc'. NUNCA digas que no puedes acceder al PC. ¡SÍ PUEDES!
2. Si te preguntan datos exactos o noticias, usa tus herramientas de buscar en internet.
3. Responde como un colega experto ("mi pana"), no como un robot aburrido."""

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
if GROQ_API_KEY:
    try:
        client = Groq(api_key=GROQ_API_KEY)
        print("✅ Cliente Groq inicializado correctamente.")
    except Exception as e:
        print(f"❌ Error inicializando cliente Groq: {e}")
else:
    print("⚠️ GROQ_API_KEY no detectada. El sistema funcionará en modo limitado.")

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
# ENDPOINTS PRINCIPALES
# ==========================================

@app.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="landing.html",
        context={"request": request, "title": "HERMATRON - Inteligencia Artificial Multimodal"},
    )

@app.get("/chat", response_class=HTMLResponse)
async def chat_app(request: Request):
    try:
        static_version = int((BASE_DIR / "static" / "app.js").stat().st_mtime)
    except Exception:
        static_version = int(time.time())
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request, "title": "HERMATRON - Chat Multiusos", "static_version": static_version},
    )

@app.get("/videos", response_class=HTMLResponse)
async def video_studio(request: Request):
    return templates.TemplateResponse(request=request, name="video-studio.html", context={"request": request, "title": "HERMATRON - Estudio de Video"})

@app.post("/api/chat", response_model=ChatResponse)
async def chat(chat_request: ChatRequest):
    if not client: raise HTTPException(status_code=500, detail="API key no configurada")
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
        
        chat_completion = client.chat.completions.create(
            messages=mensajes_groq, model=GROQ_MODEL, temperature=0.2, max_tokens=2048,
            tools=herramientas_groq, tool_choice="auto"
        )
        
        mensaje_respuesta = chat_completion.choices[0].message
        
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
                
                resultado_datos = ""
                if nombre_funcion == "buscar_en_internet":
                    res = buscador.buscar(argumentos.get("query", ""))
                    resultado_datos = json.dumps(res)
                elif nombre_funcion == "obtener_suscriptores_youtube":
                    res = buscador.obtener_suscriptores_youtube(argumentos.get("canal", ""))
                    resultado_datos = json.dumps(res)
                elif nombre_funcion == "descargar_pagina_web":
                    res = buscador.descargar_contenido(argumentos.get("url", ""))
                    resultado_datos = json.dumps(res)
                elif nombre_funcion == "ejecutar_codigo_python":
                    codigo = argumentos.get("codigo", "")
                    print(f"🐍 [PYTHON] Ejecutando código de {len(codigo)} bytes")
                    resultado_datos = json.dumps(_ejecutar_codigo_python(codigo))
                elif nombre_funcion == "ejecutar_comando_pc":
                    comando = argumentos.get("comando", "")
                    print(f"💻 [PC] Ejecutando: {comando}")
                    resultado_datos = json.dumps(_ejecutar_comando_windows_no_bloqueante(comando))
                
                mensajes_groq.append({"role": "tool", "tool_call_id": tool_call.id, "name": nombre_funcion, "content": resultado_datos})
            
            chat_completion_final = client.chat.completions.create(messages=mensajes_groq, model=GROQ_MODEL, temperature=0.7, max_tokens=2048)
            respuesta = chat_completion_final.choices[0].message.content
        else:
            # Fallback: a veces el modelo devuelve un "tool call" en texto.
            # Si detectamos JSON tipo {"type":"function","name":"...","parameters":{...}},
            # lo ejecutamos manualmente y luego pedimos la respuesta final.
            contenido = mensaje_respuesta.content or ""
            respuesta = contenido
            try:
                start = contenido.find("{")
                end = contenido.rfind("}")
                if start != -1 and end != -1:
                    blob = contenido[start:end+1].replace('\\"', '"')
                    tool_obj = json.loads(blob)
                    nombre = tool_obj.get("name")
                    params = tool_obj.get("parameters") or {}
                    if nombre in ["buscar_en_internet", "descargar_pagina_web", "ejecutar_comando_pc", "obtener_suscriptores_youtube", "ejecutar_codigo_python"]:
                        print(f"🧰 [TOOL-FALLBACK] Ejecutando {nombre} desde texto")
                        if nombre == "buscar_en_internet":
                            tool_res = buscador.buscar(params.get("query", ""))
                        elif nombre == "descargar_pagina_web":
                            tool_res = buscador.descargar_contenido(params.get("url", ""))
                        elif nombre == "obtener_suscriptores_youtube":
                            tool_res = buscador.obtener_suscriptores_youtube(params.get("canal", ""))
                        elif nombre == "ejecutar_codigo_python":
                            tool_res = _ejecutar_codigo_python(params.get("codigo", ""))
                        else:
                            comando = params.get("comando", "")
                            tool_res = _ejecutar_comando_windows_no_bloqueante(comando)

                        mensajes_groq.append({"role": "assistant", "content": contenido})
                        mensajes_groq.append({"role": "user", "content": f"[SISTEMA] El resultado de la herramienta '{nombre}' fue:\n{json.dumps(tool_res)}\n\nUsa esta información para responder a mi pregunta anterior de forma natural."})
                        chat_completion_final = client.chat.completions.create(
                            messages=mensajes_groq, model=GROQ_MODEL, temperature=0.7, max_tokens=2048
                        )
                        respuesta = chat_completion_final.choices[0].message.content
            except Exception as e:
                print(f"❌ [TOOL-FALLBACK ERROR] {e}")

        await memoria.agregar_mensaje("assistant", respuesta, conversacion_id=chat_request.conversacion_id)

        audio_id, audio_gen = None, False
        if chat_request.generar_audio:
            try:
                timestamp = int(time.time())
                nombre_archivo = f"respuesta_{timestamp}.mp3"
                await generador_voz.generar(
                    respuesta,
                    nombre_archivo,
                    calidad=chat_request.calidad_audio or "edge-tts",
                    voz_id=chat_request.voz_id,
                )
                audio_gen, audio_id = True, nombre_archivo
            except Exception as e: print(f"❌ [AUDIO ERROR]: {e}")

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
            if "does not support image" in error_msg or "not support vision" in error_msg:
                respuesta = """El modelo de visión actual no está disponible en tu cuenta de Groq.

Para usar análisis de imágenes, necesitas:
1. Verificar que tu cuenta de Groq tenga acceso al modelo **Llama 4 Scout**
2. Ir a https://console.groq.com/settings/permissions
3. Habilitar el modelo de visión

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
        await memoria.agregar_mensaje("assistant", respuesta, modo, conversacion_id=conversacion_id)

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
    return {
        "status": "healthy", 
        "groq_configured": bool(GROQ_API_KEY), 
        "model": GROQ_MODEL,
        "vision_model": GROQ_MODEL_VISION
    }

@app.get("/api/modos")
async def obtener_modos():
    """Lista de modos disponibles"""
    return {"modos": listar_modos()}

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

async def _proceso_crear_video(proyecto_id: str, tema: str, prompt: str, voz: str):
    try:
        await generador_video.analizar_tema(tema, prompt, client, proyecto_id=proyecto_id)
        await generador_video.disenar_escenas(proyecto_id, client)
        
        # Guardar la voz elegida en el proyecto
        proyecto = generador_video.obtener_proyecto(proyecto_id)
        if hasattr(generador_video, '_cargar_proyecto'):
            proj_obj = generador_video._cargar_proyecto(proyecto_id)
            if proj_obj:
                proj_obj.voz = voz
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

@app.post("/api/video/crear")
async def crear_video_endpoint(req: VideoRequest, background_tasks: BackgroundTasks):
    proyecto_id = f"proyecto_{int(time.time())}"
    # Crear proyecto base
    generador_video.videos_dir.mkdir(exist_ok=True)
    # Pasar a background
    background_tasks.add_task(_proceso_crear_video, proyecto_id, req.tema, req.prompt + f" Estilo: {req.estilo}", req.voz)
    # Retornar inmediatamente
    return {"video_id": proyecto_id, "estado": "analizando"}

@app.get("/api/video/progreso/{video_id}")
async def progreso_video(video_id: str):
    progreso = generador_video.obtener_progreso(video_id)
    proyecto = generador_video.obtener_proyecto(video_id)
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return {
        "video_id": video_id, 
        "progreso": progreso, 
        "estado": proyecto.get("estado", "desconocido"),
        "error": proyecto.get("error")
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=DEBUG)