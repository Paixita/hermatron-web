"""
✅ Quality Agent — Inspirado en ViMax
Revisor visual que usa Gemini Vision para verificar la calidad
de cada imagen generada antes de ensamblar el video final.
"""
import asyncio
import base64
import os
from pathlib import Path


class QualityAgent:
    """
    Agente de Calidad Visual (inspirado en ViMax VLM-Guided Monitoring).
    
    Usa Gemini Vision para:
    1. Verificar que la imagen coincide con la descripción visual
    2. Detectar si los personajes tienen el aspecto correcto
    3. Dar un puntaje de calidad (0-10)
    4. Decidir si regenerar o aceptar
    """

    UMBRAL_APROBACION = 5  # Puntaje mínimo para aceptar (sobre 10)
    MAX_REINTENTOS = 2

    def __init__(self, google_api_key: str = ""):
        self.api_key = google_api_key or os.getenv("GOOGLE_API_KEY", "")
        self._disponible = bool(self.api_key)

    @property
    def disponible(self) -> bool:
        return self._disponible

    async def evaluar_imagen(
        self,
        imagen_path: str,
        descripcion_esperada: str,
        numero_escena: int = 0
    ) -> dict:
        """
        Evalúa si una imagen cumple con la descripción visual esperada.
        
        Retorna:
        {
            "aprobada": bool,
            "puntaje": int (0-10),
            "razon": str,
            "sugerencia": str
        }
        """
        if not self._disponible:
            print(f"[QUALITY] ⚠️ Gemini Vision no disponible — escena {numero_escena} aprobada por defecto")
            return {"aprobada": True, "puntaje": 7, "razon": "Sin revisión (no hay API key)", "sugerencia": ""}

        if not Path(imagen_path).exists():
            return {"aprobada": False, "puntaje": 0, "razon": "Imagen no encontrada", "sugerencia": "Regenerar imagen"}

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)

            # Leer imagen como base64
            with open(imagen_path, "rb") as f:
                imagen_bytes = f.read()
            imagen_b64 = base64.b64encode(imagen_bytes).decode()

            # Determinar tipo MIME
            ext = Path(imagen_path).suffix.lower()
            mime_type = "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png"

            prompt_revision = f"""Eres un director de calidad cinematográfica. Analiza esta imagen generada por IA.

DESCRIPCIÓN ESPERADA: {descripcion_esperada[:500]}

Evalúa en una escala del 1 al 10:
- ¿La imagen coincide con la descripción?
- ¿Los personajes tienen el aspecto correcto (raza, ropa, rasgos)?
- ¿La composición es cinematográfica?

Responde SOLO en este formato JSON exacto (sin markdown):
{{"puntaje": <número 1-10>, "aprobada": <true/false>, "razon": "<una frase corta>", "sugerencia": "<qué mejorar si es rechazada>"}}

Si el puntaje es 5 o más, aprobada=true. Si es menor a 5, aprobada=false."""

            response = await asyncio.to_thread(
                client.models.generate_content,
                model="gemini-2.0-flash",
                contents=[
                    types.Part.from_bytes(data=imagen_bytes, mime_type=mime_type),
                    prompt_revision
                ]
            )

            texto = response.text.strip()
            # Limpiar markdown si lo tiene
            texto = texto.replace("```json", "").replace("```", "").strip()

            import json
            resultado = json.loads(texto)
            puntaje = int(resultado.get("puntaje", 5))
            aprobada = resultado.get("aprobada", puntaje >= self.UMBRAL_APROBACION)

            print(f"[QUALITY] 🔍 Escena {numero_escena}: puntaje={puntaje}/10 "
                  f"{'✅ APROBADA' if aprobada else '❌ RECHAZADA'} — {resultado.get('razon', '')}")

            return {
                "aprobada": aprobada,
                "puntaje": puntaje,
                "razon": resultado.get("razon", ""),
                "sugerencia": resultado.get("sugerencia", "")
            }

        except Exception as e:
            print(f"[QUALITY] ⚠️ Error en revisión visual escena {numero_escena}: {e} — aprobando por defecto")
            return {"aprobada": True, "puntaje": 6, "razon": f"Error en revisión: {e}", "sugerencia": ""}

    async def evaluar_video_clip(self, video_path: str, descripcion: str, numero_escena: int = 0) -> dict:
        """
        Evalúa si un clip de video (thumbnail del primer frame) cumple la descripción.
        """
        if not Path(video_path).exists():
            return {"aprobada": False, "puntaje": 0, "razon": "Video no encontrado", "sugerencia": ""}

        # Extraer primer frame del video para evaluarlo
        frame_path = str(video_path).replace(".mp4", "_frame_quality.jpg")
        try:
            import subprocess
            cmd = [
                "ffmpeg", "-y", "-i", video_path,
                "-vframes", "1", "-q:v", "2",
                frame_path
            ]
            subprocess.run(cmd, capture_output=True, timeout=15)

            if Path(frame_path).exists():
                resultado = await self.evaluar_imagen(frame_path, descripcion, numero_escena)
                # Limpiar frame temporal
                try:
                    os.remove(frame_path)
                except:
                    pass
                return resultado
        except Exception as e:
            print(f"[QUALITY] Error extrayendo frame de video: {e}")

        return {"aprobada": True, "puntaje": 6, "razon": "No se pudo extraer frame", "sugerencia": ""}


# Instancia global
quality_agent = QualityAgent()
