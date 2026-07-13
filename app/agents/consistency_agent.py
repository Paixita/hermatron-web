"""
🎭 Visual Consistency Agent — Inspirado en ViMax
Mantiene la coherencia visual de personajes entre escenas.
Funciona como el "Dependency-Aware Visual Consistency" de ViMax.
"""
import re
import unicodedata
from typing import Optional


def _normalizar(texto: str) -> str:
    """Normaliza texto quitando tildes y pasando a minúsculas."""
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    ).lower().strip()


class ConsistencyAgent:
    """
    Agente de Consistencia Visual (inspirado en ViMax).
    
    Su misión: asegurarse de que cada personaje tenga EXACTAMENTE
    los mismos rasgos físicos en TODAS las escenas del video.
    
    Estrategia:
    1. Extrae qué personajes aparecen en cada escena
    2. Inyecta su descripción física exacta en el prompt visual
    3. Añade restricciones de "NO cambiar" al prompt
    """

    # Prompts de referencia por personaje (en inglés para los modelos de difusión)
    PERSONAJES_CANON = {
        "julian": {
            "nombre": "Julián",
            "prompt_en": (
                "8-year-old Afro-Colombian black boy named Julian, "
                "very short tight curly black hair, innocent wide brown eyes, "
                "clean yellow sweater, dark skin, cheerful child expression, "
                "SAME CHARACTER IN EVERY SCENE"
            ),
            "restriccion": "black boy, dark skin, curly hair, yellow sweater",
        },
        "hamilton": {
            "nombre": "Hamilton",
            "prompt_en": (
                "teenage Colombian mestizo boy named Hamilton, "
                "light brown skin, short neat dark hair, distinctive light green eyes, "
                "elegant white shirt, older than Julian, confident expression, "
                "SAME CHARACTER IN EVERY SCENE"
            ),
            "restriccion": "light-skinned boy, green eyes, white shirt",
        },
        "el zarco": {
            "nombre": "El Zarco",
            "prompt_en": (
                "young Colombian mulatto man named El Zarco, "
                "intense piercing light blue eyes, stylish dark jacket, "
                "medium brown skin, standing near a blue Calima 175 motorcycle, "
                "urban cool attitude, SAME CHARACTER IN EVERY SCENE"
            ),
            "restriccion": "light blue eyes, dark jacket, motorcycle nearby",
        },
        "zarco": {
            "nombre": "El Zarco",
            "prompt_en": (
                "young Colombian mulatto man named El Zarco, "
                "intense piercing light blue eyes, stylish dark jacket, "
                "medium brown skin, blue Calima 175 motorcycle, "
                "SAME CHARACTER IN EVERY SCENE"
            ),
            "restriccion": "light blue eyes, dark jacket",
        },
        "rosalba": {
            "nombre": "Rosalba",
            "prompt_en": (
                "43-year-old Afro-Colombian woman named Rosalba, "
                "dark skin, beautiful warm maternal smile, elegant neat hair, "
                "modest nice dress, motherly loving expression, "
                "SAME CHARACTER IN EVERY SCENE"
            ),
            "restriccion": "dark-skinned woman, maternal expression",
        },
        "carlos": {
            "nombre": "Carlos",
            "prompt_en": (
                "45-year-old Afro-Colombian working-class man named Carlos, "
                "dark skin, strong build, wearing work clothes, "
                "repairing appliances in home garage, "
                "SAME CHARACTER IN EVERY SCENE"
            ),
            "restriccion": "dark-skinned man, work clothes",
        },
        "vanessa": {
            "nombre": "Vanessa",
            "prompt_en": (
                "18-year-old Colombian young woman named Vanessa, "
                "light brown skin, honey-colored eyes, "
                "casual summer outfit, cheerful young expression, "
                "SAME CHARACTER IN EVERY SCENE"
            ),
            "restriccion": "light brown skin, honey eyes, summer clothes",
        },
        "valentina": {
            "nombre": "Valentina",
            "prompt_en": (
                "15-year-old Afro-Colombian schoolgirl named Valentina, "
                "dark skin, wearing neat school uniform, holding notebooks, "
                "studious expression, SAME CHARACTER IN EVERY SCENE"
            ),
            "restriccion": "dark-skinned girl, school uniform",
        },
        "don nelson": {
            "nombre": "Don Nelson",
            "prompt_en": (
                "55-year-old mature Colombian man named Don Nelson, "
                "weathered mature face, plaid shirt, reading glasses, "
                "large gold signet ring, mysterious expression, "
                "standing near old wooden door, SAME CHARACTER IN EVERY SCENE"
            ),
            "restriccion": "older man, plaid shirt, glasses, signet ring",
        },
        "nelson": {
            "nombre": "Don Nelson",
            "prompt_en": (
                "55-year-old mature Colombian man named Don Nelson, "
                "plaid shirt, reading glasses, large signet ring, "
                "mysterious expression, SAME CHARACTER IN EVERY SCENE"
            ),
            "restriccion": "older man, glasses, signet ring",
        },
    }

    def detectar_personajes(self, texto_escena: str) -> list[dict]:
        """
        Detecta qué personajes del canon aparecen en la descripción de la escena.
        Retorna lista de dicts con info del personaje.
        """
        texto_norm = _normalizar(texto_escena)
        encontrados = []
        vistos = set()

        for clave, datos in self.PERSONAJES_CANON.items():
            if clave in texto_norm and datos["nombre"] not in vistos:
                encontrados.append(datos)
                vistos.add(datos["nombre"])

        return encontrados

    def blindar_prompt(self, prompt_visual: str, personajes_escena: list[dict] = None) -> str:
        """
        Inyecta la descripción exacta de los personajes al prompt visual.
        Si no se pasan personajes, los detecta automáticamente del prompt.
        
        Estrategia ViMax: "Dependency-Aware Visual Consistency"
        """
        if personajes_escena is None:
            personajes_escena = self.detectar_personajes(prompt_visual)

        if not personajes_escena:
            return prompt_visual

        # Construir bloque de consistencia
        bloques = []
        for p in personajes_escena:
            bloques.append(f"[CHARACTER LOCK - {p['nombre']}]: {p['prompt_en']}")

        bloque_consistencia = " | ".join(bloques)

        # Insertar al inicio del prompt para máximo peso en el modelo
        prompt_blindado = f"{bloque_consistencia}, {prompt_visual}"

        # Añadir restricciones de "NO CAMBIAR" al final
        restricciones = [p["restriccion"] for p in personajes_escena]
        if restricciones:
            prompt_blindado += (
                f", CRITICAL: maintain exact character appearance: "
                f"{', '.join(restricciones)}, do NOT change character traits"
            )

        return prompt_blindado

    def blindar_escenas(self, escenas: list[dict]) -> list[dict]:
        """
        Aplica el blindaje de consistencia a TODAS las escenas de un proyecto.
        Modifica el campo 'descripcion_visual' de cada escena.
        Retorna las escenas actualizadas.
        """
        escenas_blindadas = []
        for escena in escenas:
            escena_copia = dict(escena)
            desc_original = escena_copia.get("descripcion_visual", "")
            texto_narracion = escena_copia.get("texto_narracion", "")

            # Detectar personajes tanto en la descripción visual como en la narración
            personajes = self.detectar_personajes(desc_original + " " + texto_narracion)

            if personajes:
                nombres = [p["nombre"] for p in personajes]
                print(f"[CONSISTENCY] 👁️ Escena {escena_copia.get('numero', '?')}: "
                      f"Blindando personajes: {', '.join(nombres)}")
                escena_copia["descripcion_visual"] = self.blindar_prompt(desc_original, personajes)
            
            escenas_blindadas.append(escena_copia)

        return escenas_blindadas

    def blindar_con_db(self, prompt_visual: str, personajes_db: list[dict]) -> str:
        """
        Versión que usa la base de datos de personajes de Hermatron.
        Complementa el canon estático con datos dinámicos de la BD.
        """
        prompt_norm = _normalizar(prompt_visual)
        bloques_extra = []

        for p in personajes_db:
            nombre_norm = _normalizar(p.get("nombre", ""))
            if nombre_norm and nombre_norm in prompt_norm:
                prompt_ref = p.get("prompt_referencia", "")
                nombre = p.get("nombre", "")
                if prompt_ref and nombre:
                    bloques_extra.append(f"[DB CHARACTER - {nombre}]: {prompt_ref}")

        if bloques_extra:
            return f"{' | '.join(bloques_extra)}, {prompt_visual}"

        return prompt_visual


# Instancia global del agente
consistency_agent = ConsistencyAgent()
