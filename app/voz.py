"""
Módulo de Voz - HERMATRON v3.2 (MEJORADO)
Prioridad: edge-tts (Gonzalo Colombia - Masculino natural) -> ElevenLabs -> pyttsx3
Gratis, ilimitado, sin consumo de créditos
Sistema de caché para evitar regenerar audios idénticos
"""
import asyncio
import time
import os
import hashlib
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# --- EL PUENTE DIRECTO AL .ENV (Para que no falle ElevenLabs) ---
BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

AUDIO_DIR = BASE_DIR / "audio"
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")

# Voz principal por defecto (desde .env), fallback: Jorge (gratis)
VOZ_DEFECTO = os.getenv("TTS_VOICE", "es-MX-JorgeNeural")
ELEVENLABS_VOICE_ADAM = "pNInz6obpgDQGcFmaJgB"
ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1/text-to-speech"

# Voces masculinas recomendadas (expandidas para mejor variedad)
VOCES_MASCULINAS = {
    "gonzalo": "es-CO-GonzaloNeural",    # Colombia ⭐ RECOMENDADA (natural, profesional)
    "jorge": "es-MX-JorgeNeural",        # México (cálido, amigable)
    "alonso": "es-US-AlonsoNeural",      # US Español (neutro, claro)
    "alvaro": "es-ES-AlvaroNeural",      # España (profesional, profundo)
    "tomas": "es-AR-TomasNeural",        # Argentina (distintivo, energético)
    "carlos": "es-ES-CarlosNeural",      # España alternativo
    "diego": "es-MX-DiegoNeural",        # México alternativo
}

# Voces femeninas disponibles
VOCES_FEMENINAS = {
    "lucia": "es-ES-LuciaNeural",        # España (clara, profesional)
    "conchita": "es-ES-ConchitaNeural",  # España (cálida, amable)
    "lupe": "es-MX-LupeNeural",          # México (natural, joven)
    "raquel": "es-ES-RaquelNeural",      # España (dulce, agradable)
}

def limpiar_texto_para_tts(texto: str) -> str:
    """Limpia el texto para TTS"""
    import re
    texto = re.sub(r'\*\*(.+?)\*\*', r'\1', texto)
    texto = re.sub(r'\*(.+?)\*', r'\1', texto)
    texto = texto.replace('*', '')
    texto = re.sub(r'_{2,}(.+?)_{2,}', r'\1', texto)
    texto = texto.replace('_', '')
    texto = re.sub(r'#{1,6}\s+', '', texto)
    texto = re.sub(r'`{1,3}[^`]*`{1,3}', 'código', texto)
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto

