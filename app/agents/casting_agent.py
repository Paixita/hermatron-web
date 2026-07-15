# app/agents/casting_agent.py
# 🎙️ Director de Reparto Agent - Escanea el guion, crea y registra personajes faltantes y asigna voces Edge-TTS

import re
import json
from app.memoria import memoria

# Voces del catálogo en español
VOCES_CATALOGO = [
    {"id": "es-CO-GonzaloNeural", "genero": "masculino", "perfil": "joven/adulto", "pais": "Colombia"},
    {"id": "es-CO-SalomeNeural",  "genero": "femenino",  "perfil": "joven/adulto", "pais": "Colombia"},
    {"id": "es-MX-JorgeNeural",   "genero": "masculino", "perfil": "joven/adulto", "pais": "México"},
    {"id": "es-MX-DaliaNeural",   "genero": "femenino",  "perfil": "joven",        "pais": "México"},
    {"id": "es-MX-LupeNeural",    "genero": "femenino",  "perfil": "adulto/maduro", "pais": "México"},
    {"id": "es-MX-BeatrizNeural", "genero": "femenino",  "perfil": "adulto/maduro", "pais": "México"},
    {"id": "es-ES-AlvaroNeural",  "genero": "masculino", "perfil": "adulto/maduro", "pais": "España"},
    {"id": "es-ES-LuciaNeural",   "genero": "femenino",  "perfil": "joven",        "pais": "España"},
    {"id": "es-ES-ElviraNeural",  "genero": "femenino",  "perfil": "adulto/maduro", "pais": "España"},
    {"id": "es-US-AlonsoNeural",  "genero": "masculino", "perfil": "joven/urbano", "pais": "EEUU"},
    {"id": "es-US-PalomaNeural",  "genero": "femenino",  "perfil": "joven",        "pais": "EEUU"},
    {"id": "es-AR-ElenaNeural",   "genero": "femenino",  "perfil": "joven/adulto", "pais": "Argentina"},
    {"id": "es-AR-TomasNeural",   "genero": "masculino", "perfil": "joven/adulto", "pais": "Argentina"}
]

class CastingAgent:
    """
    Agente encargado de la consistencia de personajes, actores y asignación de voces.
    Registra automáticamente nuevos personajes si aparecen en el libreto.
    """
    def __init__(self):
        pass

    async def asignar_elenco_y_voces(self, guion_data: dict, call_llm_fn) -> dict:
        """
        Escanea las escenas en guion_data, extrae los nombres de personajes
        que hablan o participan y configura sus identidades visuales y auditivas en la DB.
        """
        print("[CASTING AGENT] 🎙️ Auditando elenco y asignando casting de voces...")
        escenas = guion_data.get("escenas", [])
        
        # 1. Identificar personajes en las escenas
        personajes_detectados = set()
        dialog_pattern = re.compile(r"^([\w\sáéíóúÁÉÍÓÚñÑ]+)\s*:")
        
        for esc in escenas:
            texto = esc.get("texto_narracion", "")
            match = dialog_pattern.match(texto)
            if match:
                char_name = match.group(1).strip()
                personajes_detectados.add(char_name)
                # Guardar el personaje de referencia principal de esta escena
                esc["personaje_ref"] = char_name
            else:
                # Si es narrador o no hay diálogo explícito
                esc["personaje_ref"] = ""

        # 2. Registrar/auditar cada personaje detectado
        for nombre in personajes_detectados:
            if nombre.lower() in ("narrador", "narracion", "voz en off", "voz"):
                continue

            existente = await memoria.obtener_personaje(nombre)
            if existente:
                print(f"[CASTING AGENT] 👤 Personaje existente encontrado: {nombre} | Voz: {existente.get('voz_edge_tts')}")
                continue

            # Si el personaje no existe, debemos crearlo/diseñarlo automáticamente con la ayuda del LLM
            print(f"[CASTING AGENT] 🆕 Diseñando nuevo personaje: '{nombre}'...")
            prompt_diseño_sistema = """
Actúa como un DIRECTOR DE REPARTO Y CASTING DE CINE. Tu objetivo es diseñar la apariencia física y elegir la voz ideal para un nuevo personaje.
Responde estrictamente con un JSON válido:
{
    "descripcion_fisica": "Descripción física detallada en español (edad, tez, vestuario, rasgos faciales).",
    "prompt_referencia": "Detailed physical description in english for Stable Diffusion generation (e.g. '8-year-old boy, light brown skin, wearing a blue shirt, pixar 3d animation style').",
    "genero": "masculino o femenino",
    "perfil_edad": "joven o adulto o maduro"
}
"""
            prompt_diseño_usuario = f"Diseña al personaje llamado '{nombre}' para la historia."
            
            try:
                res_text = await call_llm_fn(prompt_diseño_sistema, prompt_diseño_usuario, json_mode=True)
                res_text = re.sub(r'^```json\s*', '', res_text)
                res_text = re.sub(r'\s*```$', '', res_text)
                res_text = res_text.strip()
                diseno = json.loads(res_text)
                
                # Asignar la mejor voz disponible
                genero_deseado = diseno.get("genero", "masculino").lower()
                perfil_deseado = diseno.get("perfil_edad", "joven").lower()
                
                # Filtrar voces candidatas
                candidatos = [v for v in VOCES_CATALOGO if v["genero"] == genero_deseado]
                if not candidatos:
                    candidatos = VOCES_CATALOGO
                
                # Buscar perfil de edad similar
                voz_elegida = candidatos[0]["id"]
                for c in candidatos:
                    if perfil_deseado in c["perfil"]:
                        voz_elegida = c["id"]
                        break
                
                # Guardar el personaje en la base de datos de Hermatron
                # Generamos una imagen de placeholder inicial para no dejar vacía la ficha
                placeholder_path = f"/static/personajes/{nombre.replace(' ', '_')}.png"
                await memoria.guardar_personaje(
                    nombre=nombre,
                    descripcion_fisica=diseno.get("descripcion_fisica", "Personaje de la historia."),
                    prompt_referencia=diseno.get("prompt_referencia", f"{nombre}, pixar 3d style"),
                    imagen_path=placeholder_path
                )
                await memoria.actualizar_voz_personaje(nombre, voz_elegida)
                print(f"[CASTING AGENT] ✅ Nuevo personaje registrado: {nombre} | Voz asignada: {voz_elegida}")
                
            except Exception as e:
                print(f"[CASTING AGENT] ⚠️ Error diseñando personaje '{nombre}': {e}. Registrando con valores por defecto.")
                # Valores por defecto de emergencia
                await memoria.guardar_personaje(
                    nombre=nombre,
                    descripcion_fisica=f"Personaje llamado {nombre}.",
                    prompt_referencia=f"{nombre}, pixar 3d style",
                    imagen_path=f"/static/personajes/{nombre}.png"
                )
                await memoria.actualizar_voz_personaje(nombre, "es-MX-JorgeNeural")

        return guion_data
