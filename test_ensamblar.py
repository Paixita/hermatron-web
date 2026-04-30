import asyncio
from pathlib import Path
from app.video import VideoGenerator

async def main():
    generador = VideoGenerator()
    proyecto_id = "proyecto_1777076821"
    work_dir = Path(f"c:/Users/Galax/hermatron_agent/videos/{proyecto_id}")
    
    proyecto = generador.obtener_proyecto(proyecto_id)
    if not proyecto:
        print("No se encontró el proyecto")
        return
        
    print(f"Ensamblando proyecto: {proyecto_id}")
    escenas_aprobadas = [e for e in proyecto.get("escenas_disenadas", []) if e.get("aprobada", True)]
    
    video_final = await generador._ensamblar_video(
        proyecto_id=proyecto_id,
        work_dir=work_dir,
        audio_path=proyecto.get("audio_path"),
        escenas=escenas_aprobadas
    )
    print(f"Resultado: {video_final}")

if __name__ == "__main__":
    asyncio.run(main())
