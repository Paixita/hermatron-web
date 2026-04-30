import asyncio
from app.main import client
from app.video import generador_video

async def test_full_pipeline():
    print("Iniciando prueba profunda...")
    try:
        tema = "Prueba de error"
        prompt = "Una prueba sencilla para ver dónde falla el motor."
        voz = "es-MX-JorgeNeural"
        
        # 1. Analizar tema
        print("1. Analizar tema...")
        proyecto_id = await generador_video.analizar_tema(tema, prompt, client)
        print(f"Proyecto ID generado: {proyecto_id}")
        
        # 2. Diseñar escenas
        print("2. Diseñar escenas...")
        await generador_video.disenar_escenas(proyecto_id, client)
        
        # Aprobar escenas
        proyecto = generador_video.obtener_proyecto(proyecto_id)
        if hasattr(generador_video, '_cargar_proyecto'):
            proj_obj = generador_video._cargar_proyecto(proyecto_id)
            if proj_obj:
                proj_obj.voz = voz
                generador_video._guardar_proyecto(proj_obj)
                
        for escena in proyecto.get('escenas_disenadas', []):
            generador_video.aprobar_escena(proyecto_id, escena['numero'])
            
        # 3. Producir video
        print("3. Producir video (imágenes, audio, moviepy)...")
        await generador_video.producir_video(
            proyecto_id=proyecto_id, 
            groq_client=client, 
            generar_voz_func=None
        )
        print("PRUEBA EXITOSA")
    except Exception as e:
        print(f"FALLO DETECTADO: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_full_pipeline())
