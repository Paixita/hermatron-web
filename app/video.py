"""
Módulo de Video - Generador de Videos para HERMATRON v4.0
Pipeline "Director de Cine": Analizar → Diseñar → Review → Producir
"""
import asyncio
import textwrap
import os
import json
import time
import uuid
import subprocess
import re
from pathlib import Path
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, asdict, field
from enum import Enum

from google.cloud import translate_v2 as translate
from utils.ffmpeg_helper import crear_clip_imagen, concatenar_segmentos
from app.config import (
    BASE_DIR, PEXELS_API_KEY, ELEVENLABS_API_KEY, UNSPLASH_ACCESS_KEY,
    TRANSLATION_CACHE_TTL, MAX_IN_MEMORY_DURATION, IMAGE_RESOLUTIONS,
    TRANSLATION_CACHE_PATH, GROQ_MODEL
)


# --- DIRECTORIO DE VIDEOS ---
VIDEOS_DIR = BASE_DIR / "videos"
VIDEOS_DIR.mkdir(exist_ok=True)

THUMBNAILS_DIR = VIDEOS_DIR / "thumbnails"
THUMBNAILS_DIR.mkdir(exist_ok=True)

# --- ESTADO DE VIDEO ---
class VideoEstado(str, Enum):
    EN_COLA = "en_cola"
    ANALIZANDO = "analizando"
    DISENANDO = "disenando"
    EN_REVIEW = "en_review"
    APROBADO = "aprobado"
    GENERANDO_IMAGENES = "generando_imagenes"
    GENERANDO_VEZ = "generando_voz"
    ENSAMBLANDO = "ensamblando"
    COMPLETADO = "completado"
    NEEDS_RENDER = "needs_render"
    ERROR = "error"
    ELIMINADO = "eliminado"


@dataclass
class EscenaDisenada:
    """Escena diseñada por el Director (antes de generar)"""
    numero: int
    titulo: str
    texto_narracion: str
    descripcion_visual: str
    angulo_camara: str = ""
    iluminacion: str = ""
    paleta_colores: str = ""
    movimiento: str = ""
    emocion: str = ""
    query_pexels: str = ""
    aprobada: bool = False
    imagen_path: Optional[str] = None


@dataclass
class AnalisisTematico:
    """Análisis del tema que hace la IA como Director"""
    tema: str
    tono_general: str = ""
    estilo_visual: str = ""
    atmosfera: str = ""
    publico_objetivo: str = ""
    duracion_estimada: str = ""
    referencia_cinematografica: str = ""


@dataclass
class VideoProyecto:
    """Proyecto completo de video con fases"""
    id: str
    tema: str
    prompt: str
    estado: str
    creado_en: str
    prompt_original: Optional[str] = None
    analisis: Optional[dict] = None
    escenas_disenadas: list = field(default_factory=list)
    guion_completo: Optional[str] = None
    audio_path: Optional[str] = None
    archivo_final: Optional[str] = None
    thumbnail: Optional[str] = None
    duracion: Optional[float] = None
    tamano: Optional[str] = None
    error: Optional[str] = None
    narracion: bool = True
    voz: str = "es-MX-JorgeNeural"
    progreso: int = 0


