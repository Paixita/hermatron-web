"""
📝 Script Agent — Inspirado en ViMax
Generador de guiones con narrativa coherente, arcos dramáticos
y diálogos por personaje. Usa el LLM de Hermatron como backbone.
"""
import asyncio
import json
import re
from typing import Optional


# Plantilla de sistema para guiones cinematográficos avanzados
SYSTEM_PROMPT_SCRIPT = """Eres un GUIONISTA CINEMATOGRÁFICO EXPERTO para la serie animada colombiana "Las Aventuras de Julián".

PERSONAJES FIJOS DE LA SERIE (mantener SIEMPRE su aspecto):
- Julián (8 años): Niño afrocolombiano, piel negra, pelo corto y muy rizado negro, suéter amarillo
- Hamilton: Joven mestizo/trigueño, mayor que Julián, elegante, ojos claros verdes, camisa blanca
- El Zarco: Joven colombiano trigueño/mulato, ojos azul claro intensos, chaqueta oscura, moto Calima 175 azul
- Rosalba (mamá): Mujer afrocolombiana 43 años, piel negra, sonrisa maternal, vestido sobrio
- Carlos (papá): Hombre afrocolombiano 45 años, piel negra, ropa de trabajo, electricista
- Vanessa (hermana mayor, 18 años): Piel morena clara, ojos miel, ropa veraniega casual
- Valentina (hermana menor, 15 años): Afrocolombiana, piel negra, uniforme escolar
- Don Nelson (vecino): 55 años, camisa a cuadros, gafas, anillo de sello grande, misterioso

REGLAS DEL GUIÓN:
1. Cada escena dura exactamente 5 segundos de video
2. La narración de cada escena: máximo 15 palabras (para que se lea en 5 segundos)
3. Los diálogos se escriben como: Personaje: "Texto del diálogo"
4. La descripción_visual SIEMPRE en INGLÉS para compatibilidad con modelos de IA
5. La descripción visual incluye ACCIÓN y MOVIMIENTO (nunca escenas estáticas)
6. Mantener CONTINUIDAD: si es de noche en escena 2, sigue de noche en escena 3
7. Incluir EMOCIONES reales: alegría, tensión, sorpresa, tristeza, determinación

ESTRUCTURA DRAMÁTICA (como ViMax Narrative Engine):
- Escena 1-2: Planteamiento (presentación del conflicto o situación)
- Escenas 3-N-1: Desarrollo (acción, diálogos, evolución)
- Última escena: Resolución (conclusión satisfactoria o giro dramático)

Responde SOLO con JSON válido:
{
    "titulo_episodio": "Título del capítulo",
    "sinopsis": "Resumen de 2 líneas del episodio",
    "guion_completo": "Narrativa completa del guión (150-200 palabras)",
    "escenas": [
        {
            "numero": 1,
            "titulo": "Título de la escena",
            "texto_narracion": "Máximo 15 palabras de narración. O: Personaje: 'Diálogo corto.'",
            "descripcion_visual": "IN ENGLISH: [Character with exact physical description], [action in progress], [camera angle], [lighting], [cinematic quality]",
            "emocion": "alegre|tenso|sorprendido|dramático|tierno|misterioso",
            "personajes_en_escena": ["Julián", "Hamilton"],
            "continuidad": "nota sobre qué se mantiene de la escena anterior (hora del día, lugar, etc.)"
        }
    ]
}"""


