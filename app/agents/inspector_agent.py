# app/agents/inspector_agent.py
# 🛡️ Inspector de Escenas / Director de Arte Agent - Refina encuadres, climatología e inyecta escenografías consistentes

import json
import re
import unicodedata
from app.memoria import memoria
from app.agents.style_agent import style_agent

class InspectorAgent:
    """
    Agente encargado de auditar la consistencia escénica e inyectar prompts de arte de alta definición.
    Cruza el guion con las escenografías cargadas en la base de datos y define parámetros visuales.
    """
    def __init__(self):
        pass

    async def inspeccionar_y_refinar(self, guion_data: dict, estilo_visual: str, call_llm_fn) -> dict:
        """
        Refina cada escena inyectando consistencia de personajes y escenarios.
        """
        print(f"[INSPECTOR AGENT] 🛡️ Analizando sets y refinando prompts de arte (Estilo: {estilo_visual})...")
        escenas = guion_data.get("escenas", [])
        
        try:
            escenografias = await memoria.obtener_todas_escenografias()
            personajes = await memoria.obtener_todos_personajes()
        except Exception as e:
            print(f"[INSPECTOR AGENT] ⚠️ Error leyendo DB: {e}")
            escenografias = []
            personajes = []

        def normalize(text):
            return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn').lower()

        # Obtener prefijo de estilo
        estilo_prompt = style_agent.get_prompt_prefix(estilo_visual)

        for esc in escenas:
            desc_sugestiva = esc.get("descripcion_sugestiva", "")
            texto = esc.get("texto_narracion", "")
            
            # 1. Detectar y asignar Escenografía
            escenografia_asociada = None
            for e_db in escenografias:
                nombre_esc = e_db.get("nombre", "").lower()
                if nombre_esc and (normalize(nombre_esc) in normalize(desc_sugestiva) or normalize(nombre_esc) in normalize(texto)):
                    escenografia_asociada = e_db
                    esc["escenografia_ref"] = e_db["nombre"]
                    break
            
            if not escenografia_asociada:
                esc["escenografia_ref"] = ""

            # 2. Construir la consulta de consistencia para el LLM
            prompt_consistencia_escena = ""
            if escenografia_asociada:
                prompt_consistencia_escena += f"\n- ESCENARIO: {escenografia_asociada['nombre']}: {escenografia_asociada['descripcion']} (Clima: {escenografia_asociada['clima']}, Hora: {escenografia_asociada['hora_dia']}, Suelo: {escenografia_asociada['material_suelo']})\n"
            
            # Buscar personajes implicados para pasar su ficha al LLM
            personajes_implicados = []
            for p in personajes:
                nombre_p = p.get("nombre", "").lower()
                if nombre_p and (normalize(nombre_p) in normalize(desc_sugestiva) or normalize(nombre_p) in normalize(texto)):
                    personajes_implicados.append(p)
            
            if personajes_implicados:
                prompt_consistencia_escena += "- PERSONAJES PARTICIPANTES (RASGOS OBLIGATORIOS):\n"
                for p in personajes_implicados:
                    prompt_consistencia_escena += f"  * {p['nombre']}: {p['descripcion_fisica']} (SD Prompt: {p['prompt_referencia']})\n"

            # 3. Llamar al LLM para generar el prompt técnico visual en inglés
            system_prompt = f"""
Actúa como un INGENIERO DE PROMPTS DE DIFUSIÓN DE ÉLITE y DIRECTOR DE ARTE DE CINE.
Tu objetivo es redactar un prompt visual cinematográfico detallado en INGLÉS para esta toma.

ESTILO SELECCIONADO PARA EL PROYECTO (USAR COMO BASE):
"{estilo_prompt}"

DETALLES DE CONSISTENCIA DE ESCENA:
{prompt_consistencia_escena}

🛠 ESTRUCTURA DEL PROMPT VISUAL (EN INGLÉS):
Combina el estilo de animación con el sujeto, la acción en progreso, encuadre de cámara, iluminación volumétrica y la escenografía indicada.
No utilices abstracciones, describe una acción física en progreso (ej: "A is walking towards B", "A is looking at B and smiling").

Responde estrictamente con un JSON válido:
{{
    "descripcion_visual": "Prompt detallado en inglés (50-70 palabras)...",
    "angulo_camara": "e.g. Medium shot, eye level",
    "iluminacion": "e.g. Warm dramatic orange rim light",
    "paleta_colores": "e.g. Saturated warm tones, dark background",
    "movimiento": "e.g. Subtle camera pan right",
    "emocion": "e.g. Focused, intense",
    "query_pexels": "e.g. street corner night orange light"
}}
"""
            user_prompt = f"""
NARRATIVA DE LA TOMA: "{texto}"
DESCRIPCIÓN DE ARTE SUGERIDA: "{desc_sugestiva}"

Redacta el prompt visual consistente en inglés y los detalles de cámara. Responde únicamente con el JSON estructurado.
"""
            try:
                res_text = await call_llm_fn(system_prompt, user_prompt, json_mode=True)
                res_text = re.sub(r'^```json\s*', '', res_text)
                res_text = re.sub(r'\s*```$', '', res_text)
                res_text = res_text.strip()
                diseno_visual = json.loads(res_text)
                
                # Rellenar datos en la escena
                esc["descripcion_visual"] = diseno_visual.get("descripcion_visual", "")
                esc["angulo_camara"] = diseno_visual.get("angulo_camara", "Medium shot")
                esc["iluminacion"] = diseno_visual.get("iluminacion", "Cinematic light")
                esc["paleta_colores"] = diseno_visual.get("paleta_colores", "Cinematic")
                esc["movimiento"] = diseno_visual.get("movimiento", "Static")
                esc["emocion"] = diseno_visual.get("emocion", "Neutral")
                esc["query_pexels"] = diseno_visual.get("query_pexels", "")
                
            except Exception as e:
                print(f"[INSPECTOR AGENT] ⚠️ Error refinando visuales para escena {esc.get('numero')}: {e}")
                # Fallback simple
                esc["descripcion_visual"] = f"{estilo_prompt}, scene based on: {texto}, {desc_sugestiva}, detailed background, 8k resolution"
                esc["angulo_camara"] = "Medium shot"
                esc["iluminacion"] = "Cinematic"
                esc["paleta_colores"] = "Cinematic"
                esc["movimiento"] = "Subtle zoom in"
                esc["emocion"] = "Neutral"
                esc["query_pexels"] = ""

        print("[INSPECTOR AGENT] ✅ Inspección de escenas finalizada.")
        return guion_data