class GeneradorVideo:
    """
    Generador de videos con pipeline "Director de Cine"

    Fases:
    1. 📖 LEER PROMPT
    2. 🧠 ANALIZAR TEMA → Tono, estilo, atmósfera
    3. 🎬 DISEÑAR ESCENAS → Coherentes entre sí, con visión de director
    4. 👁️ REVIEW → Usuario aprueba/rechaza cada escena
    5. 🖼️ GENERAR/DESCARGAR IMÁGENES
    6. 🎙️ GENERAR AUDIO
    7. 🎬 ENSAMBLAR CON FFMPEG
    """

    def __init__(self, videos_dir: Path = VIDEOS_DIR):
        self.videos_dir = videos_dir
        self.videos_dir.mkdir(exist_ok=True)
        self._progreso: dict = {}
        self._proyectos: dict = {}  # id -> VideoProyecto
        self.translation_cache = {}
        self.translation_ttl = TRANSLATION_CACHE_TTL
        self._cargar_cache()

    def _cargar_cache(self):
        if TRANSLATION_CACHE_PATH.exists():
            try:
                with open(TRANSLATION_CACHE_PATH, "r", encoding="utf-8") as f:
                    self.translation_cache = json.load(f)
                # Purge expired entries
                now = int(time.time())
                self.translation_cache = {
                    k: v for k, v in self.translation_cache.items()
                    if now - v.get("timestamp", 0) < self.translation_ttl
                }
            except Exception as e:
                print(f"[TRAD] Error cargando caché: {e}")
                self.translation_cache = {}

    def _guardar_cache(self):
        try:
            with open(TRANSLATION_CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(self.translation_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[TRAD] Error guardando caché: {e}")

    def _get_proyecto_dir(self, proyecto_id: str) -> Path:
        d = self.videos_dir / proyecto_id
        d.mkdir(exist_ok=True)
        return d

    def _guardar_proyecto(self, proyecto: VideoProyecto):
        path = self.videos_dir / f"{proyecto.id}.json"
        with open(path, "w", encoding="utf-8") as f:
            data = asdict(proyecto)
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _cargar_proyecto(self, proyecto_id: str) -> Optional[VideoProyecto]:
        path = self.videos_dir / f"{proyecto_id}.json"
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return VideoProyecto(**data)

    def _actualizar_estado(self, proyecto_id: str, estado: str, error: str = None):
        proyecto = self._cargar_proyecto(proyecto_id)
        if proyecto:
            proyecto.estado = estado
            if error:
                proyecto.error = error
            self._guardar_proyecto(proyecto)

    def _actualizar_progreso(self, proyecto_id: str, progreso: int):
        progreso = max(0, min(100, progreso))
        self._progreso[proyecto_id] = progreso
        # Persistir en el JSON para que el proceso principal (API) lo vea
        proyecto = self._cargar_proyecto(proyecto_id)
        if proyecto:
            proyecto.progreso = progreso
            self._guardar_proyecto(proyecto)

    def obtener_progreso(self, proyecto_id: str) -> int:
        # Intentar desde memoria primero (si estamos en el mismo proceso)
        if proyecto_id in self._progreso:
            return self._progreso[proyecto_id]
        # Si no, leer del JSON
        proyecto = self._cargar_proyecto(proyecto_id)
        return proyecto.progreso if proyecto and hasattr(proyecto, 'progreso') else 0

    # ================================================================
    # FASE 1+2: ANALIZAR TEMA
    # ================================================================
    async def analizar_tema(self, tema: str, prompt: str, groq_client=None, proyecto_id: str = None) -> str:
        """
        Fase 1+2: Leer prompt y analizar como Director de Cine
        Returns: proyecto_id
        """
        if not proyecto_id:
            proyecto_id = f"proyecto_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        work_dir = self._get_proyecto_dir(proyecto_id)

        # Translate prompt to English if possible
        english_prompt = await self._traducir_prompt(prompt)

        proyecto = VideoProyecto(
            id=proyecto_id,
            tema=tema,
            prompt=english_prompt,
            prompt_original=prompt,
            estado=VideoEstado.ANALIZANDO,
            creado_en=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        self._guardar_proyecto(proyecto)
        self._proyectos[proyecto_id] = proyecto
        self._actualizar_progreso(proyecto_id, 10)

        # Analizar tema con Groq using English prompt
        analisis = await self._analizar_con_ia(proyecto_id, tema, english_prompt, groq_client)
        self._actualizar_progreso(proyecto_id, 30)

        return proyecto_id

    async def _analizar_con_ia(self, proyecto_id: str, tema: str, prompt: str, groq_client=None) -> dict:
        """La IA analiza el tema como Director de Cine"""
        system_prompt = """
Eres un DIRECTOR DE CINE experto en videos para YouTube.
Tu trabajo es ANALIZAR cualquier tema y diseñar la visión cinematográfica.

Analiza:
- TONO GENERAL (misterioso, épico, emotivo, dinámico, etc.)
- ESTILO VISUAL (documental, cinematográfico, minimalista, dramático, etc.)
- ATMÓSFERA (oscura, luminosa, íntima, grandiosa, etc.)
- PÚBLICO OBJETIVO
- DURACIÓN ESTIMADA (basada en la complejidad)
- REFERENCIA CINEMATOGRÁFICA (película o estilo similar)

Responde SOLO con JSON válido, sin markdown ni texto extra:
{
    "tono_general": "...",
    "estilo_visual": "...",
    "atmosfera": "...",
    "publico_objetivo": "...",
    "duracion_estimada": "2-4 minutos",
    "referencia_cinematografica": "..."
}
"""
        user_prompt = f"""
TEMA: {tema}
DESCRIPCIÓN: {prompt}

Analiza este tema como director de cine profesional.
"""

        if groq_client:
            response = groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.7,
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            texto = response.choices[0].message.content.strip()
            # Limpiar markdown si existe
            texto = re.sub(r'^```json\s*', '', texto)
            texto = re.sub(r'\s*```$', '', texto)
            analisis = json.loads(texto)
        else:
            analisis = {
                "tono_general": "documental informativo",
                "estilo_visual": "cinematográfico profesional",
                "atmosfera": "misteriosa y reveladora",
                "publico_objetivo": "público general interesado en el tema",
                "duracion_estimada": "2-3 minutos",
                "referencia_cinematografica": "documental de Discovery Channel"
            }

        proyecto = self._cargar_proyecto(proyecto_id)
        if proyecto:
            proyecto.analisis = analisis
            self._guardar_proyecto(proyecto)

        return analisis

    # ================================================================
    # FASE 3: DISEÑAR ESCENAS
    # ================================================================
    async def disenar_escenas(self, proyecto_id: str, groq_client=None) -> list:
        """
        Fase 3: Diseñar escenas coherentes como Director de Cine
        """
        self._actualizar_estado(proyecto_id, VideoEstado.DISENANDO)
        self._actualizar_progreso(proyecto_id, 40)

        proyecto = self._cargar_proyecto(proyecto_id)
        if not proyecto:
            raise ValueError(f"Proyecto {proyecto_id} no encontrado")

        analisis = proyecto.analisis or {}
        tono = analisis.get("tono_general", "documental")
        estilo = analisis.get("estilo_visual", "cinematográfico")
        atmosfera = analisis.get("atmosfera", "profesional")

        # Generar guión + escenas diseñadas
        system_prompt = f"""
Eres un DIRECTOR DE CINE PROFESIONAL creando un video LARGO y detallado para YouTube.

CONTEXTO DEL VIDEO:
- Tono: {tono}
- Estilo visual: {estilo}
- Atmósfera: {atmosfera}

Tu trabajo:
1. Crear un GUIÓN EXTENSO Y DETALLADO con narración profunda y envolvente
2. DISEÑAR MUCHAS ESCENAS con visión cinematográfica completa

Para cada escena debes definir:
- texto_narracion: Lo que dice el narrador. DEBE SER EXTENSO: entre 60 y 100 palabras por escena. Incluye datos, reflexiones, descripciones vívidas y ganchos narrativos. NO seas breve.
- descripcion_visual: Qué se ve en pantalla (MANTÉN ESTRICTA COHERENCIA VISUAL Y NARRATIVA con el TEMA ORIGINAL: "{proyecto.tema}" y la DESCRIPCIÓN ORIGINAL: "{proyecto.prompt}". TODAS las imágenes deben parecer del mismo video).
- angulo_camara: Plano general, primer plano, picado, contrapicado, etc.
- iluminacion: Dramática, natural, contraluz, dorada, etc.
- paleta_colores: Fría, cálida, neutra, alto contraste, etc.
- movimiento: Estático, paneo, zoom, travelling, etc.
- emocion: Qué debe transmitir (tensión, asombro, curiosidad, etc.)
- query_pexels: Búsqueda en inglés para Pexels (máx 5 palabras)

REGLAS CRÍTICAS DE DURACIÓN:
- GENERA ENTRE 10 Y 15 ESCENAS. Esto NO es opcional. Un video profesional necesita al menos 10 escenas.
- CADA ESCENA DEBE tener un 'texto_narracion' de MÍNIMO 60 PALABRAS y MÁXIMO 100 PALABRAS. NO lo dejes corto. Cuenta las palabras mentalmente.
- El guion_completo debe ser la concatenación de TODAS las narraciones, resultando en un texto de al menos 800 palabras.
- CADA ESCENA debe ser COHERENTE con las demás (misma línea visual)
- La escena 1 debe tener un HOOK visual impactante
- Las transiciones entre escenas deben ser fluidas y naturales
- Incluye una escena final con CTA poderoso y memorable
- NO repitas información entre escenas. Cada escena debe aportar algo nuevo.

Responde SOLO con JSON válido, sin markdown ni texto extra:
{{
    "guion_completo": "texto completo del guión narrativo (800+ palabras)",
    "escenas": [
        {{
            "numero": 1,
            "titulo": "Apertura impactante",
            "texto_narracion": "Escribe aquí MÍNIMO 60 palabras de narración profesional, detallada, envolvente...",
            "descripcion_visual": "Descripción cinematográfica detallada...",
            "angulo_camara": "...",
            "iluminacion": "...",
            "paleta_colores": "...",
            "movimiento": "...",
            "emocion": "...",
            "query_pexels": "..."
        }}
    ]
}}
"""
        user_prompt = f"""
TEMA: {proyecto.tema}
DESCRIPIÓN: {proyecto.prompt}

Diseña el video completo como director de cine.
"""

        if groq_client:
            response = groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.7,
                max_tokens=9192,
                response_format={"type": "json_object"}
            )
            texto = response.choices[0].message.content.strip()
            # Limpiar TODO tipo de markdown y texto extra
            texto = re.sub(r'^```json\s*', '', texto)
            texto = re.sub(r'\s*```$', '', texto)
            texto = texto.strip()
            # Si empieza con { o [, es JSON válido
            if not texto.startswith('{'):
                # Buscar el primer {
                idx = texto.find('{')
                if idx != -1:
                    texto = texto[idx:]
            data = json.loads(texto)
        else:
            data = self._generar_escenas_placeholder(proyecto.tema)

        # Guardar guión y escenas
        proyecto.guion_completo = data.get("guion_completo", "")
        escenas_data = data.get("escenas", [])

        escenas_disenadas = []
        for e in escenas_data:
            escena = EscenaDisenada(
                numero=e.get("numero", len(escenas_disenadas) + 1),
                titulo=e.get("titulo", f"Escena {len(escenas_disenadas)+1}"),
                texto_narracion=e.get("texto_narracion", ""),
                descripcion_visual=e.get("descripcion_visual", ""),
                angulo_camara=e.get("angulo_camara", ""),
                iluminacion=e.get("iluminacion", ""),
                paleta_colores=e.get("paleta_colores", ""),
                movimiento=e.get("movimiento", ""),
                emocion=e.get("emocion", ""),
                query_pexels=e.get("query_pexels", "cinematic dramatic"),
                aprobada=True  # Aprobadas por defecto
            )
            escenas_disenadas.append(asdict(escena))

        proyecto.escenas_disenadas = escenas_disenadas
        proyecto.estado = VideoEstado.EN_REVIEW
        self._guardar_proyecto(proyecto)
        self._actualizar_progreso(proyecto_id, 60)

        return escenas_disenadas

    def _generar_escenas_placeholder(self, tema: str) -> dict:
        return {
            "guion_completo": f"Video sobre {tema}.",
            "escenas": [
                {
                    "numero": 1,
                    "titulo": "Introducción",
                    "texto_narracion": f"Descubre los secretos de {tema}.",
                    "descripcion_visual": "Imagen cinematográfica introductoria",
                    "angulo_camara": "Plano general",
                    "iluminacion": "Dramática",
                    "paleta_colores": "Oscura con acentos cálidos",
                    "movimiento": "Zoom lento hacia adelante",
                    "emocion": "Curiosidad",
                    "query_pexels": "mystery cinematic dramatic"
                },
                {
                    "numero": 2,
                    "titulo": "Desarrollo",
                    "texto_narracion": "Los detalles revelan la verdad.",
                    "descripcion_visual": "Secuencia de revelación",
                    "angulo_camara": "Primer plano",
                    "iluminacion": "Contraluz",
                    "paleta_colores": "Cálida dorada",
                    "movimiento": "Paneo suave",
                    "emocion": "Asombro",
                    "query_pexels": "revelation light cinematic"
                },
                {
                    "numero": 3,
                    "titulo": "Conclusión",
                    "texto_narracion": "Ahora sabes la verdad completa.",
                    "descripcion_visual": "Cierre poderoso",
                    "angulo_camara": "Plano general épico",
                    "iluminacion": "Luz cenital",
                    "paleta_colores": "Neutra elegante",
                    "movimiento": "Zoom out revelador",
                    "emocion": "Satisfacción",
                    "query_pexels": "ending cinematic epic"
                }
            ]
        }

    # ================================================================
    # FASE 4: REVIEW (aprobar/repetir escenas)
    # ================================================================
    def aprobar_escena(self, proyecto_id: str, escena_num: int) -> bool:
        proyecto = self._cargar_proyecto(proyecto_id)
        if not proyecto:
            return False
        for escena in proyecto.escenas_disenadas:
            if escena["numero"] == escena_num:
                escena["aprobada"] = True
                self._guardar_proyecto(proyecto)
                return True
        return False

    def rechazar_escena(self, proyecto_id: str, escena_num: int, razon: str, groq_client=None) -> dict:
        """Repetir el diseño de una escena"""
        proyecto = self._cargar_proyecto(proyecto_id)
        if not proyecto:
            return None

        escena_vieja = None
        for e in proyecto.escenas_disenadas:
            if e["numero"] == escena_num:
                escena_vieja = e
                break

        if not escena_vieja:
            return None

        # Rediseñar con IA
        if groq_client:
            system_prompt = f"""
Rediseña esta escena de video como director de cine profesional.

ESCENA ANTERIOR (que no gustó):
- Título: {escena_vieja['titulo']}
- Visual: {escena_vieja['descripcion_visual']}
- Narración: {escena_vieja['texto_narracion']}

RAZÓN DEL CAMBIO: {razon}

Crea una versión MEJOR y DIFERENTE manteniendo ESTRICTA COHERENCIA con el documento original:
- Tema Original: {proyecto.tema}
- Descripción Original: {proyecto.prompt}
- Tono: {proyecto.analisis.get('tono_general', '')}
- Estilo: {proyecto.analisis.get('estilo_visual', '')}
(Las imágenes deben seguir exactamente la línea del documento original, solo ajustando lo que pide la razón del cambio)

Responde SOLO JSON:
{{
    "numero": {escena_num},
    "titulo": "...",
    "texto_narracion": "...",
    "descripcion_visual": "...",
    "angulo_camara": "...",
    "iluminacion": "...",
    "paleta_colores": "...",
    "movimiento": "...",
    "emocion": "...",
    "query_pexels": "..."
}}
"""
            response = groq_client.chat.completions.create(
                messages=[{"role": "system", "content": system_prompt}],
                model="llama-3.3-70b-versatile",
                temperature=0.9,
                max_tokens=500
            )
            texto = response.choices[0].message.content.strip()
            texto = re.sub(r'^```json\s*', '', texto)
            texto = re.sub(r'\s*```$', '', texto)
            nueva_escena = json.loads(texto)
        else:
            nueva_escena = escena_vieja.copy()
            nueva_escena["titulo"] += " (v2)"

        # Reemplazar en el proyecto
        for i, e in enumerate(proyecto.escenas_disenadas):
            if e["numero"] == escena_num:
                nueva_escena["aprobada"] = True
                proyecto.escenas_disenadas[i] = nueva_escena
                break

        self._guardar_proyecto(proyecto)
        return nueva_escena

    # ================================================================
    # NUEVA ARQUITECTURA: MODO EDITOR STORYBOARD
    # ================================================================
    
    async def pre_producir_video(self, proyecto_id: str) -> dict:
        """
        Fase 1-5: Genera el guion y las imágenes (Storyboard) sin audio ni ensamblaje.
        """
        proyecto = self._cargar_proyecto(proyecto_id)
        if not proyecto: raise ValueError("Proyecto no encontrado")
        
        work_dir = self._get_proyecto_dir(proyecto_id)
        
        # Las aprobamos todas por defecto en la pre-producción
        for i, e in enumerate(proyecto.escenas_disenadas):
            proyecto.escenas_disenadas[i]["aprobada"] = True
            
        escenas_aprobadas = [e for e in proyecto.escenas_disenadas if e.get("aprobada", False)]
        
        self._actualizar_estado(proyecto_id, VideoEstado.GENERANDO_IMAGENES)
        self._actualizar_progreso(proyecto_id, 40)
        
        await self._generar_escenas_visuales(proyecto_id, escenas_aprobadas, work_dir)
        
        self._actualizar_estado(proyecto_id, VideoEstado.EN_REVIEW)
        self._actualizar_progreso(proyecto_id, 80)
        
        # Volvemos a cargar para tener las rutas de imágenes actualizadas
        proyecto = self._cargar_proyecto(proyecto_id)
        return asdict(proyecto)

    async def regenerar_imagen_escena(self, proyecto_id: str, escena_num: int, nuevo_prompt: str = None) -> str:
        """
        Regenera la imagen de una escena específica.
        """
        proyecto = self._cargar_proyecto(proyecto_id)
        if not proyecto: raise ValueError("Proyecto no encontrado")
        
        escena_obj = None
        for e in proyecto.escenas_disenadas:
            if e["numero"] == escena_num:
                escena_obj = e
                break
                
        if not escena_obj: raise ValueError("Escena no encontrada")
        
        if nuevo_prompt:
            escena_obj["descripcion_visual"] = nuevo_prompt
            
        work_dir = self._get_proyecto_dir(proyecto_id)
        
        # Pasamos solo esta escena al generador visual
        await self._generar_escenas_visuales(proyecto_id, [escena_obj], work_dir)
        
        # Marcar que el video necesita ser re-renderizado
        proyecto.estado = VideoEstado.NEEDS_RENDER
        self._guardar_proyecto(proyecto)
        
        # Devolver el path de la nueva imagen
        for e in proyecto.escenas_disenadas:
            if e["numero"] == escena_num:
                return e.get("imagen_path")
        return ""

    async def ensamblar_video_final(self, proyecto_id: str, generar_voz_func=None, resolucion: str = "1080") -> str:
        """
        Fases 6-7: Una vez el Storyboard está aprobado por el usuario, genera voz y ensambla.
        """
        proyecto = self._cargar_proyecto(proyecto_id)
        if not proyecto: raise ValueError("Proyecto no encontrado")
        work_dir = self._get_proyecto_dir(proyecto_id)
        # En esta versión, todas las escenas diseñadas se consideran aprobadas para ensamblaje.
        escenas_aprobadas = proyecto.escenas_disenadas
        
        if proyecto.narracion:
            self._actualizar_estado(proyecto_id, VideoEstado.GENERANDO_VEZ)
            self._actualizar_progreso(proyecto_id, 85)

            escenas_con_texto = [e.get("texto_narracion") for e in escenas_aprobadas if len(e.get("texto_narracion") or "") > 5]
            if len(proyecto.guion_completo or "") < 50 and escenas_con_texto:
                texto_audio = " ".join(escenas_con_texto)
            else:
                texto_audio = proyecto.guion_completo or " ".join(escenas_con_texto)

            if not texto_audio.strip():
                texto_audio = "Video generado con Hermatron."

            audio_path = await self._generar_audio(
                proyecto_id, texto_audio, work_dir,
                generar_voz_func, proyecto.voz
            )
            proyecto.audio_path = audio_path
        else:
            proyecto.audio_path = None

        self._guardar_proyecto(proyecto)

        self._actualizar_estado(proyecto_id, VideoEstado.ENSAMBLANDO)
        self._actualizar_progreso(proyecto_id, 95)

        video_final = await self._ensamblar_video(
            proyecto_id, work_dir, proyecto.audio_path, escenas_aprobadas, resolucion=resolucion
        )
        
        if not video_final or not Path(video_final).exists():
             print("[VIDEO] Error crítico: El ensamblaje no generó archivo.")
             self._actualizar_estado(proyecto_id, VideoEstado.ERROR, "Error en ensamblaje de FFmpeg")
             return ""

        self._actualizar_progreso(proyecto_id, 100)

        proyecto.estado = VideoEstado.COMPLETADO
        proyecto.archivo_final = Path(video_final).name if video_final else None
        if video_final:
            proyecto.duracion = self._obtener_duracion(video_final)
            proyecto.tamano = self._formatear_tamano(Path(video_final).stat().st_size)
        self._guardar_proyecto(proyecto)

        return video_final

    # ================================================================
    # FASE 5-7: PRODUCIR VIDEO COMPLETO (Flujo Antiguo/Automático)
    # ================================================================
    async def producir_video(self, proyecto_id: str, groq_client=None,
                              generar_voz_func=None) -> str:
        """
        Fases 5-7: Generar imágenes, audio y ensamblar
        """
        proyecto = self._cargar_proyecto(proyecto_id)
        if not proyecto:
            raise ValueError(f"Proyecto {proyecto_id} no encontrado")

        work_dir = self._get_proyecto_dir(proyecto_id)

        # Verificar que hay escenas aprobadas
        escenas_aprobadas = [e for e in proyecto.escenas_disenadas if e.get("aprobada", False)]
        if not escenas_aprobadas:
            raise ValueError("No hay escenas aprobadas. Aprueba al menos una.")

        try:
            # FASE 5: Generar imágenes (60-80%)
            self._actualizar_estado(proyecto_id, VideoEstado.GENERANDO_IMAGENES)
            self._actualizar_progreso(proyecto_id, 65)

            await self._generar_escenas_visuales(proyecto_id, escenas_aprobadas, work_dir)
            self._actualizar_progreso(proyecto_id, 80)

            # FASE 6: Generar audio (80-90%)
            if proyecto.narracion:
                self._actualizar_estado(proyecto_id, VideoEstado.GENERANDO_VEZ)
                self._actualizar_progreso(proyecto_id, 85)

                # Priorizar narraciones detalladas de escenas si el guion es muy corto
                escenas_con_texto = [e.get("texto_narracion", "") for e in escenas_aprobadas if len(e.get("texto_narracion", "")) > 5]
                if len(proyecto.guion_completo or "") < 50 and escenas_con_texto:
                    texto_audio = " ".join(escenas_con_texto)
                else:
                    texto_audio = proyecto.guion_completo or " ".join(escenas_con_texto)

                if not texto_audio.strip():
                    texto_audio = "Video generado con Hermatron."

                print(f"[AUDIO] Texto para audio: {texto_audio[:100]}...")

                audio_path = await self._generar_audio(
                    proyecto_id, texto_audio, work_dir,
                    generar_voz_func, proyecto.voz
                )
                proyecto.audio_path = audio_path
                print(f"[AUDIO] Audio generado en: {audio_path}")
            else:
                proyecto.audio_path = None

            self._actualizar_progreso(proyecto_id, 90)
            self._guardar_proyecto(proyecto)

            # FASE 7: Ensamblar (90-100%)
            self._actualizar_estado(proyecto_id, VideoEstado.ENSAMBLANDO)
            self._actualizar_progreso(proyecto_id, 95)

            video_final = await self._ensamblar_video(
                proyecto_id, work_dir, proyecto.audio_path, escenas_aprobadas
            )
            self._actualizar_progreso(proyecto_id, 100)

            # COMPLETADO
            proyecto.estado = VideoEstado.COMPLETADO
            proyecto.archivo_final = Path(video_final).name if video_final else None
            if video_final:
                proyecto.duracion = self._obtener_duracion(video_final)
                proyecto.tamano = self._formatear_tamano(Path(video_final).stat().st_size)
            self._guardar_proyecto(proyecto)

            print(f"[VIDEO]  Completado: {proyecto_id}")
            return video_final

        except Exception as e:
            print(f"[VIDEO]  Error: {e}")
            import traceback
            traceback.print_exc()
            self._actualizar_estado(proyecto_id, VideoEstado.ERROR, str(e))
            self._actualizar_progreso(proyecto_id, 0)
            raise

    def _get_resolucion_from_tema(self, tema: str) -> tuple[int, int]:
        texto = str(tema).lower()
        if any(w in texto for w in ["9:16", "9/16", "vertical", "tiktok", "reels", "shorts"]):
            return (1080, 1920) # 9:16 Full HD
        elif any(w in texto for w in ["1:1", "cuadrado", "square", "instagram", "post"]):
            return (1080, 1080) # 1:1
        return (1920, 1080) # 16:9 Full HD (default más estable para 1GB RAM)

    # ================================================================
    # FASE 5: Generar Imágenes
    # ================================================================
    async def _generar_escenas_visuales(self, proyecto_id: str, escenas: list, work_dir: Path):
        total = len(escenas)
        fuente_usada = "placeholder"
        
        proyecto = self._cargar_proyecto(proyecto_id)
        analisis = proyecto.analisis if (proyecto and hasattr(proyecto, 'analisis') and proyecto.analisis) else {}
        estilo_visual = analisis.get("estilo_visual", "cinematic")
        atmosfera = analisis.get("atmosfera", "professional")
        
        # ── COHERENCIA VISUAL: Seed compartido para TODO el proyecto ──
        # Todas las escenas usan el mismo seed para que Pollinations
        # genere imágenes con el mismo ADN artístico.
        project_seed = abs(hash(proyecto_id)) % 99999
        style_prefix = f"{estilo_visual}, {atmosfera} atmosphere, consistent art style"
        print(f"[VIDEO] Seed compartido del proyecto: {project_seed}, Estilo: {style_prefix}")

        for i, escena in enumerate(escenas):
            num_escena = escena.get("numero", i+1)
            print(f"[VIDEO] Procesando visuales para escena {num_escena} de {total}...")
            escena_dir = work_dir / f"escena_{num_escena}"
            escena_dir.mkdir(exist_ok=True)
            img_path = escena_dir / "imagen.png"

            # Construir un prompt robusto con PREFIJO DE ESTILO CONSISTENTE
            descripcion = escena.get("descripcion_visual", "")
            query = escena.get("query_pexels", "")
            
            # El style_prefix va primero para que Pollinations lo priorice
            query_mejorado = f"{style_prefix}, {descripcion}, {query}, highly detailed, masterpiece, 8k resolution, cinematic lighting"
            print(f"[VIDEO]  Generando con IA (Pollinations): {query_mejorado[:80]}...")
            
            width, height = self._get_resolucion_from_tema(proyecto.tema if proyecto else "")
            exito = await self._generar_imagen_pollinations(query_mejorado, str(img_path), width, height, seed=project_seed)
            if exito:
                fuente_usada = "pollinations"
                # Actualizar el path en la escena del proyecto
                for e_orig in proyecto.escenas_disenadas:
                    if e_orig.get("numero") == num_escena:
                        e_orig["imagen_path"] = str(img_path)
            else:
                print(f"[VIDEO]  Fallback Placeholder para escena {num_escena}")
                await self._generar_imagen_placeholder(
                    str(img_path), escena.get("descripcion_visual", f"Escena {num_escena}"),
                    indice=i, total=total, query=query
                )
                for e_orig in proyecto.escenas_disenadas:
                    if e_orig.get("numero") == num_escena:
                        e_orig["imagen_path"] = str(img_path)

            # Guardar metadata (SIEMPRE, sin importar la fuente)
            with open(escena_dir / "metadata.json", "w", encoding="utf-8") as f:
                json.dump({
                    "indice": num_escena,
                    "titulo": escena.get("titulo", ""),
                    "texto": escena.get("texto_narracion", ""),
                    "visual": escena.get("descripcion_visual", ""),
                    "query": query,
                    "aprobada": escena.get("aprobada", True),
                    "imagen": str(img_path),
                    "fuente": fuente_usada
                }, f, ensure_ascii=False, indent=2)

            self._actualizar_progreso(proyecto_id, 65 + int((i + 1) / total * 15))
            fuente_usada = "placeholder"  # Reset para siguiente escena
            
            # Pequeña pausa para no saturar la API gratuita de Pollinations
            await asyncio.sleep(1.5)
        
        self._guardar_proyecto(proyecto)
        print(f"[VIDEO]  {total} escenas procesadas y guardadas")
        
        # Forzar liberación de memoria tras procesar muchas imágenes
        import gc
        gc.collect()

    async def _generar_imagen_pollinations(self, query: str, ruta_salida: str, width: int = 2560, height: int = 1440, seed: int = None) -> bool:
        """
        Cadena de fuentes de imágenes (orden: velocidad + confiabilidad):
        1. Pollinations.ai — IA gratis con seed compartido para coherencia
        2. Picsum Photos — siempre disponible, sin API key
        """
        import httpx
        import urllib.parse
        import random

        # Limpieza inicial del prompt
        query_limpio = query[:1000].replace("\n", " ").replace('"', "").strip()

        # ── OPTIMIZACIÓN DE PROMPT (Director de Arte IA) ──
        query_opt = await self._optimizar_prompt_imagen(query_limpio)
        query_cod = urllib.parse.quote(query_opt)
        
        # ── FUENTE 1: Pollinations.ai (IA Generativa Principal) ──
        gen_w, gen_h = width, height
        # Usar seed del proyecto si se proporcionó (coherencia visual)
        # Si no, generar uno aleatorio (para regeneraciones individuales)
        if seed is None:
            seed = random.randint(1, 99999)
        url_poll = (
            f"https://image.pollinations.ai/prompt/{query_cod}"
            f"?width={gen_w}&height={gen_h}&nologo=true&seed={seed}&model=flux"
        )
        try:
            print(f"[IMAGENES] Pollinations 720p: {query_opt[:50]}...")
            async with httpx.AsyncClient(timeout=50.0, follow_redirects=True) as hc:
                resp = await hc.get(url_poll)
                if resp.status_code == 200 and len(resp.content) > 15000:
                    with open(ruta_salida, "wb") as f:
                        f.write(resp.content)
                    print(f"[IMAGENES] Pollinations OK ({len(resp.content)//1024} KB)")
                    return True
                print(f"[IMAGENES] Pollinations status {resp.status_code}, pasando a Picsum...")
        except Exception as e:
            print(f"[IMAGENES] Pollinations timeout/error: {e} — pasando a Picsum...")

        # ── FUENTE 3: Picsum Photos (always-on, sin API key) ──────────
        try:
            print("[IMAGENES] Picsum Photos fallback...")
            picsum_seed = (hash(query_limpio) % 1000) + 1
            url_picsum = f"https://picsum.photos/seed/{picsum_seed}/1280/720"
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as hc:
                resp = await hc.get(url_picsum)
                if resp.status_code == 200 and len(resp.content) > 10000:
                    with open(ruta_salida, "wb") as f:
                        f.write(resp.content)
                    print(f"[IMAGENES] Picsum OK ({len(resp.content)//1024} KB)")
                    return True
        except Exception as e:
            print(f"[IMAGENES] Picsum error: {e}")

        print("[IMAGENES] Todas las fuentes fallaron — usando placeholder")
        return False



    async def _buscar_imagen_pexels(self, query: str, ruta_salida: str) -> bool:
        """Buscar imagen en Pexels API (requiere API key)"""
        try:
            import httpx
            headers = {"Authorization": PEXELS_API_KEY}
            url = f"https://api.pexels.com/v1/search?query={query}&per_page=3&size=large"

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)
                if response.status_code != 200:
                    return False

                data = response.json()
                fotos = data.get("photos", [])
                if not fotos:
                    return False

                foto = fotos[0]
                img_url = foto["src"]["large"]
                print(f"[PEXELS] Descargando: {foto['photographer']} - {query}")

                img_response = await client.get(img_url)
                if img_response.status_code == 200:
                    with open(ruta_salida, "wb") as f:
                        f.write(img_response.content)
                    return True
                return False
        except Exception as e:
            print(f"[PEXELS] Error: {e}")
            return False

    async def _generar_imagen_placeholder(self, ruta_salida: str, descripcion: str,
                                           indice: int = 0, total: int = 1, query: str = ""):
        """Generar placeholder CINEMATOGRÁFICO rápido (gradiente por líneas, no pixel-a-pixel)"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            import random
            random.seed(indice + total)

            width, height = 1920, 1080
            img = Image.new('RGB', (width, height))
            draw = ImageDraw.Draw(img)

            # Paletas cinematográficas
            paletas = [
                ((10, 60, 120), (0, 180, 160)),   # Aurora Boreal
                ((200, 80, 30), (255, 160, 50)),   # Atardecer épico
                ((0, 80, 160), (0, 180, 220)),     # Océano profundo
                ((20, 80, 40), (60, 180, 80)),     # Bosque mágico
                ((40, 10, 80), (100, 30, 150)),    # Galaxia
                ((180, 30, 10), (255, 120, 20)),   # Fuego dramático
            ]
            c1, c2 = paletas[indice % len(paletas)]

            # Gradiente eficiente: 1 línea horizontal por iteración (no pixel a pixel)
            for y in range(height):
                t = y / height
                r = int(c1[0] * (1 - t) + c2[0] * t)
                g = int(c1[1] * (1 - t) + c2[1] * t)
                b = int(c1[2] * (1 - t) + c2[2] * t)
                draw.line([(0, y), (width, y)], fill=(r, g, b))

            # Viñeta simple con rectángulos transparentes (rápido)
            overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            ov_draw = ImageDraw.Draw(overlay)
            ov_draw.rectangle([0, 0, width, height], fill=(0, 0, 0, 60))
            img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
            draw = ImageDraw.Draw(img)

            # Texto
            try:
                font = ImageFont.truetype("arial.ttf", 48)
                font_small = ImageFont.truetype("arial.ttf", 28)
            except:
                font = ImageFont.load_default()
                font_small = font

            text = f"Escena {indice + 1}"
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            draw.text(((width - text_w) // 2, height // 2 - 40), text, fill="white", font=font)

            desc = descripcion[:70] + "..." if len(descripcion) > 70 else descripcion
            bbox2 = draw.textbbox((0, 0), desc, font=font_small)
            desc_w = bbox2[2] - bbox2[0]
            draw.text(((width - desc_w) // 2, height // 2 + 20), desc, fill=(220, 220, 220), font=font_small)

            if ruta_salida.endswith('.png'):
                ruta_salida = ruta_salida[:-4] + '.jpg'
            img.save(ruta_salida, "JPEG", quality=88)

        except Exception as e:
            print(f"[PLACEHOLDER] Error: {e}")
            self._crear_imagen_simple(ruta_salida, indice)


    async def _generar_imagen_unsplash(self, query: str, ruta_salida: str, use_source: bool = False) -> bool:
        """Obtener una imagen libre de Unsplash.
        Si `use_source` es True, usa el endpoint público sin API key.
        Retorna True si la descarga fue exitosa.
        """
        try:
            import httpx
            import urllib.parse
            if use_source:
                url = f"https://source.unsplash.com/1920x1080?{urllib.parse.quote(query)}"
            else:
                url = f"https://api.unsplash.com/photos/random?query={urllib.parse.quote(query)}&orientation=landscape&client_id={UNSPLASH_ACCESS_KEY}"
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    if not use_source:
                        data = resp.json()
                        img_url = data.get('urls', {}).get('full') or data.get('urls', {}).get('regular')
                        if not img_url:
                            print("[UNSPLASH] No se encontró URL en respuesta API")
                            return False
                        resp = await client.get(img_url)
                    with open(ruta_salida, "wb") as f:
                        f.write(resp.content)
                    return True
                print(f"[UNSPLASH] Falló descarga (status {resp.status_code})")
        except Exception as e:
            print(f"[UNSPLASH] Error: {e}")
        return False


    def _crear_imagen_simple(self, ruta: str, indice: int):
        import struct, zlib
        width, height = 1920, 1080
        colores_base = [
            (15, 5, 30), (5, 15, 40), (40, 10, 5),
            (5, 25, 20), (25, 5, 35), (35, 15, 5)
        ]
        r, g, b = colores_base[indice % len(colores_base)]

        def make_png(w, h, rr, gg, bb):
            signature = b'\x89PNG\r\n\x1a\n'
            def chunk(ct, data):
                c = ct + data
                return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)
            ihdr = chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
            raw_data = b''
            for y in range(h):
                raw_data += b'\x00'
                for x in range(w):
                    factor = (x + y) / (w + h)
                    raw_data += bytes([min(int(rr + factor*30), 255), min(int(gg + factor*20), 255), min(int(bb + factor*40), 255)])
            idat = chunk(b'IDAT', zlib.compress(raw_data))
            iend = chunk(b'IEND', b'')
            return signature + ihdr + idat + iend

        with open(ruta, 'wb') as f:
            f.write(make_png(width, height, r, g, b))

    # ================================================================
    # FASE 6: Generar Audio
    # ================================================================
    async def _generar_audio(self, proyecto_id: str, guion: str, work_dir: Path,
                              generar_voz_func=None, voz: str = "es-MX-JorgeNeural") -> str:
        audio_path = work_dir / "audio_narracion.mp3"

        # ── FIX CRÍTICO: Usar el texto COMPLETO sin truncar ──
        # El texto ya viene ensamblado correctamente desde ensamblar_video_final()
        # con todas las narraciones de todas las escenas concatenadas.
        # NO truncar a 500 caracteres (eso causaba videos de solo 27 segundos).
        texto_completo = guion.strip()
        if not texto_completo:
            texto_completo = "Video generado con Hermatron."
        
        print(f"[AUDIO] Texto completo para narración: {len(texto_completo)} caracteres ({len(texto_completo.split())} palabras)")

        # Intento 1: ElevenLabs
        if ELEVENLABS_API_KEY:
            try:
                from app.voz_elevenlabs import generar_voz_elevenlabs
                # Si el id es de edge-tts (tiene guiones como es-MX), usar map inverso o saltar
                if "-" in voz and voz not in ["pNInz6obpgDQGcFmaJgB", "EXAVITQu4vr4xnSDxMaL"]:
                    pass # Saltar a edge-tts
                else:
                    print(f"[AUDIO] Generando con ElevenLabs ({voz})...")
                    ruta = await generar_voz_elevenlabs(
                        texto_completo, voz, "audio_narracion.mp3", work_dir
                    )
                    print(f"[AUDIO]  ElevenLabs OK")
                    return ruta
            except Exception as e:
                print(f"[AUDIO] Error ElevenLabs: {e}")

        # Intento 2: edge-tts
        try:
            import edge_tts
            import asyncio
            edge_voz = voz if "-" in voz else "es-MX-JorgeNeural"
            print(f"[AUDIO] Generando con edge-tts ({edge_voz})...")
            communicate = edge_tts.Communicate(texto_completo, edge_voz, rate="-5%", volume="+5%")
            await asyncio.wait_for(communicate.save(str(audio_path)), timeout=120.0)
            print(f"[AUDIO]  edge-tts OK")
            return str(audio_path)
        except Exception as e:
            print(f"[AUDIO] Error edge-tts: {e}")

        # Intento 3: gTTS (Nube / Bulletproof)
        try:
            import gtts
            import asyncio
            print(f"[AUDIO] Generando con gTTS (respaldo)...")
            tts = gtts.gTTS(text=texto_completo, lang='es', tld='com.mx')
            # Ejecutar llamada sincrónica en un hilo separado para no bloquear el Event Loop de FastAPI
            await asyncio.to_thread(tts.save, str(audio_path))
            print(f"[AUDIO]  gTTS OK")
            return str(audio_path)
        except Exception as e:
            print(f"[AUDIO] Error gTTS: {e}")

        # Intento 4: pyttsx3 (local, para pruebas)
        try:
            import pyttsx3
            print(f"[AUDIO] Generando con pyttsx3 (local)...")
            engine = pyttsx3.init()
            engine.setProperty('rate', 175)
            engine.setProperty('volume', 0.95)
            # Intentar voz española/latina
            voices = engine.getProperty('voices')
            for v in voices:
                if 'sabina' in v.name.lower() or 'es-' in v.id.lower():
                    engine.setProperty('voice', v.id)
                    break
            def run_pyttsx3():
                import pythoncom
                pythoncom.CoInitialize()
                engine.save_to_file(texto_completo, str(audio_path))
                engine.runAndWait()
                engine.stop()
            
            await asyncio.to_thread(run_pyttsx3)
            if Path(audio_path).exists():
                print(f"[AUDIO]  pyttsx3 OK")
                return str(audio_path)
        except Exception as e:
            print(f"[AUDIO] Error pyttsx3: {e}")

        raise Exception("No se pudo generar audio con ningún sistema")

    # ================================================================
    # FASE 7: Ensamblar con FFmpeg (usando subprocess.run para confiabilidad)
    # ================================================================
    def _run_ffmpeg(self, cmd: list) -> tuple:
        """Ejecutar FFmpeg con subprocess.run de forma segura (evitando deadlocks por buffer lleno)"""
        try:
            # Redirigir stdout a DEVNULL para evitar llenar el pipe, ya que FFmpeg es muy ruidoso.
            # Capturamos solo stderr que es donde FFmpeg reporta errores y progreso.
            kwargs = {
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.PIPE,
                "text": True,
            }
            if os.name == "nt":
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

            process = subprocess.Popen(cmd, **kwargs)
            try:
                # Esperar a que termine capturando la salida para evitar el deadlock del buffer
                _, stderr = process.communicate(timeout=600)
                return process.returncode == 0, stderr or ""
            except subprocess.TimeoutExpired:
                process.kill()
                _, stderr = process.communicate()
                return False, f"Timeout FFmpeg: {stderr[-500:] if stderr else ''}"
            
        except Exception as e:
            return False, str(e)


    async def _ensamblar_video(self, proyecto_id: str, work_dir: Path,
                                audio_path: Optional[str], escenas: list, resolucion: str = "1080") -> Optional[str]:
        """Ensamblar video con Ken Burns zoom + subtítulos sincronizados (FFmpeg nativo)"""
        video_final = self.videos_dir / f"{proyecto_id}.mp4"

        # ── Recopilar imágenes ────────────────────────────────────────
        imagenes = []
        for i, escena in enumerate(escenas):
            num_escena = escena.get("numero", i + 1)
            img = work_dir / f"escena_{num_escena}" / "imagen.jpg"
            if not img.exists():
                img = work_dir / f"escena_{num_escena}" / "imagen.png"
            if img.exists():
                imagenes.append((str(img), escena.get("texto_narracion", "")))

        if not imagenes:
            print("[VIDEO] Sin imágenes")
            return None

        print(f"[VIDEO] Ensamblando {len(imagenes)} escenas con zoom + SRT a {resolucion}p...")

        try:
            import PIL.Image
            
            # Calcular duración
            dur_total = 10.0 # Por defecto
            if audio_path and Path(audio_path).exists():
                dur_total = self._obtener_duracion_audio(audio_path)
                if dur_total <= 0: dur_total = 10.0
            
            # --- Lógica de tiempos proporcionales para sincronizar subtítulos ---
            # Si una escena no tiene texto, le damos un peso equivalente a 15 caracteres
            pesos_escenas = []
            for _, texto in imagenes:
                chars_escena = len(texto.strip())
                peso = chars_escena if chars_escena > 0 else 15
                pesos_escenas.append(peso)
                
            total_peso = sum(pesos_escenas)
            if total_peso == 0: total_peso = 1
            
            duraciones_escenas = []
            for peso in pesos_escenas:
                dur = (peso / total_peso) * dur_total
                duraciones_escenas.append(dur)

            # --- NUEVA LÓGICA DE STREAMING PARA VIDEOS LARGOS ---
            if dur_total > MAX_IN_MEMORY_DURATION:
                print(f"[VIDEO] Duración ({dur_total:.1f}s) excede umbral ({MAX_IN_MEMORY_DURATION}s). Usando streaming helper.")
                
                # Obtener resolución del proyecto
                proyecto = self._cargar_proyecto(proyecto_id)
                width, height = self._get_resolucion_from_tema(proyecto.tema if proyecto else "")
                
                clips_streaming = []
                total_clips = len(imagenes)
                for i, (img_path, _) in enumerate(imagenes):
                    # Progreso entre 90 y 96%
                    pct_streaming = 90 + int((i / total_clips) * 6)
                    self._actualizar_progreso(proyecto_id, pct_streaming)
                    
                    dur_escena = duraciones_escenas[i]
                    clip_path = work_dir / f"clip_stream_{i:02d}.mp4"
                    await asyncio.to_thread(crear_clip_imagen, img_path, dur_escena, width, height, str(clip_path))
                    clips_streaming.append(str(clip_path))
                
                # Concatenar y aplicar audio
                self._actualizar_progreso(proyecto_id, 97)
                # Aumentamos el timeout a 900s (15 min) para videos de 10 minutos
                await asyncio.to_thread(concatenar_segmentos, clips_streaming, str(video_final), audio_path)
                
                # Limpieza exhaustiva
                for c in clips_streaming:
                    try: Path(c).unlink(missing_ok=True)
                    except: pass
                
                # Limpiar archivo concat.txt si quedó (el helper lo limpia pero por si acaso)
                concat_txt = work_dir / "concat.txt"
                if concat_txt.exists(): concat_txt.unlink()
                
                return str(video_final)

            # Mapa de resoluciones
            res_map = {
                "720": (1280, 720),
                "1080": (1920, 1080),
                "1920": (2560, 1440), # 2K
                "2160": (3840, 2160)  # 4K
            }
            base_w, base_h = res_map.get(resolucion, (1280, 720))
            
            # Detectar si es vertical
            w, h = base_w, base_h
            try:
                with PIL.Image.open(imagenes[0][0]) as first_img:
                    orig_w, orig_h = first_img.size
                    if orig_h > orig_w: # Vertical 9:16
                        w, h = base_h, base_w
            except Exception:
                pass

            fps = 30  # Subido a 30 para evitar el efecto de 'tildarse' (lag)

            # ── PASO 1: clip por escena con Ken Burns ─────────────────
            clips = []
            total_escenas = len(imagenes)

            for i, (img_path, _) in enumerate(imagenes):
                # Progreso entre 91 y 96%
                pct_assembly = 91 + int((i / total_escenas) * 5)
                self._actualizar_progreso(proyecto_id, pct_assembly)
                
                dur_escena = duraciones_escenas[i]
                d_frames = int(dur_escena * fps)
                clip_path = work_dir / f"clip_{i:02d}.mp4"
                
                # Zoom estabilizado con OVERSAMPLING (para eliminar el "baile" / vibración)
                # Renderizamos internamente en 2K (2560x1440) y luego bajamos a 1080p.
                # Esto suaviza el movimiento sub-píxel.
                if i % 2 == 0:
                    zoom_expr = "zoom+0.0006"
                else:
                    zoom_expr = "if(eq(on,1),1.1,max(1.0006,zoom-0.0006))"
                
                # Agregamos +5 frames de margen para que el zoom nunca se quede quieto al final
                d_frames_safe = d_frames + 5
                
                # --- LÓGICA PRO DE ESCALADO Y ZOOM ---
                # Si es vertical, escalamos a un lienzo vertical (1440x2560) con crop al centro.
                # Si es horizontal, escalamos a un lienzo horizontal (2560x1440).
                if h > w: # Vertical (Shorts/TikTok)
                    # Tomamos la imagen y la escalamos para que cubra todo el alto vertical
                    canvas_w, canvas_h = 1080, 1920
                    vf_zoom = (
                        f"scale=1080:1920:force_original_aspect_ratio=increase,"
                        f"crop=1080:1920,"
                        f"zoompan=z='{zoom_expr}':d={d_frames_safe}:"
                        f"x='trunc(iw/2-(iw/zoom/2))':y='trunc(ih/2-(ih/zoom/2))':s=1080x1920:fps={fps},"
                        f"scale={w}:{h}"
                    )
                else: # Horizontal (YouTube)
                    canvas_w, canvas_h = 1920, 1080
                    vf_zoom = (
                        f"scale=1920:1080:force_original_aspect_ratio=increase,"
                        f"crop=1920:1080,"
                        f"zoompan=z='{zoom_expr}':d={d_frames_safe}:"
                        f"x='trunc(iw/2-(iw/zoom/2))':y='trunc(ih/2-(ih/zoom/2))':s=1920x1080:fps={fps},"
                        f"scale={w}:{h}"
                    )
                cmd_clip = [
                    "ffmpeg", "-y", "-loop", "1", "-t", f"{dur_escena:.4f}",
                    "-i", img_path, "-vf", vf_zoom,
                    "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                    "-t", f"{dur_escena:.4f}", str(clip_path)
                ]
                ok, err = await asyncio.to_thread(self._run_ffmpeg, cmd_clip)
                if ok and clip_path.exists():
                    clips.append(str(clip_path))
                else:
                    print(f"[VIDEO] zoompan falló escena {i} → estática: {err[:80]}")
                    cmd_st = [
                        "ffmpeg", "-y", "-loop", "1", "-t", f"{dur_escena:.3f}",
                        "-i", img_path,
                        "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,fps={fps}",
                        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                        "-t", f"{dur_escena:.3f}", str(clip_path)
                    ]
                    ok2, _ = await asyncio.to_thread(self._run_ffmpeg, cmd_st)
                    if ok2: clips.append(str(clip_path))

            if not clips:
                print("[VIDEO] No se generó ningún clip"); return None

            # ── PASO 2: concatenar clips ──────────────────────────────
            concat_path = work_dir / "clips.txt"
            with open(concat_path, "w", encoding="utf-8") as f:
                for c in clips:
                    f.write(f"file '{c.replace(chr(92), '/')}'\n")

            video_base = work_dir / "video_base.mp4"
            self._actualizar_progreso(proyecto_id, 97)
            ok, err = await asyncio.to_thread(self._run_ffmpeg, [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", str(concat_path), "-c", "copy", str(video_base)
            ])
            if not ok or not video_base.exists():
                print(f"[VIDEO] Concat error: {err[:150]}"); return None

            # ── PASO 3: SRT sincronizado ──────────────────────────────
            self._actualizar_progreso(proyecto_id, 98)
            srt_path = work_dir / "subtitulos.srt"
            srt_generado = False
            
            if audio_path and Path(audio_path).exists():
                print("[VIDEO] Solicitando subtítulos exactos a Groq Whisper...")
                srt_generado = await self._generar_srt_con_whisper(audio_path, str(srt_path))
                
            if not srt_generado:
                print("[VIDEO] Fallback: generando subtítulos matemáticos...")
                srt_path.write_text(self._generar_srt(imagenes, duraciones_escenas), encoding="utf-8")

            # --- PASO 4: audio + subtítulos ────────────────────────────
            # Ajustamos PlayResY a la altura real para que el tamaño de letra sea predecible
            play_res_y = h
            
            # Tamaño profesional (en píxeles): 75 para Vertical (7% del ancho), 65 para Horizontal
            f_size = 75 if h > w else 65
            srt_esc = str(srt_path).replace("\\", "/")
            if os.name == "nt":
                srt_esc = srt_esc.replace(":", "\\:")
            
            # Ajustar margen vertical según formato para no tapar el centro
            margin_v = 350 if h > w else 120 

            # Estilo MoneyPrinter: Blanco puro, borde negro grueso, alineado abajo
            sub_style = (
                f"PlayResY={play_res_y},FontName=Arial Black,FontSize={f_size},"
                f"PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
                f"BackColour=&H00000000,Outline=3,Shadow=0,"
                f"BorderStyle=1,Alignment=2,MarginV={margin_v}"
            )

            cmd_final = ["ffmpeg", "-y", "-i", str(video_base)]
            if audio_path and Path(audio_path).exists():
                cmd_final += ["-i", str(audio_path)]
            cmd_final += [
                "-vf", f"subtitles='{srt_esc}':force_style='{sub_style}'",
                "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p"
            ]
            if audio_path and Path(audio_path).exists():
                cmd_final += ["-c:a", "aac"]
            cmd_final.append(str(video_final))

            print("[VIDEO] Aplicando SRT + audio...")
            self._actualizar_progreso(proyecto_id, 99)
            ok, err = await asyncio.to_thread(self._run_ffmpeg, cmd_final)

            # Fallback sin subtítulos si libass no está disponible
            if not ok or not video_final.exists():
                print(f"[VIDEO] subtitles filter falló → sin subtítulos: {err[:100]}")
                cmd_ns = ["ffmpeg", "-y", "-i", str(video_base)]
                if audio_path and Path(audio_path).exists():
                    cmd_ns += ["-i", str(audio_path), "-c:a", "aac"]
                cmd_ns += ["-c:v", "copy", str(video_final)]
                ok, err = await asyncio.to_thread(self._run_ffmpeg, cmd_ns)

            # ── Limpieza ─────────────────────────────────────────────
            for c in clips:
                try: Path(c).unlink(missing_ok=True)
                except: pass
            for tmp in [concat_path, video_base]:
                try: tmp.unlink(missing_ok=True)
                except: pass
            import gc; gc.collect()

            if ok and video_final.exists():
                print(f"[VIDEO] Completado: {video_final}")
                return str(video_final)
            else:
                print(f"[VIDEO] Error final: {err[:200]}"); return None

        except Exception as e:
            print(f"[VIDEO] Excepción en ensamblaje: {e}")
            import traceback; traceback.print_exc()
            return None

    def _generar_srt(self, imagenes: list, duraciones_escenas: list) -> str:
        """SRT con timing proporcional a caracteres — sincronizado con el audio"""
        lines = []
        idx = 1
        # Menos palabras por línea en vertical para no salir, más palabras en horizontal para más tiempo en pantalla
        proj_obj = self._cargar_proyecto(str(Path(imagenes[0][0]).parent.parent.name)) if imagenes else None
        chars_por_linea = 36 if (proj_obj and "9:16" in str(proj_obj.tema)) else 70
        scene_start = 0.0

        for i, (_, texto) in enumerate(imagenes):
            texto = (texto or "").strip()
            dur_escena = duraciones_escenas[i]
            
            if not texto: 
                scene_start += dur_escena
                continue

            # Trocear en líneas de max 36 chars
            words = texto.split()
            chunks, cur, cur_len = [], [], 0
            for word in words:
                if cur_len + len(word) + 1 > chars_por_linea and cur:
                    chunks.append(" ".join(cur)); cur, cur_len = [word], len(word)
                else:
                    cur.append(word); cur_len += len(word) + 1
            if cur: chunks.append(" ".join(cur))
            if not chunks: continue

            total_chars = sum(len(c) for c in chunks) or 1
            t = scene_start
            for chunk in chunks:
                dur_chunk = dur_escena * (len(chunk) / total_chars)
                t_end = t + dur_chunk
                lines += [str(idx), f"{self._fmt_srt(t)} --> {self._fmt_srt(t_end)}", chunk, ""]
                idx += 1
                t += dur_chunk
            
            scene_start += dur_escena

        return "\n".join(lines)

    def _fmt_srt(self, s: float) -> str:
        s = max(0.0, s)
        h = int(s // 3600); m = int((s % 3600) // 60)
        sec = int(s % 60); ms = int(round((s - int(s)) * 1000))
        return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"

    async def _generar_srt_con_whisper(self, audio_path: str, srt_path: str) -> bool:
        """Usa Groq Whisper para transcribir el audio y generar un SRT perfecto"""
        try:
            import groq
            from app.config import GROQ_API_KEY
            import os
            
            if not GROQ_API_KEY:
                print("[WHISPER] No hay GROQ_API_KEY, usando fallback matemático.")
                return False
                
            client = groq.AsyncGroq(api_key=GROQ_API_KEY)
            
            with open(audio_path, "rb") as file:
                transcription = await client.audio.transcriptions.create(
                    file=(os.path.basename(audio_path), file.read()),
                    model="whisper-large-v3",
                    response_format="verbose_json",
                    language="es"
                )
            
            lines = []
            # Whisper devuelve los segments con 'start', 'end' y 'text'
            for i, segment in enumerate(transcription.segments, 1):
                start = self._fmt_srt(segment["start"])
                end = self._fmt_srt(segment["end"])
                text = segment["text"].strip()
                if text:
                    lines.extend([str(i), f"{start} --> {end}", text, ""])
                    
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
                
            print("[WHISPER] Subtítulos generados con éxito!")
            return True
        except Exception as e:
            print(f"[WHISPER] Error generando SRT: {e}")
            return False



    async def _verificar_ffmpeg(self) -> Optional[str]:
        try:
            proc = await asyncio.create_subprocess_exec(
                "ffmpeg", "-version",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            if proc.returncode == 0:
                return "ffmpeg"
        except FileNotFoundError:
            pass

        for ruta in [r"C:\ffmpeg\bin\ffmpeg.exe", r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"]:
            if Path(ruta).exists():
                return ruta
        return None

    def _get_resolucion_from_tema(self, tema: str) -> tuple:
        """Determina la resolución base (W, H) a partir del tema/formato."""
        tema_low = tema.lower()
        if "9:16" in tema_low or "vertical" in tema_low or "short" in tema_low or "tiktok" in tema_low:
            return 1080, 1920
        # Default 16:9
        return 1920, 1080

    # ================================================================
    # UTILIDADES
    # ================================================================
    def _obtener_duracion(self, ruta_video: str) -> float:
        """Obtener duración real usando ffprobe o ffmpeg"""
        import subprocess
        try:
            # 1. ffprobe
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", ruta_video],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return round(float(data.get("format", {}).get("duration", 0)), 2)
        except Exception:
            pass

        try:
            # 2. ffmpeg fallback
            result = subprocess.run(["ffmpeg", "-i", ruta_video], capture_output=True, text=True, timeout=10)
            import re
            m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", result.stderr)
            if m:
                return int(m.group(1))*3600 + int(m.group(2))*60 + float(m.group(3))
        except: pass
        return 0.0

        # Fallback: ruta directa
        try:
            for p in [r"C:\ffmpeg\bin\ffprobe.exe", "ffprobe"]:
                if Path(p).exists() or p == "ffprobe":
                    result = subprocess.run(
                        [p, "-v", "quiet", "-print_format", "json",
                         "-show_format", ruta_video],
                        capture_output=True, text=True, timeout=10
                    )
                    if result.returncode == 0:
                        data = json.loads(result.stdout)
                        return round(float(data.get("format", {}).get("duration", 0)), 2)
        except Exception:
            pass
        return 0.0

    def _obtener_duracion_audio(self, ruta_audio: str) -> float:
        """Obtener duración del audio usando Triple Sensor (ffprobe, ffmpeg y matemática robusta)"""
        import subprocess
        # 1. Sensor Maestro: ffprobe
        for p in ["ffprobe", r"C:\ffmpeg\bin\ffprobe.exe"]:
            try:
                result = subprocess.run(
                    [p, "-v", "error", "-show_entries", "format=duration", 
                     "-of", "default=noprint_wrappers=1:nokey=1", ruta_audio],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0 and result.stdout.strip():
                    return round(float(result.stdout.strip()), 2)
            except Exception:
                continue
        
        # 2. Sensor de Respaldo: ffmpeg "listener"
        try:
            result = subprocess.run(["ffmpeg", "-i", ruta_audio], capture_output=True, text=True, timeout=10)
            import re
            match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", result.stderr)
            if match:
                h, m, s = match.groups()
                dur = int(h)*3600 + int(m)*60 + float(s)
                if dur > 0: return round(dur, 2)
        except Exception:
            pass
                
        # 3. Sensor de Emergencia: Matemática de bytes (Asumimos 64kbps que es común en TTS)
        print("[AUDIO] Sensores fallaron. Usando matemática de 64kbps.")
        try:
            # 64 kbps = 8000 bytes por segundo
            size_bytes = Path(ruta_audio).stat().st_size
            dur = size_bytes / 8000.0
            if dur > 0: return round(dur, 2)
        except Exception:
            pass
            
        return 30.0

    async def _traducir_prompt(self, prompt: str) -> str:
        """Traduce un prompt a inglés para el modelo de imágenes con caché expirable"""
        if not prompt or prompt.strip() == "":
            return ""

        # Buscar en caché
        now = int(time.time())
        entry = self.translation_cache.get(prompt)
        if entry and now - entry.get("timestamp", 0) < self.translation_ttl:
            print(f"[TRAD] Usando caché para: {prompt[:30]}...")
            return entry.get("translated", prompt)

        # Intentar traducción
        print(f"[TRAD] Traduciendo: {prompt[:30]}...")
        translated = prompt
        try:
            # 1. Google Translate
            client_tr = translate.Client()
            result = client_tr.translate(prompt, target_language="en")
            translated = result["translatedText"]
            print("[TRAD] Google Translate OK")
        except Exception as e:
            print(f"[TRAD] Google Translate falló: {e}. Usando fallback Groq.")
            try:
                # 2. Fallback Groq
                from app.config import GROQ_API_KEY
                if GROQ_API_KEY:
                    import groq
                    client_g = groq.AsyncGroq(api_key=GROQ_API_KEY)
                    resp = await client_g.chat.completions.create(
                        model=GROQ_MODEL,
                        messages=[
                            {"role": "system", "content": "Translate the following Spanish text to English. Output only the translated text, no comments."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.0
                    )
                    translated = resp.choices[0].message.content.strip()
                    print("[TRAD] Fallback Groq OK")
            except Exception as e2:
                print(f"[TRAD] Fallback Groq falló: {e2}")

        # Guardar en caché
        self.translation_cache[prompt] = {
            "translated": translated,
            "timestamp": now
        }
        self._guardar_cache()
        return translated

    async def _optimizar_prompt_imagen(self, prompt_visual: str) -> str:
        """Usa Groq para traducir y dar estilo cinematográfico al prompt (con timeout estricto)"""
        try:
            from app.config import GROQ_API_KEY
            if not GROQ_API_KEY: return prompt_visual
            
            import groq
            client_groq = groq.AsyncGroq(api_key=GROQ_API_KEY, timeout=10.0)
            
            sys_msg = (
                "You are a professional cinematic prompt engineer. "
                "Translate to English and expand with technical keywords (Flux/Stable Diffusion). "
                "Style: Cinematic, 8k, hyper-realistic, high resolution. "
                "Output ONLY the optimized prompt in English."
            )
            
            resp = await asyncio.wait_for(
                client_groq.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": prompt_visual}],
                    temperature=0.7, max_tokens=100
                ),
                timeout=12.0
            )
            optimized = resp.choices[0].message.content.strip()
            optimized = optimized.replace('"', '').replace('\n', ' ').strip()
            return optimized
        except Exception as e:
            print(f"[IMAGENES] Salto de optimización por lentitud/error: {e}")
            return prompt_visual.replace("\n", " ").strip()

    def _formatear_tamano(self, bytes: int) -> str:
        if bytes < 1024:
            return f"{bytes} B"
        elif bytes < 1024 * 1024:
            return f"{bytes / 1024:.1f} KB"
        elif bytes < 1024 * 1024 * 1024:
            return f"{bytes / (1024 * 1024):.1f} MB"
        return f"{bytes / (1024 * 1024 * 1024):.2f} GB"

    # ================================================================
    # GESTIÓN DE PROYECTOS
    # ================================================================
    def listar_proyectos(self) -> list:
        proyectos = []
        for json_path in sorted(self.videos_dir.glob("proyecto_*.json"), reverse=True):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # NO mostrar proyectos eliminados
                if data.get("estado") == "eliminado":
                    continue
                if data.get("archivo_final"):
                    video_path = self.videos_dir / data["archivo_final"]
                    data["archivo_existe"] = video_path.exists()
                proyectos.append(data)
            except Exception as e:
                print(f"[VIDEO] Error leyendo {json_path}: {e}")
        return proyectos

    def obtener_proyecto(self, proyecto_id: str) -> Optional[dict]:
        p = self._cargar_proyecto(proyecto_id)
        return p.__dict__ if p else None

    def eliminar_proyecto(self, proyecto_id: str) -> bool:
        p = self._cargar_proyecto(proyecto_id)
        if not p:
            return False
        work_dir = self._get_proyecto_dir(proyecto_id)
        try:
            import shutil
            # Eliminar carpeta de trabajo
            if work_dir.exists():
                shutil.rmtree(work_dir)
            # Eliminar video final si existe
            if p.archivo_final:
                video_path = self.videos_dir / p.archivo_final
                if video_path.exists():
                    video_path.unlink()
            # Eliminar el archivo JSON del proyecto también
            json_path = self.videos_dir / f"{proyecto_id}.json"
            if json_path.exists():
                json_path.unlink()
            return True
        except Exception as e:
            print(f"[VIDEO] Error eliminando: {e}")
            return False

    def generar_idm_link(self, proyecto_id: str, base_url: str = "http://localhost:5000") -> Optional[str]:
        p = self._cargar_proyecto(proyecto_id)
        if not p or not p.archivo_final:
            return None
        return f"{base_url}/api/video/descargar/{p.archivo_final}"

    def generar_script_idm(self, proyecto_id: str, base_url: str = "http://localhost:5000") -> Optional[str]:
        p = self._cargar_proyecto(proyecto_id)
        if not p or not p.archivo_final:
            return None
        url = f"{base_url}/api/video/descargar/{p.archivo_final}"
        script = f"""@echo off
echo Descargando video con Internet Download Manager...
set IDM_PATH="C:\\Program Files (x86)\\Internet Download Manager\\IDMan.exe"
if exist %IDM_PATH% (
    %IDM_PATH% /d "{url}" /p "%USERPROFILE%\\Downloads" /f "{p.archivo_final}" /a
    echo ¡Descarga iniciada en IDM!
) else (
    echo IDM no encontrado. Abre: {url}
)
pause
"""
        script_path = self.videos_dir / f"descargar_{proyecto_id}.bat"
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script)
        return str(script_path)


# Instancia global
generador_video = GeneradorVideo()
