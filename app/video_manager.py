# app/video_manager.py
"""Módulo central para gestionar la creación y edición de videos en Hermatron.
Utiliza Celery + Redis como cola de tareas para procesar trabajos en background.
Integrado con GeneradorVideo y GeneradorVoz existentes.
"""
import os
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List

# from .celery_app import celery
from .video import generador_video, VideoEstado
from .voz import generador_voz
from .config import GROQ_API_KEY
from groq import Groq

# Cliente Groq para las tareas en background
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

def run_async(coro):
    """Helper para ejecutar corrutinas en un entorno síncrono (Celery worker)."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    if loop.is_running():
        return asyncio.ensure_future(coro)
    return loop.run_until_complete(coro)

def pre_producir_video_task(payload: Dict[str, Any]):
    """Fase 1-5: Analiza, diseña escenas y genera imágenes (Storyboard)."""
    proyecto_id = payload.get("proyecto_id")
    tema = payload.get("tema")
    prompt = payload.get("prompt")
    voz = payload.get("voz", "es-MX-JorgeNeural")
    
    try:
        # 1. Analizar tema
        # self.update_state(state="ANALIZANDO", meta={"progreso": 10})
        run_async(generador_video.analizar_tema(tema, prompt, client, proyecto_id=proyecto_id))
        
        # 2. Diseñar escenas
        # self.update_state(state="DISENANDO", meta={"progreso": 30})
        run_async(generador_video.disenar_escenas(proyecto_id, client))
        
        # Configurar la voz en el proyecto
        proj_obj = generador_video._cargar_proyecto(proyecto_id)
        if proj_obj:
            proj_obj.voz = voz
            generador_video._guardar_proyecto(proj_obj)
        
        # 3. Pre-producir (Generar imágenes)
        # self.update_state(state="GENERANDO_IMAGENES", meta={"progreso": 50})
        run_async(generador_video.pre_producir_video(proyecto_id))
        
        # self.update_state(state="LISTO_PARA_REVISION", meta={"progreso": 100})
        return {"status": "success", "proyecto_id": proyecto_id}
        
    except Exception as e:
        # self.update_state(state="ERROR", meta={"error": str(e)})
        generador_video._actualizar_estado(proyecto_id, VideoEstado.ERROR, str(e))
        raise e

def regenerar_imagen_task(proyecto_id: str, escena_num: int, nuevo_prompt: Optional[str] = None, cantidad: int = 1):
    """Regenera la imagen de una escena específica (permite generar múltiples opciones)."""
    try:
        # self.update_state(state="REGENERANDO_IMAGEN", meta={"progreso": 20})
        opciones = []
        
        proj_obj = generador_video._cargar_proyecto(proyecto_id)
        escena_info = next((e for e in proj_obj.escenas_disenadas if e["numero"] == escena_num), None)
        prompt_visual = nuevo_prompt or (escena_info["descripcion_visual"] if escena_info else "Cinematic scene")
        prompt_final = f"{proj_obj.estilo_visual}. {prompt_visual}"
        
        escena_dir = Path(generador_video._get_proyecto_dir(proyecto_id)) / f"escena_{escena_num}"
        escena_dir.mkdir(parents=True, exist_ok=True)
        
        width, height = generador_video._get_resolucion_from_tema(proj_obj.tema)
        
        import shutil
        for i in range(cantidad):
            # Mover a ruta de alternativa (alt_1, alt_2...)
            alt_path = escena_dir / f"imagen_alt_{i+1}.png"
            # Generar imagen directamente con Pollinations respetando formato
            exito = run_async(generador_video._generar_imagen_pollinations(prompt_final, str(alt_path), width, height))
            
            if not exito:
                run_async(generador_video._generar_imagen_placeholder(str(alt_path), prompt_final))
                
            opciones.append(str(alt_path))
            
        return {"success": True, "opciones": opciones}
    except Exception as e:
        # self.update_state(state="ERROR", meta={"error": str(e)})
        raise e

def ensamblar_video_task(proyecto_id: str, resolucion: str = "1080"):
    """Fase 6-7: Genera voz y ensambla el video final."""
    try:
        # self.update_state(state="ENSAMBLANDO", meta={"progreso": 10})
        video_final = run_async(generador_video.ensamblar_video_final(
            proyecto_id=proyecto_id, 
            generar_voz_func=None, 
            resolucion=resolucion
        ))
        # self.update_state(state="COMPLETO", meta={"progreso": 100})
        return {"status": "success", "video_url": f"/video_files/{Path(video_final).name}"}
    except Exception as e:
        # self.update_state(state="ERROR", meta={"error": str(e)})
        generador_video._actualizar_estado(proyecto_id, VideoEstado.ERROR, str(e))
        raise e
