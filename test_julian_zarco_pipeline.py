import asyncio
import sys
from app.main import client
from app.video import generador_video

async def main():
    print("="*60)
    print("🎬 PIPELINE AUTOMATIZADO: JULIÁN Y EL ZARCO - CAPÍTULO 1 🎬")
    print("="*60)
    
    tema = "Julian y el Zarco - Capitulo 1: La Confesion"
    prompt = """
    Libreto y Narrativa de la Escena:
    Julián: "Es de verdad muy hermoso, yo tengo problemas Hamilton y por eso quise encontrarme contigo aquí porque aquí estamos seguros."
    Hamilton: "Me preocupa tu forma de decirme las cosas. ¿Qué te pasa Julián? ¿Te puedo ayudar en algo?"
    Julián: "Solo necesito de ti que me escuches y me ayudes, porque tengo unos problemas con los pelados del barrio."
    Hamilton: "Cómo así, dime, lo resolveremos juntos."
    Julián: "Para que me puedas entender en qué lío estoy metido te contaré mis inicios... Todo comenzó un día cuando yo era un pelado de 8 años. Ese día me levanté en mi cuarto. Mi hermana mayor estaba dormida... me vestí y salí a ver si había algo de desayunar."
    """
    
    # Usaremos la voz masculina colombiana nativa de Edge TTS
    voz_colombiana = "es-CO-GonzaloNeural"
    
    try:
        # FASE 1 & 2: Analizar tema y Diseñar Escenas con IA (Groq)
        print("\n🧠 [1/3] Diseñando escenas del guion con IA...")
        proyecto_id = await generador_video.analizar_tema(tema, prompt, client)
        print(f"✅ Proyecto creado con ID: {proyecto_id}")
        
        await generador_video.disenar_escenas(proyecto_id, client)
        
        # Configurar la voz colombiana en el proyecto antes de producir
        proj_obj = generador_video._cargar_proyecto(proyecto_id)
        if proj_obj:
            proj_obj.voz = voz_colombiana
            generador_video._guardar_proyecto(proj_obj)
            print(f"🎤 Voz configurada: {voz_colombiana} (Español Colombiano 🇨🇴)")
        
        # FASE 3: Aprobar escenas automáticamente
        proyecto = generador_video.obtener_proyecto(proyecto_id)
        escenas = proyecto.get('escenas_disenadas', [])
        print(f"🎬 Storyboard diseñado con {len(escenas)} escenas.")
        
        for escena in escenas:
            generador_video.aprobar_escena(proyecto_id, escena['numero'])
        print("✅ Todas las escenas aprobadas.")
        
        # FASE 4: Producción de video (Generación visual, audio y compilación FFmpeg)
        print("\n🎨 [2/3] Generando contenido visual, voz colombiana y ensamblado final...")
        await generador_video.producir_video(
            proyecto_id=proyecto_id,
            groq_client=client,
            generar_voz_func=None
        )
        
        # Cargar proyecto final para obtener el nombre del archivo
        proj_final = generador_video.obtener_proyecto(proyecto_id)
        archivo_final = proj_final.get("archivo_final")
        
        print("\n" + "="*60)
        print("🚀 [3/3] ¡PRODUCCIÓN COMPLETADA CON ÉXITO!")
        print(f"🎥 Video final generado: {generador_video.videos_dir / archivo_final}")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Error en la producción: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Soporte para loops asíncronos en Windows/Linux
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
