# app/agents/scriptwriter_agent.py
# ✍️ El Guionista Agent - Escribe el libreto, diálogos y estructura de escenas

import json
import re

class ScriptwriterAgent:
    """
    Agente encargado de la estructura narrativa del video.
    Expande la idea del usuario en escenas fluidas y diálogos cinematográficos.
    """
    def __init__(self):
        pass

    async def generar_guion(self, tema: str, prompt_usuario: str, call_llm_fn) -> dict:
        """
        Escribe el libreto estructurado en formato JSON.
        """
        print("[GUIONISTA AGENT] ✍️ Escribiendo libreto cinematográfico...")
        
        system_prompt = """
Actúa como un GUIONISTA DE CINE DE ELITE. Tu tarea es expandir la idea del usuario en una estructura narrativa dividida en escenas para un video.
Asegura un ritmo dramático consistente.

🚫 REGLAS NARRATIVAS DE ORO:
1. DURACIÓN DE ESCENAS (CRÍTICO): Cada escena dura exactamente 5 segundos. Por lo tanto, la narración (texto_narracion) de cada escena debe ser sumamente CORTA (entre 12 y 15 palabras de lectura lenta y fluida).
2. FORMATO DE DIÁLOGOS MULTI-VOZ: Si la escena tiene un personaje hablando, el texto de la narración o del diálogo debe seguir estrictamente el formato: `Nombre: "Mensaje"`. 
   Ejemplos:
   - `Julián: "Hola Zarco, ¿has visto a Don Nelson pasar por aquí?"`
   - `El Zarco: "Ese señor no ha salido hoy, Julián. Mejor vuelve con tu mamá."`
3. COHERENCIA DE PERSONAJES: Mantén los nombres de los personajes consistentes en todo el guion (Julián, El Zarco, Hamilton, Don Nelson, Rosalba, Vanessa, Valentina, Carlos, etc.).
4. CANTIDAD DE ESCENAS: Si la idea es simple, genera de 1 a 3 escenas. Si es compleja, hasta 5 escenas. No agregues escenas de relleno sin sentido.

Responde estrictamente con un objeto JSON válido con la siguiente estructura:
{
    "guion_completo": "Un resumen narrativo del guion completo (100-150 palabras).",
    "escenas": [
        {
            "numero": 1,
            "titulo": "Título descriptivo de la escena",
            "texto_narracion": "El texto que será narrado/hablado. Recuerda la regla de 12-15 palabras máximo y el formato Nombre: 'Mensaje' si es un diálogo.",
            "descripcion_sugestiva": "Una breve descripción en español de lo que pasa en la escena para guiar al equipo de arte."
        }
    ]
}
"""
        user_prompt = f"""
TEMA DEL VIDEO: {tema}
DESCRIPCIÓN DEL USUARIO: {prompt_usuario}

Diseña la estructura de escenas y diálogos. Responde únicamente con el JSON estructurado.
"""
        try:
            res_text = await call_llm_fn(system_prompt, user_prompt, json_mode=True)
            # Limpiar markdown de JSON
            res_text = re.sub(r'^```json\s*', '', res_text)
            res_text = re.sub(r'\s*```$', '', res_text)
            res_text = res_text.strip()
            if not res_text.startswith('{'):
                idx = res_text.find('{')
                if idx != -1:
                    res_text = res_text[idx:]
            
            data = json.loads(res_text)
            print(f"[GUIONISTA AGENT] ✅ Guion generado con {len(data.get('escenas', []))} escenas.")
            return data
        except Exception as e:
            print(f"[GUIONISTA AGENT] ⚠️ Error escribiendo guion: {e}. Usando fallback de emergencia.")
            # Fallback simple
            return {
                "guion_completo": f"Historia sobre {tema}.",
                "escenas": [
                    {
                        "numero": 1,
                        "titulo": "Escena de apertura",
                        "texto_narracion": f"Narrador: 'Esta es una historia sobre {tema}.'",
                        "descripcion_sugestiva": "Apertura cinematográfica del tema."
                    }
                ]
            }