class ScriptAgent:
    """
    Agente de Guionaje (inspirado en ViMax Script Agent + Storyboard Agent).
    
    Genera guiones con:
    - Arcos dramáticos reales (planteamiento/nudo/desenlace)
    - Continuidad temporal entre escenas
    - Diálogos por personaje con formato multi-voz
    - Emociones por escena
    """

    def __init__(self, llm_caller=None):
        """
        llm_caller: función async que acepta (system_prompt, user_prompt) y retorna str
        """
        self._llm = llm_caller

    async def generar_guion(
        self,
        tema: str,
        descripcion: str,
        num_escenas: int = None,
        tono: str = "aventura"
    ) -> dict:
        """
        Genera un guión completo con arco dramático y consistencia de personajes.
        
        Returns: dict con 'titulo_episodio', 'sinopsis', 'guion_completo', 'escenas'
        """
        if not self._llm:
            print("[SCRIPT AGENT] ⚠️ Sin LLM configurado, usando guión básico")
            return self._guion_fallback(tema, num_escenas or 3)

        instruccion_escenas = ""
        if num_escenas:
            instruccion_escenas = f"\nGENERA EXACTAMENTE {num_escenas} ESCENAS. No más, no menos."

        user_prompt = f"""TEMA DEL EPISODIO: {tema}
DESCRIPCIÓN: {descripcion}
TONO: {tono}
{instruccion_escenas}

Crea el guión completo del episodio con arco dramático real.
Recuerda: cada escena = 5 segundos de video. La descripción_visual en INGLÉS."""

        try:
            texto = await self._llm(SYSTEM_PROMPT_SCRIPT, user_prompt)
            texto = re.sub(r'^```json\s*', '', texto)
            texto = re.sub(r'\s*```$', '', texto).strip()
            if not texto.startswith('{'):
                idx = texto.find('{')
                if idx != -1:
                    texto = texto[idx:]
            guion = json.loads(texto)
            print(f"[SCRIPT AGENT] ✅ Guión generado: '{guion.get('titulo_episodio', tema)}' "
                  f"con {len(guion.get('escenas', []))} escenas")
            return guion
        except Exception as e:
            print(f"[SCRIPT AGENT] ⚠️ Error generando guión: {e}. Usando fallback.")
            return self._guion_fallback(tema, num_escenas or 3)

    def _guion_fallback(self, tema: str, num_escenas: int) -> dict:
        """Guión de emergencia si el LLM falla."""
        escenas = []
        for i in range(num_escenas):
            escenas.append({
                "numero": i + 1,
                "titulo": f"Escena {i + 1}",
                "texto_narracion": f"En esta aventura, Julián descubre algo increíble.",
                "descripcion_visual": (
                    f"8-year-old Afro-Colombian black boy Julian with short curly black hair "
                    f"and yellow sweater, walking confidently through a Colombian neighborhood, "
                    f"cinematic shot, warm sunlight, 4K quality"
                ),
                "emocion": "alegre",
                "personajes_en_escena": ["Julián"],
                "continuidad": "Día soleado en el barrio"
            })
        return {
            "titulo_episodio": tema,
            "sinopsis": f"Julián vive una nueva aventura sobre {tema}.",
            "guion_completo": f"En las calles de su barrio, Julián aprende sobre {tema}.",
            "escenas": escenas
        }

    def convertir_a_formato_hermatron(self, guion: dict) -> dict:
        """
        Convierte el formato del ScriptAgent al formato que espera Hermatron.
        """
        escenas_hermatron = []
        for e in guion.get("escenas", []):
            escenas_hermatron.append({
                "numero": e.get("numero", len(escenas_hermatron) + 1),
                "titulo": e.get("titulo", ""),
                "texto_narracion": e.get("texto_narracion", ""),
                "descripcion_visual": e.get("descripcion_visual", ""),
                "angulo_camara": "medium shot",
                "iluminacion": "natural cinematic light",
                "paleta_colores": "warm vibrant colors",
                "movimiento": e.get("emocion", "dynamic"),
                "emocion": e.get("emocion", "neutral"),
                "query_pexels": "cinematic Colombia",
                "personajes_en_escena": e.get("personajes_en_escena", []),
                "continuidad": e.get("continuidad", ""),
                "aprobada": True
            })

        return {
            "guion_completo": guion.get("guion_completo", ""),
            "titulo_episodio": guion.get("titulo_episodio", ""),
            "sinopsis": guion.get("sinopsis", ""),
            "escenas": escenas_hermatron
        }


# Instancia global (se configura con el LLM al inicializar el video manager)
script_agent = ScriptAgent()
