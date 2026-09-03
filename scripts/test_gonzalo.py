"""Prueba de voz Gonzalo Colombia - edge-tts"""
import asyncio
import edge_tts
import os

async def main():
    texto = "¡Hola mi pana! Soy Hermatron, tu asistente creativo. Estoy hablando con la voz de Gonzalo de Colombia. ¿Te gusta cómo sueno? Es una voz natural, casi humana, y es completamente gratis e ilimitada."
    voz = "es-CO-GonzaloNeural"
    salida = "C:/WINDOWS/system32/hermatron_agent/audio/test_gonzalo.mp3"
    
    print(f"🎙️ Generando audio con {voz}...")
    communicate = edge_tts.Communicate(texto, voz)
    await communicate.save(salida)
    
    size = os.path.getsize(salida)
    print(f"✅ Audio generado: {salida}")
    print(f"   Tamaño: {size/1024:.1f} KB")
    print(f"   Texto: '{texto}'")
    print(f"\n🎵 Reproduce el audio para escuchar a Gonzalo")

asyncio.run(main())