class GeneradorVoz:
    """Generador de voz: edge-tts (Gonzalo gratis) -> ElevenLabs -> pyttsx3"""

    def __init__(self, output_dir: Path = AUDIO_DIR, voz: str = VOZ_DEFECTO):
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
        self.voz = voz
        self.cache_dir = self.output_dir / ".cache_voz"
        self.cache_dir.mkdir(exist_ok=True)

    def _obtener_hash_audio(self, texto: str, voz: str, calidad: str) -> str:
        """Genera hash único para cada combinación texto-voz-calidad"""
        clave = f"{texto}:{voz}:{calidad}"
        return hashlib.md5(clave.encode()).hexdigest()
    
    def _buscar_en_cache(self, hash_audio: str) -> Optional[Path]:
        """Busca si el audio ya existe en caché"""
        archivo_cache = self.cache_dir / f"{hash_audio}.mp3"
        if archivo_cache.exists() and archivo_cache.stat().st_size > 0:
            print(f"[CACHÉ] ✅ Audio encontrado en caché: {hash_audio[:8]}...")
            return archivo_cache
        return None
    
    def _guardar_en_cache(self, hash_audio: str, ruta_origen: Path) -> Path:
        """Guarda el audio en caché"""
        archivo_cache = self.cache_dir / f"{hash_audio}.mp3"
        if ruta_origen.exists():
            import shutil
            shutil.copy2(ruta_origen, archivo_cache)
            print(f"[CACHÉ] 💾 Audio guardado en caché")
        return archivo_cache

    async def generar(self, texto: str, nombre_archivo: Optional[str] = None, 
                      lang: Optional[str] = None, calidad: str = "edge-tts", voz_id: str = None) -> str:
        """
        Generar audio con mejor calidad disponible
        """
        import time

        try:
            texto_limpio = limpiar_texto_para_tts(texto)
            
            # --- CONEXIÓN CON EL MENÚ DE LA WEB ---
            voz_actual = voz_id if voz_id else self.voz

            # Forzar fallback local desde la UI
            if voz_actual in ["local", "pyttsx3", "sabina"]:
                calidad = "local"

            # ElevenLabs (compat: "Adam" o ID directo)
            eleven_voice_id: Optional[str] = None
            if voz_actual == "Adam":
                calidad = "elevenlabs"
                eleven_voice_id = ELEVENLABS_VOICE_ADAM
            elif isinstance(voz_actual, str) and len(voz_actual) >= 15 and " " not in voz_actual:
                # Si enviamos el voice_id directo desde el select
                calidad = "elevenlabs"
                eleven_voice_id = voz_actual

            # Edge-TTS (IDs completos)
            if voz_actual in ["es-ES-AlvaroNeural", "es-CO-GonzaloNeural", "es-MX-JorgeNeural", "es-US-AlonsoNeural", "es-AR-TomasNeural"]:
                calidad = "edge-tts"
                self.voz = voz_actual
            
            # --- VERIFICAR CACHÉ ANTES DE GENERAR ---
            hash_audio = self._obtener_hash_audio(texto_limpio, str(voz_actual), calidad)
            audio_en_cache = self._buscar_en_cache(hash_audio)
            if audio_en_cache:
                return str(audio_en_cache)
            
            print(f"[TTS] Generando (calidad: {calidad}, voz: {self.voz}): '{texto_limpio[:50]}...'")

            if not nombre_archivo:
                timestamp = int(time.time())
                nombre_archivo = f"respuesta_{timestamp}.mp3"

            ruta_completa = self.output_dir / nombre_archivo

            if calidad == "elevenlabs" and ELEVENLABS_API_KEY:
                # ElevenLabs Adam (premium, usa créditos)
                try:
                    exito = await self._generar_elevenlabs(texto_limpio, ruta_completa, voice_id=eleven_voice_id or ELEVENLABS_VOICE_ADAM)
                    if exito:
                        self._guardar_en_cache(hash_audio, ruta_completa)
                        print(f"[TTS] ✅ ElevenLabs: {ruta_completa}")
                        return str(ruta_completa)
                except Exception as e:
                    print(f"[TTS] ElevenLabs falló: {e}")
            
            # edge-tts Gonzalo (GRATIS, ilimitado, calidad casi humana)
            if calidad in ["edge-tts", "elevenlabs"]:  # Fallback de elevenlabs
                try:
                    # Parámetros suaves para sonar menos “robótico”
                    exito = await self._generar_edge_tts(texto_limpio, ruta_completa, velocidad=0.95, tono=0)
                    if exito:
                        self._guardar_en_cache(hash_audio, ruta_completa)
                        print(f"[TTS] ✅ edge-tts ({self.voz}): {ruta_completa}")
                        return str(ruta_completa)
                except Exception as e:
                    print(f"[TTS] edge-tts falló: {e}")
            
            # Fallback local (siempre funciona, pero robotizado)
            print(f"[TTS] Usando fallback local (pyttsx3)")
            # Importante: no "envenenar" la caché de edge-tts con audio local.
            # Si caemos a local, usamos una clave de caché distinta.
            hash_audio_local = self._obtener_hash_audio(texto_limpio, str(voz_actual), "local")
            audio_local_en_cache = self._buscar_en_cache(hash_audio_local)
            if audio_local_en_cache:
                return str(audio_local_en_cache)

            exito = await self._generar_local(texto_limpio, ruta_completa, voz_seleccionada=voz_actual)
            if exito:
                self._guardar_en_cache(hash_audio_local, ruta_completa)
                print(f"[TTS] ✅ Local: {ruta_completa}")
                return str(ruta_completa)
            
            raise Exception("No se pudo generar audio con ningún método")

        except Exception as e:
            print(f"[TTS] Error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def _generar_edge_tts(self, texto: str, ruta: Path, velocidad: float = 1.0, tono: int = 0) -> bool:
        """Generar audio con edge-tts (Microsoft - GRATIS, calidad casi humana)
        
        Args:
            texto: Texto a convertir en voz
            ruta: Ruta de salida del archivo MP3
            velocidad: Velocidad de reproducción (0.5 a 2.0, default 1.0)
            tono: Tono de voz (-50 a 50, default 0)
        """
        try:
            import edge_tts
            
            # Construir parámetros SSML para mejor control
            communicate = edge_tts.Communicate(
                texto, 
                self.voz,
                rate=f"{int((velocidad - 1) * 100):+d}%",  # Conversión a porcentaje
                pitch=f"{int(tono):+d}Hz"
            )
            await communicate.save(str(ruta))
            
            return ruta.exists() and ruta.stat().st_size > 0
        except Exception as e:
            print(f"[edge-tts] Error: {e}")
            return False

    async def _generar_elevenlabs(self, texto: str, ruta: Path, voice_id: str) -> bool:
        """Generar audio con ElevenLabs (voice_id)"""
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
                    "stability": 0.5,
                    "similarity_boost": 0.8,
                    "style": 0.1,
                    "use_speaker_boost": True
                }
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{ELEVENLABS_API_URL}/{voice_id}",
                    json=payload,
                    headers=headers
                )
                
                if response.status_code == 200:
                    with open(ruta, "wb") as f:
                        f.write(response.content)
                    return ruta.exists() and ruta.stat().st_size > 0
                else:
                    print(f"[ElevenLabs] Error {response.status_code}: {response.text[:200]}")
                    return False
        except Exception as e:
            print(f"[ElevenLabs] Excepción: {e}")
            return False

    def _obtener_voces_locales(self) -> list[dict]:
        """
        Devuelve voces locales (SAPI5/Windows) visibles por pyttsx3.
        """
        try:
            import pyttsx3
            engine = pyttsx3.init()
            voces = engine.getProperty("voices") or []
            out: list[dict] = []
            for v in voces:
                # v.id suele ser tipo token SAPI; v.name es el nombre amigable
                nombre = getattr(v, "name", "") or ""
                vid = getattr(v, "id", "") or ""
                if not vid and not nombre:
                    continue
                out.append(
                    {
                        "id": f"sapi::{vid}" if vid else f"sapi-name::{nombre}",
                        "nombre": f"🖥️ {nombre or vid}",
                        "tipo": "local",
                        "engine": "pyttsx3",
                    }
                )
            try:
                engine.stop()
            except Exception:
                pass
            del engine
            return out
        except Exception:
            return []

    def _elegir_voz_local_por_defecto(self, voces) -> Optional[str]:
        """
        Elige una voz local evitando "Sabina" cuando sea posible.
        Retorna voice.id o None.
        """
        def _norm(s: str) -> str:
            return (s or "").strip().lower()

        # 1) Preferir voces en español que NO sean Sabina
        candidatos_es_no_sabina = []
        for v in voces:
            name = _norm(getattr(v, "name", ""))
            vid = _norm(getattr(v, "id", ""))
            if "es" in name or "spanish" in name or "es-" in name or "es_" in name or "es-" in vid or "es_" in vid:
                if "sabina" not in name and "sabina" not in vid:
                    candidatos_es_no_sabina.append(v)
        if candidatos_es_no_sabina:
            return getattr(candidatos_es_no_sabina[0], "id", None)

        # 2) Si solo hay Sabina en español, usarla
        for v in voces:
            name = _norm(getattr(v, "name", ""))
            vid = _norm(getattr(v, "id", ""))
            if "sabina" in name or "sabina" in vid:
                return getattr(v, "id", None)

        # 3) Fallback: primera voz disponible
        if voces:
            return getattr(voces[0], "id", None)
        return None

    async def _generar_local(self, texto: str, ruta: Path, voz_seleccionada: Optional[str] = None) -> bool:
        """Fallback con pyttsx3 - Voz local (Windows) seleccionable desde UI"""
        try:
            import pyttsx3
            engine = pyttsx3.init()
            
            voces = []
            try:
                voces = engine.getProperty("voices") or []
            except Exception:
                voces = []

            # Si llega un id "sapi::...", lo usamos tal cual
            voz_id_directa: Optional[str] = None
            if isinstance(voz_seleccionada, str) and voz_seleccionada:
                if voz_seleccionada.startswith("sapi::"):
                    voz_id_directa = voz_seleccionada[len("sapi::") :]
                elif voz_seleccionada.startswith("sapi-name::"):
                    # buscar por nombre
                    target_name = voz_seleccionada[len("sapi-name::") :].strip().lower()
                    for v in voces:
                        if (getattr(v, "name", "") or "").strip().lower() == target_name:
                            voz_id_directa = getattr(v, "id", None)
                            break

            if voz_id_directa:
                engine.setProperty("voice", voz_id_directa)
            else:
                # Si no se seleccionó una específica, elegir por defecto evitando Sabina si hay otra
                voz_default = self._elegir_voz_local_por_defecto(voces)
                if voz_default:
                    engine.setProperty("voice", voz_default)
            
            # Configuración optimizada para mejor claridad y naturalidad
            engine.setProperty('rate', 160)      # Velocidad más natural
            engine.setProperty('volume', 0.98)   # Volumen máximo pero sin saturación
            engine.setProperty('pitch', 1.0)     # Tono neutral
            
            engine.save_to_file(texto, str(ruta))
            engine.runAndWait()
            del engine
            return ruta.exists() and ruta.stat().st_size > 0
        except Exception as e:
            print(f"[pyttsx3] Error: {e}")
            return False

    def obtener_voces_disponibles(self) -> list:
        """Lista de voces adaptada para el menú de la web"""
        voces_masculinas = [
            {"id": "es-CO-GonzaloNeural", "nombre": "🎙️ Gonzalo (Colombia) ⭐ RECOMENDADA", "tipo": "masculina"},
            {"id": "es-ES-AlvaroNeural", "nombre": "🎙️ Álvaro (España) - Profesional", "tipo": "masculina"},
            {"id": "es-MX-JorgeNeural", "nombre": "🎙️ Jorge (México) - Cálido", "tipo": "masculina"},
            {"id": "es-US-AlonsoNeural", "nombre": "🎙️ Alonso (USA) - Neutral", "tipo": "masculina"},
            {"id": "es-AR-TomasNeural", "nombre": "🎙️ Tomás (Argentina) - Energético", "tipo": "masculina"},
        ]
        voces_femeninas = [
            {"id": "es-ES-LuciaNeural", "nombre": "👩 Lucía (España) - Clara", "tipo": "femenina"},
            {"id": "es-ES-ConchitaNeural", "nombre": "👩 Conchita (España) - Cálida", "tipo": "femenina"},
        ]
        voces_premium = [
            {"id": "Adam", "nombre": "💎 Adam (ElevenLabs) - PREMIUM", "tipo": "premium"},
        ]
        voces_locales = self._obtener_voces_locales()
        return voces_masculinas + voces_femeninas + voces_premium + voces_locales

# Instancia global
generador_voz = GeneradorVoz()