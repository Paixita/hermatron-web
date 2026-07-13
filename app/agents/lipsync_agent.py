"""
🎤 LipSync Agent — 100% Gratuito vía Hugging Face Spaces
Sincronización labial de personajes usando modelos open-source:
  - SadTalker (imagen → video con cara hablando)
  - MuseTalk (video + audio → labios sincronizados)
  - Wav2Lip (imagen + audio → labios sincronizados, clásico)

Todos son GRATIS usando gradio_client apuntando a Hugging Face Spaces.
No requieren GPU local ni dinero.
"""
import asyncio
import os
import time
from pathlib import Path
from typing import Optional


# ── Spaces disponibles con fallback automático ────────────────────────────────
# SadTalker: Convierte imagen estática en video con cara hablando (ideal para personajes)
SADTALKER_SPACES = [
    "vinthony/SadTalker",           # Space oficial del autor
    "fffiloni/SadTalker",           # Mirror alternativo
    "KwaiVGI/SadTalker",            # Mirror alternativo
]

# MuseTalk: Sincronización labial de alta calidad en video
MUSETALK_SPACES = [
    "TMElyralab/MuseTalk",
    "fffiloni/musetalk",
]

# Wav2Lip: Clásico open-source, más ligero y rápido
WAV2LIP_SPACES = [
    "AshDavid12/wav2lip",
    "camenduru/wav2lip",
]


