"""Probar TODAS las voces masculinas en español"""
import asyncio
import edge_tts
import os

TEXTO_PRUEBA = "¡Hola mi pana! Soy Hermatron, tu asistente creativo profesional. Estoy probando todas las voces disponibles para encontrar la mejor para ti. ¿Cuál te gusta más?"

VOCES_MASCULINAS = [
    ("es-ES-AlvaroNeural", "España ⭐"),
    ("es-MX-JorgeNeural", "México"),
    ("es-US-AlonsoNeural", "US Neutro"),
    ("es-AR-TomasNeural", "Argentina"),
    ("es-CO-GonzaloNeural", "Colombia"),
    ("es-CL-LorenzoNeural", "Chile"),
    ("es-PE-AlexNeural", "Perú"),
    ("es-VE-SebastianNeural", "Venezuela"),
    ("es-CR-JuanNeural", "Costa Rica"),
    ("es-PA-RobertoNeural", "Panamá"),
    ("es-UY-MateoNeural", "Uruguay"),
]

AUDIO_DIR = "C:/WINDOWS/system32/hermatron_agent/audio"

async def probar_voz(voz, etiqueta):
    try:
        archivo = f"{AUDIO_DIR}/voz_{etiqueta.replace(' ', '_').replace('⭐', '')}.mp3"
        print(f"🎙️ Generando: {voz} ({etiqueta})...")
        communicate = edge_tts.Communicate(TEXTO_PRUEBA, voz, rate="-10%")
        await communicate.save(archivo)
        size = os.path.getsize(archivo)
        print(f"  ✅ Listo: {size/1024:.0f} KB")
        return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

async def main():
    print(f"\n{'='*60}")
    print(f"🎙️ PROBANDO {len(VOCES_MASCULINAS)} VOCES MASCULINAS")
    print(f"{'='*60}\n")
    
    for voz, etiqueta in VOCES_MASCULINAS:
        await probar_voz(voz, etiqueta)
    
    print(f"\n{'='*60}")
    print("✅ ¡Todas las voces generadas!")
    print(f"{'='*60}")
    print(f"\n📁 Están en: {AUDIO_DIR}")
    print("\n🎵 Reproduce cada archivo 'voz_*.mp3' para escucharlas")
    print("y dime cuál te gusta más, mi pana\n")

asyncio.run(main())
