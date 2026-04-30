"""
Módulo de Voz - ElevenLabs para HERMATRON
Voces naturales (si la API key tiene permisos)
Fallback a pyttsx3 local (siempre disponible)
"""
import asyncio
import time
from pathlib import Path
from typing import Optional

from app.config import ELEVENLABS_API_KEY, AUDIO_DIR

# Voces de ElevenLabs en español
VOCES_ELEVENLABS = [
    {
        "id": "pNInz6obpgDQGcFmaJgB",
        "nombre": "Adam",
        "region": "Español Neutro",
        "tipo": "Masculina",
        "flag": "🎙️",
        "descripcion": "Voz profunda y profesional"
    },
    {
        "id": "EXAVITQu4vr4xnSDxMaL",
        "nombre": "Sarah",
        "region": "Español Neutro",
        "tipo": "Femenina",
        "flag": "🎙️",
        "descripcion": "Voz cálida y natural"
    },
]

ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1/text-to-speech"


async def generar_voz_elevenlabs(
    texto: str,
    voz_id: str = "pNInz6obpgDQGcFmaJgB",
    nombre_archivo: Optional[str] = None,
    output_dir: Path = AUDIO_DIR
) -> str:
    """
    Generar audio con ElevenLabs. Si falla, usa pyttsx3 local.
    """
    output_dir.mkdir(exist_ok=True)

    if not nombre_archivo:
        nombre_archivo = f"elevenlabs_{voz_id}_{int(time.time())}.mp3"

    ruta_salida = output_dir / nombre_archivo

    # Intentar ElevenLabs
    if ELEVENLABS_API_KEY:
        try:
            import httpx
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": ELEVENLABS_API_KEY
            }
            payload = {
                "text": texto,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.75,  # Mayor estabilidad = más consistencia
                    "similarity_boost": 0.85,  # Mayor similitud = más natural
                    "style": 0.2,  # Toque de expresión
                    "use_speaker_boost": True
                }
            }
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{ELEVENLABS_API_URL}/{voz_id}",
                    json=payload,
                    headers=headers
                )
                if response.status_code == 200:
                    with open(ruta_salida, "wb") as f:
                        f.write(response.content)
                    print(f"[ElevenLabs] ✅ Audio generado: {ruta_salida}")
                    return str(ruta_salida)
                else:
                    print(f"[ElevenLabs] Error {response.status_code}, usando fallback local")
        except Exception as e:
            print(f"[ElevenLabs] Error: {e}, usando fallback local")

    # Fallback a pyttsx3 local (siempre funciona)
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty('voice', 'HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Speech\\Voices\\Tokens\\TTS_MS_ES-MX_SABINA_11.0')
        engine.setProperty('rate', 175)
        engine.setProperty('volume', 0.95)
        engine.save_to_file(texto, str(ruta_salida))
        engine.runAndWait()
        del engine

        if ruta_salida.exists() and ruta_salida.stat().st_size > 0:
            print(f"[pyttsx3] ✅ Audio local generado: {ruta_salida}")
            return str(ruta_salida)
        else:
            raise Exception("Archivo vacío")
    except Exception as e:
        raise Exception(f"No se pudo generar audio: {e}")


async def probar_voz_elevenlabs(voz_id: str) -> str:
    """Generar muestra de audio de una voz para preview"""
    texto_preview = "¡Hola! Soy la voz seleccionada para tu video. Si te gusta mi sonido, elígeme para tu proyecto."
    nombre = f"preview_{voz_id}_{int(time.time())}.mp3"
    return await generar_voz_elevenlabs(texto_preview, voz_id, nombre)


def obtener_voces_elevenlabs() -> list:
    """Obtener lista de voces disponibles"""
    return VOCES_ELEVENLABS
