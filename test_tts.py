import edge_tts
import asyncio
import os

async def test():
    print("Probando Edge TTS...")
    c = edge_tts.Communicate('Hola mi pana, esto es una prueba de audio', 'es-MX-JorgeNeural', rate='-5%', pitch='+0Hz')
    print("Generando audio...")
    await c.save('test.mp3')
    print(f"Done! Tamaño: {os.path.getsize('test.mp3')} bytes")

asyncio.run(test())
