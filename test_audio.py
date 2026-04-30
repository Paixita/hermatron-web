from app.voz import generador_voz
import asyncio

async def test():
    print("Probando generación de audio...")
    try:
        ruta = await generador_voz.generar("Hola mi pana, esto es una prueba")
        print(f"Audio generado: {ruta}")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(test())
