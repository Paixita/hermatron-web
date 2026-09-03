import asyncio
import edge_tts

async def main():
    voices = await edge_tts.list_voices()
    spanish = [v for v in voices if v['Locale'].startswith('es')]
    
    print("\n🎙️ VOCES ESPAÑOL DISPONIBLES EN edge-tts:\n")
    print(f"{'Nombre':<30} {'Género':<10} {'Locale'}")
    print("-" * 60)
    for v in spanish:
        nombre = v['ShortName']
        genero = "♂️ Masculino" if v['Gender'] == 'Male' else "♀️ Femenino"
        locale = v['Locale']
        print(f"{nombre:<30} {genero:<15} {locale}")
    
    print(f"\n✅ Total: {len(spanish)} voces en español")

asyncio.run(main())
