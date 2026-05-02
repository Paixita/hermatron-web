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

from app.config import BASE_DIR, PEXELS_API_KEY, ELEVENLABS_API_KEY, UNSPLASH_ACCESS_KEY


# --- DIRECTORIO DE VIDEOS ---
VIDEOS_DIR = BASE_DIR / "videos"
VIDEOS_DIR.mkdir(exist_ok=True)

THUMBNAILS_DIR = VIDEOS_DIR / "thumbnails"
THUMBNAILS_DIR.mkdir(exist_ok=True)

# --- ESTADO DE VIDEO ---
class VideoEstado(str, Enum):
    ANALIZANDO = "analizando"
    DISENANDO = "disenando"
    EN_REVIEW = "en_review"
    APROBADO = "aprobado"
    GENERANDO_IMAGENES = "generando_imagenes"
    GENERANDO_VEZ = "generando_voz"
    ENSAMBLANDO = "ensamblando"
    COMPLETADO = "completado"
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
        self._progreso[proyecto_id] = max(0, min(100, progreso))

    def obtener_progreso(self, proyecto_id: str) -> int:
        return self._progreso.get(proyecto_id, 0)

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

        proyecto = VideoProyecto(
            id=proyecto_id,
            tema=tema,
            prompt=prompt,
            estado=VideoEstado.ANALIZANDO,
            creado_en=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        self._guardar_proyecto(proyecto)
        self._proyectos[proyecto_id] = proyecto
        self._actualizar_progreso(proyecto_id, 10)

        # Analizar tema con Groq
        analisis = await self._analizar_con_ia(proyecto_id, tema, prompt, groq_client)
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
Eres un DIRECTOR DE CINE creando un video para YouTube.

CONTEXTO DEL VIDEO:
- Tono: {tono}
- Estilo visual: {estilo}
- Atmósfera: {atmosfera}

Tu trabajo:
1. Crear un GUIÓN COHERENTE con narración poderosa
2. DISEÑAR CADA ESCENA con visión cinematográfica completa

Para cada escena debes definir:
- texto_narracion: Lo que dice el narrador (poderoso, conciso)
- descripcion_visual: Qué se ve en pantalla (detallado, cinematográfico)
- angulo_camara: Plano general, primer plano, picado, contrapicado, etc.
- iluminacion: Dramática, natural, contraluz, dorada, etc.
- paleta_colores: Fría, cálida, neutra, alto contraste, etc.
- movimiento: Estático, paneo, zoom, travelling, etc.
- emocion: Qué debe transmitir (tensión, asombro, curiosidad, etc.)
- query_pexels: Búsqueda en inglés para Pexels (máx 5 palabras)

REGLAS CRÍTICAS:
- CADA ESCENA debe tener un 'texto_narracion' de al menos 20 palabras. NO lo dejes vacío.
- CADA ESCENA debe ser COHERENTE con las demás (misma línea visual)
- La escena 1 debe tener un HOOK visual impactante
- Las transiciones entre escenas deben ser fluidas
- Incluye una escena final con CTA poderoso

Responde SOLO con JSON válido, sin markdown ni texto extra:
{{
    "guion_completo": "texto completo del guión narrativo",
    "escenas": [
        {{
            "numero": 1,
            "titulo": "Apertura impactante",
            "texto_narracion": "Escribe aquí al menos 20 palabras de narración profesional...",
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
                max_tokens=4096,
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

Crea una versión MEJOR y DIFERENTE manteniendo coherencia con:
- Tema: {proyecto.tema}
- Tono: {proyecto.analisis.get('tono_general', '')}
- Estilo: {proyecto.analisis.get('estilo_visual', '')}

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
            self._guardar_proyecto(proyecto)
            
        work_dir = self._get_proyecto_dir(proyecto_id)
        
        # Pasamos solo esta escena al generador visual
        await self._generar_escenas_visuales(proyecto_id, [escena_obj], work_dir)
        
        proyecto = self._cargar_proyecto(proyecto_id)
        for e in proyecto.escenas_disenadas:
            if e["numero"] == escena_num:
                return e.get("imagen_path")
        return ""

    async def ensamblar_video_final(self, proyecto_id: str, generar_voz_func=None) -> str:
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
            proyecto_id, work_dir, proyecto.audio_path, escenas_aprobadas
        )
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

    # ================================================================
    # FASE 5: Generar Imágenes
    # ================================================================
    async def _generar_escenas_visuales(self, proyecto_id: str, escenas: list, work_dir: Path):
        total = len(escenas)
        fuente_usada = "placeholder"
        
        proyecto = self._cargar_proyecto(proyecto_id)
        estilo_visual = proyecto.analisis.get("estilo_visual", "") if (proyecto and hasattr(proyecto, 'analisis') and proyecto.analisis) else "cinematic"

        for i, escena in enumerate(escenas):
            num_escena = escena.get("numero", i+1)
            print(f"[VIDEO] Procesando visuales para escena {num_escena} de {total}...")
            escena_dir = work_dir / f"escena_{num_escena}"
            escena_dir.mkdir(exist_ok=True)
            img_path = escena_dir / "imagen.png"

            # Construir un prompt robusto para Pollinations usando la descripción visual completa
            descripcion = escena.get("descripcion_visual", "")
            query = escena.get("query_pexels", "")
            
            # Nueva Generación con IA (Pollinations.ai)
            query_mejorado = f"{descripcion}, {query}, {estilo_visual}, highly detailed, masterpiece, 8k resolution, cinematic lighting"
            print(f"[VIDEO]  Generando con IA (Pollinations): {query_mejorado}")
            
            exito = await self._generar_imagen_pollinations(query_mejorado, str(img_path))
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

    async def _generar_imagen_pollinations(self, query: str, ruta_salida: str) -> bool:
        """Generar imagen usando Pollinations.ai con reintentos y sanitización"""
        import httpx
        import urllib.parse
        import random

        # Sanitizar query: Limitar longitud y caracteres especiales
        query_limpio = query[:250].replace("\n", " ").replace('"', "").strip()
        query_codificado = urllib.parse.quote(query_limpio)
        
        # MEJORAS: Mayor resolución y mejor calidad
        # Opciones: 1920x1080 (HD), 2560x1440 (2K), 3840x2160 (4K)
        resolution = os.getenv("IMAGEN_RESOLUTION", "2560x1440")  # Default 2K
        width, height = map(int, resolution.split('x'))
        
        # Seeds múltiples para variedad + mejores prompts
        seed = random.randint(1, 99999)
        
        # URL con opciones de máxima calidad:
        # - width/height: resolución
        # - nologo: sin logo de Watermark
        # - seed: para reproducibilidad
        # - enhance: mejora el prompt internamente
        # - private: no publicly visible
        url = f"https://image.pollinations.ai/prompt/{query_codificado}?width={width}&height={height}&nologo=true&seed={seed}&enhance=true&private=true&model=flux"
        
        print(f"[POLLINATIONS] Generando en {resolution} - {query_limpio[:50]}...")
        
        intentos = 3
        for i in range(intentos):
            try:
                print(f"[POLLINATIONS] Intento {i+1}/3...")
                async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                    response = await client.get(url)
                    
                    if response.status_code == 200 and len(response.content) > 20000:
                        with open(ruta_salida, "wb") as f:
                            f.write(response.content)
                        size_kb = len(response.content) / 1024
                        print(f"[POLLINATIONS] ✅ Éxito: {size_kb:.0f} KB ({width}x{height})")
                        return True
                    
                    print(f"[POLLINATIONS] ⚠️ Respuesta inválida ({response.status_code}), reintentando...")
            except Exception as e:
                print(f"[POLLINATIONS] ❌ Error intento {i+1}: {e}")
            
            if i < intentos - 1:
                await asyncio.sleep(2 * (i + 1)) # Espera incremental

        # Fallback to Unsplash (lightweight free images)
        print("[UNSPLASH] Intentando fallback con Unsplash Source")
        success = await self._generar_imagen_unsplash(query_limpio, ruta_salida, use_source=True)
        if success:
            print("[UNSPLASH] ✅ Imagen obtenida de Unsplash Source")
            return True
        # If API key is provided, try official Unsplash API
        if UNSPLASH_ACCESS_KEY:
            print("[UNSPLASH] Intentando fallback con API oficial")
            success = await self._generar_imagen_unsplash(query_limpio, ruta_salida)
            if success:
                print("[UNSPLASH] ✅ Imagen obtenida de Unsplash API")
                return True
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
        """Generar placeholder CINEMATOGRÁFICO VISIBLE (colores brillantes)"""
        try:
            from PIL import Image, ImageDraw, ImageFont, ImageFilter
            import random
            random.seed(indice + total)  # Reproducible por escena

            width, height = 1920, 1080
            img = Image.new('RGB', (width, height))
            draw = ImageDraw.Draw(img)

            # Paletas cinematográficas BRILLANTES
            paletas = [
                # Aurora Boreal
                ((10, 60, 120), (0, 180, 160), (120, 40, 180)),
                # Atardecer épico
                ((200, 80, 30), (255, 160, 50), (80, 20, 80)),
                # Océano profundo
                ((0, 80, 160), (0, 180, 220), (0, 40, 100)),
                # Bosque mágico
                ((20, 80, 40), (60, 180, 80), (180, 140, 40)),
                # Galaxia
                ((40, 10, 80), (100, 30, 150), (180, 60, 120)),
                # Fuego dramático
                ((180, 30, 10), (255, 120, 20), (80, 10, 40)),
            ]

            idx = indice % len(paletas)
            colores = paletas[idx]

            # Gradiente multi-color con ondas
            for y in range(height):
                for x in range(width):
                    # Posición normalizada
                    px = x / width
                    py = y / height

                    # Mezcla de colores con ondas
                    onda1 = 0.5 + 0.5 * __import__('math').sin(px * 3.14159 * 4 + indice)
                    onda2 = 0.5 + 0.5 * __import__('math').cos(py * 3.14159 * 3 + indice * 2)

                    t1 = onda1
                    t2 = onda2 * (1 - t1)

                    r = int(colores[0][0] * (1 - t1 - t2) + colores[1][0] * t1 + colores[2][0] * t2)
                    g = int(colores[0][1] * (1 - t1 - t2) + colores[1][1] * t1 + colores[2][1] * t2)
                    b = int(colores[0][2] * (1 - t1 - t2) + colores[1][2] * t1 + colores[2][2] * t2)

                    # Asegurar rango válido
                    r = max(0, min(255, r))
                    g = max(0, min(255, g))
                    b = max(0, min(255, b))

                    img.putpixel((x, y), (r, g, b))

            # Efecto de luz/viñeta cinematográfica
            # Viñeta oscura en bordes
            for y in range(height):
                for x in range(width):
                    cx = (x / width - 0.5) * 2
                    cy = (y / height - 0.5) * 2
                    dist = __import__('math').sqrt(cx * cx + cy * cy)
                    vignette = max(0, 1 - dist * 0.7)

                    r, g, b = img.getpixel((x, y))
                    r = int(r * vignette)
                    g = int(g * vignette)
                    b = int(b * vignette)
                    img.putpixel((x, y), (r, g, b))

            # Desenfoque sutil para efecto cinematográfico
            img = img.filter(ImageFilter.GaussianBlur(radius=2))

            # Agregar texto
            try:
                font = ImageFont.truetype("arial.ttf", 48)
                font_small = ImageFont.truetype("arial.ttf", 28)
            except:
                font = ImageFont.load_default()
                font_small = font

            text = f"Escena {indice + 1}"
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]

            # Fondo semi-transparente
            overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            overlay_draw.rounded_rectangle(
                [(width//2 - 250, height//2 - 60), (width//2 + 250, height//2 + 100)],
                radius=20, fill=(0, 0, 0, 150)
            )
            img.paste(Image.alpha_composite(Image.new('RGBA', img.size, (0,0,0)), overlay).convert('RGB'))

            draw = ImageDraw.Draw(img)
            draw.text(((width - text_w) // 2, height // 2 - 40), text, fill="white", font=font)

            desc = descripcion[:70] + "..." if len(descripcion) > 70 else descripcion
            if query:
                desc += f"\n[{query}]"
            bbox2 = draw.textbbox((0, 0), desc, font=font_small)
            desc_w = bbox2[2] - bbox2[0]
            draw.text(((width - desc_w) // 2, height // 2 + 20), desc, fill=(220, 220, 220), font=font_small)

            # Guardar como JPEG mejor calidad
            if ruta_salida.endswith('.png'):
                ruta_salida = ruta_salida[:-4] + '.jpg'
            img.save(ruta_salida, "JPEG", quality=92)

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

        # Extraer textos de narración del guión
        textos = []
        for linea in guion.split("\n"):
            if "TEXTO:" in linea or "texto_narracion" in linea:
                texto = linea.split(":", 1)[-1].strip().strip('"').strip("'")
                if texto:
                    textos.append(texto)

        texto_completo = " ".join(textos) if textos else guion[:500]

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
            await asyncio.wait_for(communicate.save(str(audio_path)), timeout=40.0)
            print(f"[AUDIO]  edge-tts OK")
            return str(audio_path)
        except Exception as e:
            print(f"[AUDIO] Error edge-tts: {e}")

        # Intento 3: gTTS (Nube / Bulletproof)
        try:
            import gtts
            print(f"[AUDIO] Generando con gTTS (respaldo)...")
            tts = gtts.gTTS(text=texto_completo, lang='es', tld='com.mx')
            tts.save(str(audio_path))
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
            engine.save_to_file(texto_completo, str(audio_path))
            engine.runAndWait()
            engine.stop()
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
        """Ejecutar FFmpeg con subprocess.run y retornar (success, stderr)"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return result.returncode == 0, result.stderr
        except subprocess.TimeoutExpired:
            return False, "Timeout FFmpeg"
        except Exception as e:
            return False, str(e)

    async def _ensamblar_video(self, proyecto_id: str, work_dir: Path,
                                audio_path: Optional[str], escenas: list) -> Optional[str]:
        """Ensamblar video con MoviePy (Efecto Ken Burns, Crossfades y Audio)"""
        video_final = self.videos_dir / f"{proyecto_id}.mp4"
        
        imagenes = []
        for i, escena in enumerate(escenas):
            num_escena = escena.get("numero", i+1)
            img = work_dir / f"escena_{num_escena}" / "imagen.jpg"
            if not img.exists():
                img = work_dir / f"escena_{num_escena}" / "imagen.png"
            if img.exists():
                imagenes.append(str(img))

        if not imagenes:
            print("[VIDEO]  Sin imágenes")
            return None

        print(f"[VIDEO]  MoviePy: Ensamblando {len(imagenes)} imágenes")

        try:
            # Monkey-patch para Pillow 10+ (MoviePy 1.0.3 usa ANTIALIAS que fue eliminado)
            import PIL.Image
            if not hasattr(PIL.Image, 'ANTIALIAS'):
                PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS

            from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip
            import moviepy.video.fx.all as vfx
            
            # Calcular duración por escena
            dur_total = 10.0 # Por defecto
            audio_clip = None
            if audio_path and Path(audio_path).exists():
                audio_clip = AudioFileClip(audio_path)
                dur_total = audio_clip.duration
            
            dur_escena = max(3.0, dur_total / max(len(imagenes), 1))
            
            # Crear clips de imagen con efecto Ken Burns (Zoom Dinámico)
            # Obtener resolución configurada (dinámica)
            resolution = os.getenv("IMAGEN_RESOLUTION", "2560x1440")
            w, h = map(int, resolution.split('x'))
        
            clips = []
            for i, img in enumerate(imagenes):
                # 1. Cargar imagen y establecer duración
                base_clip = ImageClip(img).set_duration(dur_escena + 1.0).resize(width=w, height=h)
                
                # 2. Generar subtítulo para la escena
                texto_escena = escenas[i].get("texto_narracion", "") if i < len(escenas) else ""
                if texto_escena and len(texto_escena) > 3:
                    sub_clip = self._crear_clip_subtitulo(texto_escena, w, h, dur_escena + 1.0, work_dir, i)
                    # Componer el subtítulo sobre la imagen base
                    clip = CompositeVideoClip([base_clip, sub_clip.set_position("center")])
                else:
                    clip = base_clip
            
                # 3. Fade suave entre escenas
                if len(clips) > 0:
                    clip = clip.crossfadein(0.5)
            
                clips.append(clip)
        
            # Concatenar todos los clips usando 'compose' method para crossfades
            video = concatenate_videoclips(clips, padding=-1.0, method="compose")

            # Ajustar duración exacta al audio si existe
            if audio_clip:
                video = video.set_audio(audio_clip)
                video = video.set_duration(audio_clip.duration)
            else:
                video = video.set_duration(dur_total)
            
            # Exportar archivo
            video.write_videofile(
                str(video_final), 
                fps=24, 
                codec='libx264', 
                audio_codec='aac',
                preset='fast',
                threads=4,
                logger=None # Evitar consola saturada
            )
            
            # Liberar memoria de moviepy
            if audio_clip: audio_clip.close()
            video.close()
            for c in clips: c.close()
            
            print(f"[VIDEO]  Video generado exitosamente en {video_final}")
            return str(video_final)

        except Exception as e:
            print(f"[VIDEO]  Error con MoviePy: {e}")
            import traceback
            traceback.print_exc()
            return None


    def _crear_clip_subtitulo(self, texto: str, w: int, h: int, duracion: float, work_dir: Path, idx: int) -> "ImageClip":
        """Crear clip de imagen transparente con texto (evita usar ImageMagick)"""
        from PIL import Image, ImageDraw, ImageFont
        import textwrap
        
        # Imagen transparente
        img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Intentar cargar una fuente bonita, si no, usa la por defecto
        try:
            # Usar una fuente grande
            font_size = int(h * 0.05) # 5% de la pantalla
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()
            font_size = 40
            
        # Dividir texto largo en líneas
        caracteres_por_linea = 40
        lineas = textwrap.wrap(texto, width=caracteres_por_linea)
        
        # Dibujar líneas en la parte inferior (80% de la altura)
        y_start = int(h * 0.80)
        
        for i, linea in enumerate(lineas):
            # Obtener el cuadro delimitador del texto
            bbox = draw.textbbox((0, 0), linea, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            
            x = (w - text_w) // 2
            y = y_start + (i * (text_h + 10))
            
            # Dibujar borde negro para que resalte
            grosor = 3
            for dx in range(-grosor, grosor+1):
                for dy in range(-grosor, grosor+1):
                    draw.text((x+dx, y+dy), linea, font=font, fill=(0,0,0,255))
                    
            # Dibujar texto blanco encima
            draw.text((x, y), linea, font=font, fill=(255,255,255,255))
            
        # Guardar temporal
        temp_path = work_dir / f"sub_{idx}.png"
        img.save(temp_path)
        
        from moviepy.editor import ImageClip
        return ImageClip(str(temp_path)).set_duration(duracion)

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

    # ================================================================
    # UTILIDADES
    # ================================================================
    def _obtener_duracion(self, ruta_video: str) -> float:
        """Obtener duración real usando ffprobe"""
        import subprocess
        try:
            ffprobe_path = "ffprobe"
            # Probar en PATH primero
            proc = subprocess.run(
                [ffprobe_path, "-v", "quiet", "-print_format", "json",
                 "-show_format", ruta_video],
                capture_output=True, text=True, timeout=10
            )
            if proc.returncode == 0:
                data = json.loads(proc.stdout)
                return round(float(data.get("format", {}).get("duration", 0)), 2)
        except Exception:
            pass

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
        """Obtener duración del audio usando ffprobe"""
        import subprocess
        try:
            for p in ["ffprobe", r"C:\ffmpeg\bin\ffprobe.exe"]:
                if Path(p).exists() or p == "ffprobe":
                    result = subprocess.run(
                        [p, "-v", "quiet", "-print_format", "json",
                         "-show_format", ruta_audio],
                        capture_output=True, text=True, timeout=10
                    )
                    if result.returncode == 0:
                        data = json.loads(result.stdout)
                        return round(float(data.get("format", {}).get("duration", 30)), 2)
        except Exception:
            pass
        return 30.0

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
