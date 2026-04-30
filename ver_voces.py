import pyttsx3

engine = pyttsx3.init()
voces = engine.getProperty('voices')

print("=" * 50)
print("VOCES DISPONIBLES EN TU SISTEMA:")
print("=" * 50)

for i, voz in enumerate(voces):
    print(f"\n{i+1}. ID: {voz.id}")
    print(f"   Nombre: {voz.name}")
    print(f"   Idiomas: {voz.languages}")
    print(f"   Género: {voz.gender}")
    print(f"   Edad: {voz.age}")

print("\n" + "=" * 50)
print("Para usar una voz específica, copia el ID")
print("y configúralo en el código.")
print("=" * 50)
