import subprocess
import os
from typing import List
from pathlib import Path

def crear_clip_imagen(imagen_path: str, duracion: float, width: int, height: int, out_path: str) -> None:
    """
    Crea un clip de video (MP4) a partir de una imagen estática usando FFmpeg.
    """
    cmd = [
        "ffmpeg", "-y", "-loop", "1",
        "-i", imagen_path,
        "-t", f"{duracion:.4f}",
        "-vf", f"scale={width}:{height},format=yuv420p",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20",
        out_path
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
    except subprocess.TimeoutExpired:
        print(f"[FFMPEG] Timeout creando clip para {imagen_path}")
        raise
    except Exception as e:
        print(f"[FFMPEG] Error creando clip: {e}")
        raise

def concatenar_segmentos(segmentos: List[str], output_path: str, audio_path: str = None) -> None:
    """
    Concatena varios clips de video usando el demuxer de FFmpeg.
    Si se proporciona audio_path, lo mezcla con el video.
    """
    if not segmentos:
        return

    # Crear archivo concat.txt
    temp_dir = Path(segmentos[0]).parent
    concat_file = temp_dir / "concat.txt"
    with open(concat_file, "w", encoding="utf-8") as f:
        for seg in segmentos:
            # FFmpeg requiere rutas escapadas o relativas en el archivo concat
            abs_path = os.path.abspath(seg).replace("\\", "/")
            f.write(f"file '{abs_path}'\n")

    try:
        # Comando de concatenación
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_file),
            "-c", "copy",
            output_path
        ]
        # Aumentamos a 1200s (20 min) para concatenar videos largos
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1200)

        # Si hay audio, mezclarlo
        if audio_path and os.path.exists(audio_path):
            temp_video = output_path + ".tmp.mp4"
            
            # Reintento para rename en Windows (por si el archivo está bloqueado)
            import time
            for _ in range(3):
                try:
                    if os.path.exists(temp_video): os.remove(temp_video)
                    os.rename(output_path, temp_video)
                    break
                except OSError:
                    time.sleep(1)
            
            cmd_audio = [
                "ffmpeg", "-y", "-i", temp_video, "-i", audio_path,
                "-c:v", "copy", "-c:a", "aac", "-map", "0:v:0", "-map", "1:a:0",
                output_path
            ]
            # Aumentamos a 1800s (30 min) para el merge final de audio
            subprocess.run(cmd_audio, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1800)
            if os.path.exists(temp_video):
                try: os.remove(temp_video)
                except: pass

    except Exception as e:
        print(f"[FFMPEG] Error en concatenación: {e}")
        raise
    finally:
        # Limpiar archivo temporal
        if concat_file.exists():
            try: concat_file.unlink()
            except: pass
