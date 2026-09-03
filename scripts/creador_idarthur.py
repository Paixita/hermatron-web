import os
import sys
import json
import uuid
import httpx
import urllib.parse
from dotenv import load_dotenv
import asyncio

# Cargar variables de entorno de Hermatron
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    print("❌ ERROR: No se encontró GROQ_API_KEY en el archivo .env de Hermatron.")
    sys.exit(1)

# Rutas de IdarThur
IDARTHUR_PATH = r"C:\Users\Galax\OneDrive\Escritorio\IdarThur"
DATA_PATH = os.path.join(IDARTHUR_PATH, "data", "historias")
IMG_PATH = os.path.join(IDARTHUR_PATH, "public", "historias")

# Asegurar que existan las carpetas en IdarThur
os.makedirs(DATA_PATH, exist_ok=True)
os.makedirs(IMG_PATH, exist_ok=True)

async def generar_historia_groq(tema):
    print(f"\n🧠 [Hermatron Investigador] Pensando en la historia sobre: '{tema}'...")
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""
    Eres un escritor experto en historias de viajes y un ilustrador. 
    Escribe una historia real y emocionante sobre: {tema}.
    Usa nombres ficticios.
    
    Devuelve EXACTAMENTE Y ÚNICAMENTE un objeto JSON válido con la siguiente estructura, sin formato Markdown alrededor:
    {{
      "titulo": "Título elegante",
      "subtitulo": "Un breve subtítulo atrapante",
      "personajes": "Nombres de los personajes",
      "ano": "2024",
      "narrativa": "La historia completa en varios párrafos usando <br><br> para separar los párrafos. Que sea elegante y emocionante.",
      "prompt_imagen": "Una descripción muy detallada en INGLÉS para generar una imagen. DEBES INCLUIR términos como 'desaturated, muted colors, natural lighting, raw photography, cinematic soft light, hyperrealistic' para evitar que la imagen salga con colores muy saturados o irreales."
    }}
    """
    
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "response_format": {"type": "json_object"}
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, headers=headers, json=data)
        if response.status_code == 200:
            content = response.json()["choices"][0]["message"]["content"]
            return json.loads(content)
        else:
            print(f"❌ Error de Groq: {response.text}")
            sys.exit(1)

async def descargar_imagen(prompt_imagen, filename):
    print(f"\n🎨 [Hermatron Ilustrador] Pintando la imagen (Modo Realista)...\nPrompt: {prompt_imagen}")
    
    # Formatear el prompt para la URL
    prompt_seguro = urllib.parse.quote(prompt_imagen)
    # Agregar parámetros para evitar saturación y usar modelo realista
    url = f"https://image.pollinations.ai/prompt/{prompt_seguro}?width=1200&height=800&nologo=true&enhance=false&model=flux-realism"
    
    filepath = os.path.join(IMG_PATH, filename)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(url)
        if response.status_code == 200:
            with open(filepath, 'wb') as f:
                f.write(response.content)
            print(f"✅ Imagen guardada exitosamente en IdarThur: {filename}")
        else:
            print(f"❌ Error descargando la imagen: {response.status_code}")

async def main():
    print("="*50)
    print("✈️  HERMATRON x IDARTHUR - Creador de Historias  ✈️")
    print("="*50)
    
    tema = input("\n📝 ¿De qué quieres que trate la historia de hoy? (ej. 'Una pareja que perdió su perro en el aeropuerto de Miami'): ")
    
    if not tema.strip():
        print("Operación cancelada.")
        return
        
    try:
        # 1. Generar la historia
        historia_json = await generar_historia_groq(tema)
        
        # 2. Mostrar borrador
        print("\n" + "="*50)
        print(f"TITULO: {historia_json['titulo']}")
        print(f"SUBTITULO: {historia_json['subtitulo']}")
        print("="*50)
        
        aprobar = input("\n¿Apruebas este borrador para generar la imagen y publicarlo? (s/n): ")
        if aprobar.lower() != 's':
            print("❌ Historia descartada.")
            return
            
        # 3. Descargar imagen
        id_historia = f"historia-{uuid.uuid4().hex[:8]}"
        nombre_imagen = f"{id_historia}.jpg"
        
        await descargar_imagen(historia_json['prompt_imagen'], nombre_imagen)
        
        # 4. Guardar archivo JSON
        historia_final = {
            "id": id_historia,
            "titulo": historia_json['titulo'],
            "subtitulo": historia_json['subtitulo'],
            "personajes": historia_json['personajes'],
            "ano": historia_json['ano'],
            "narrativa": historia_json['narrativa'],
            "imagen": f"/historias/{nombre_imagen}"
        }
        
        json_path = os.path.join(DATA_PATH, f"{id_historia}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(historia_final, f, ensure_ascii=False, indent=2)
            
        # 5. Generar index.js para compatibilidad con Cloudflare
        historias_list = []
        for file in os.listdir(DATA_PATH):
            if file.endswith('.json'):
                with open(os.path.join(DATA_PATH, file), 'r', encoding='utf-8') as f:
                    historias_list.append(json.load(f))
        
        index_content = "export const stories = " + json.dumps(historias_list, ensure_ascii=False, indent=2) + ";"
        with open(os.path.join(DATA_PATH, 'index.js'), 'w', encoding='utf-8') as f:
            f.write(index_content)
            
        print(f"✅ Texto de la historia guardado en: {json_path}")
        print("✅ Índice regenerado correctamente (index.js).")
        print("\n🚀 ¡Todo listo! Hermatron ha inyectado la historia en IdarThur.")
        print("Si quieres subirla a internet, ve a IdarThur y corre: git add . && git commit -m 'Historia' && git push")
        
    except Exception as e:
        print(f"\n❌ Ocurrió un error inesperado: {e}")

if __name__ == "__main__":
    # Evitar problemas de loop en Windows
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