class LipSyncAgent:
    """
    Agente de Sincronización Labial (Lip-Sync) 100% gratuito.

    Flujo de trabajo:
    1. Recibe: imagen del personaje + audio TTS de su voz
    2. Llama a SadTalker/MuseTalk/Wav2Lip vía Hugging Face Spaces (gratis)
    3. Devuelve: clip de video con el personaje hablando con labios sincronizados

    Prioridad de modelos:
    SadTalker → MuseTalk → Wav2Lip → Fallback (imagen estática sin lip-sync)
    """

    TIMEOUT_SEGUNDOS = 120  # SadTalker puede tardar hasta 2 min por clip

    def __init__(self):
        self._gradio_disponible = self._verificar_gradio()

    def _verificar_gradio(self) -> bool:
        try:
            from gradio_client import Client
            return True
        except ImportError:
            print("[LIPSYNC] ⚠️ gradio_client no instalado. Instalar con: pip install gradio_client")
            return False

    async def generar_lip_sync(
        self,
        imagen_path: str,
        audio_path: str,
        salida_path: str,
        personaje: str = "personaje"
    ) -> bool:
        """
        Genera un clip de video con labios sincronizados usando Hugging Face Spaces (GRATIS).

        Args:
            imagen_path: Ruta a la imagen del personaje (jpg/png)
            audio_path:  Ruta al audio TTS generado por Edge-TTS (mp3/wav)
            salida_path: Ruta donde guardar el clip resultante (mp4)
            personaje:   Nombre del personaje (solo para logs)

        Returns:
            True si se generó exitosamente, False si falló todo.
        """
        if not self._gradio_disponible:
            print(f"[LIPSYNC] ❌ gradio_client no disponible para {personaje}")
            return False

        if not Path(imagen_path).exists():
            print(f"[LIPSYNC] ❌ Imagen no encontrada: {imagen_path}")
            return False

        if not Path(audio_path).exists():
            print(f"[LIPSYNC] ❌ Audio no encontrado: {audio_path}")
            return False

        print(f"[LIPSYNC] 🎤 Iniciando lip-sync para {personaje}...")

        # Intentar SadTalker primero (mejor para imágenes → video hablando)
        resultado = await asyncio.to_thread(
            self._intentar_sadtalker, imagen_path, audio_path, salida_path, personaje
        )
        if resultado:
            print(f"[LIPSYNC] ✅ SadTalker funcionó para {personaje}")
            return True

        # Fallback a Wav2Lip (más simple y rápido)
        print(f"[LIPSYNC] 🔄 SadTalker falló, intentando Wav2Lip para {personaje}...")
        resultado = await asyncio.to_thread(
            self._intentar_wav2lip, imagen_path, audio_path, salida_path, personaje
        )
        if resultado:
            print(f"[LIPSYNC] ✅ Wav2Lip funcionó para {personaje}")
            return True

        print(f"[LIPSYNC] ⚠️ Todos los modelos de lip-sync fallaron para {personaje}. "
              f"Se usará imagen estática.")
        return False

    def _intentar_sadtalker(
        self, imagen_path: str, audio_path: str, salida_path: str, personaje: str
    ) -> bool:
        """
        Intenta generar lip-sync con SadTalker vía Hugging Face Spaces.
        SadTalker convierte imagen estática + audio → video con cara animada.
        """
        from gradio_client import Client, handle_file

        for space_id in SADTALKER_SPACES:
            try:
                print(f"[LIPSYNC] Conectando a {space_id}...")
                client = Client(space_id, verbose=False)

                # Parámetros de SadTalker
                resultado = client.predict(
                    source_image=handle_file(imagen_path),
                    driven_audio=handle_file(audio_path),
                    preprocess_type="crop",          # crop, resize, full
                    is_still_mode=False,             # False = más movimiento natural
                    enhancer=True,                   # GFPGAN para mejorar calidad facial
                    batch_size=2,
                    size_of_image=256,
                    pose_style=0,
                    facerender="facevid2vid",        # Mejor calidad
                    exp_scale=1.0,
                    use_ref_video=False,
                    ref_video=None,
                    ref_info="pose",
                    use_idle_mode=False,
                    length_of_video=90,
                    blink_every=True,
                    fps=30,
                    api_name="/test"
                )

                # resultado puede ser ruta al video o dict con la ruta
                video_resultado = resultado
                if isinstance(resultado, dict):
                    video_resultado = resultado.get("video", resultado.get("output", None))
                if isinstance(resultado, (list, tuple)):
                    video_resultado = resultado[0]

                if video_resultado and Path(str(video_resultado)).exists():
                    # Copiar/mover al destino
                    import shutil
                    shutil.copy2(str(video_resultado), salida_path)
                    print(f"[LIPSYNC] ✅ SadTalker ({space_id}) → {salida_path}")
                    return True

            except Exception as e:
                print(f"[LIPSYNC] ⚠️ {space_id} falló: {type(e).__name__}: {str(e)[:100]}")
                continue

        return False

    def _intentar_wav2lip(
        self, imagen_path: str, audio_path: str, salida_path: str, personaje: str
    ) -> bool:
        """
        Intenta generar lip-sync con Wav2Lip vía Hugging Face Spaces.
        Wav2Lip es más rápido y ligero, bueno para animaciones de personajes.
        """
        from gradio_client import Client, handle_file

        for space_id in WAV2LIP_SPACES:
            try:
                print(f"[LIPSYNC] Conectando a Wav2Lip: {space_id}...")
                client = Client(space_id, verbose=False)

                resultado = client.predict(
                    face=handle_file(imagen_path),
                    audio=handle_file(audio_path),
                    api_name="/predict"
                )

                video_resultado = resultado
                if isinstance(resultado, (list, tuple)):
                    video_resultado = resultado[0]

                if video_resultado and Path(str(video_resultado)).exists():
                    import shutil
                    shutil.copy2(str(video_resultado), salida_path)
                    print(f"[LIPSYNC] ✅ Wav2Lip ({space_id}) → {salida_path}")
                    return True

            except Exception as e:
                print(f"[LIPSYNC] ⚠️ Wav2Lip {space_id} falló: {str(e)[:100]}")
                continue

        return False

    async def procesar_escenas_con_lipsync(
        self,
        escenas: list[dict],
        work_dir: Path
    ) -> list[dict]:
        """
        Procesa todas las escenas del proyecto aplicando lip-sync a las que
        tienen imagen de personaje y audio TTS disponibles.

        Modifica la escena para que use el clip con lip-sync en lugar de la imagen.
        """
        if not self._gradio_disponible:
            print("[LIPSYNC] ⚠️ gradio_client no disponible — saltando lip-sync")
            return escenas

        escenas_procesadas = []
        for i, escena in enumerate(escenas):
            escena_copia = dict(escena)
            num_escena = escena_copia.get("numero", i + 1)

            # Buscar imagen y audio de la escena
            escena_dir = work_dir / f"escena_{num_escena:02d}"
            img_path = str(escena_dir / "imagen.png")
            if not Path(img_path).exists():
                img_path = str(escena_dir / "imagen.jpg")

            audio_path = str(escena_dir / "audio_escena.mp3")
            if not Path(audio_path).exists():
                audio_path = str(escena_dir / "audio_escena.wav")

            lipsync_path = str(escena_dir / "lipsync.mp4")

            if Path(img_path).exists() and Path(audio_path).exists():
                personajes = escena_copia.get("personajes_en_escena", ["personaje"])
                nombre = personajes[0] if personajes else "personaje"

                print(f"[LIPSYNC] 🎬 Escena {num_escena}: aplicando lip-sync a {nombre}...")
                exito = await self.generar_lip_sync(img_path, audio_path, lipsync_path, nombre)

                if exito and Path(lipsync_path).exists():
                    # Marcar la escena para que el Assembly use el clip con lip-sync
                    escena_copia["lipsync_path"] = lipsync_path
                    escena_copia["tiene_lipsync"] = True
                    print(f"[LIPSYNC] ✅ Escena {num_escena}: lip-sync listo")
                else:
                    escena_copia["tiene_lipsync"] = False
            else:
                escena_copia["tiene_lipsync"] = False

            escenas_procesadas.append(escena_copia)

        total_lipsync = sum(1 for e in escenas_procesadas if e.get("tiene_lipsync"))
        print(f"[LIPSYNC] 🎤 {total_lipsync}/{len(escenas_procesadas)} escenas con lip-sync")
        return escenas_procesadas


# Instancia global del agente
lipsync_agent = LipSyncAgent()
