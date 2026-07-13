"""
🎬 Assembly Agent — Inspirado en ViMax Assembly Agent
Ensambla el video final con transiciones cinematográficas,
voces diferenciadas por personaje y sincronización perfecta.
"""
import re
from typing import Optional


# Voces disponibles por personaje en Edge-TTS
VOCES_POR_PERSONAJE = {
    "julián": "es-CO-GonzaloNeural",      # Niño - voz colombiana masculina
    "julian": "es-CO-GonzaloNeural",
    "hamilton": "es-MX-JorgeNeural",       # Joven - voz mexicana masculina joven
    "el zarco": "es-CO-GonzaloNeural",     # Joven adulto - colombiano
    "zarco": "es-CO-GonzaloNeural",
    "rosalba": "es-CO-SalomeNeural",       # Mamá - voz colombiana femenina
    "carlos": "es-MX-JorgeNeural",         # Papá - voz masculina
    "vanessa": "es-MX-DaliaNeural",        # Hermana mayor - femenina joven
    "valentina": "es-CO-SalomeNeural",     # Hermana menor - femenina
    "don nelson": "es-ES-AlvaroNeural",    # Vecino mayor - española madura
    "nelson": "es-ES-AlvaroNeural",
    "narrador": "es-MX-JorgeNeural",       # Narrador por defecto
    "default": "es-MX-JorgeNeural",
}

# Regex para detectar diálogos: "Personaje: "Texto""
DIALOGO_PATTERN = re.compile(r'^([A-ZÁÉÍÓÚÑa-záéíóúñ\s]+):\s*["\'](.+?)["\']', re.MULTILINE)


class AssemblyAgent:
    """
    Agente de Ensamblaje (inspirado en ViMax Assembly Agent).
    
    Mejoras sobre el ensamblaje actual de Hermatron:
    1. Detecta diálogos en el texto y asigna voz correcta por personaje
    2. Parsea segmentos de voz múltiple en una escena
    3. Proporciona metadatos para crossfade entre escenas
    """

    def detectar_tipo_audio(self, texto_narracion: str) -> str:
        """
        Detecta si el texto es:
        - 'dialogo': contiene "Personaje: 'Texto'"
        - 'narracion': texto narrativo normal
        - 'mixto': mezcla de narración y diálogos
        """
        if DIALOGO_PATTERN.search(texto_narracion):
            # Verificar si hay texto adicional fuera del diálogo
            texto_sin_dialogos = DIALOGO_PATTERN.sub('', texto_narracion).strip()
            if texto_sin_dialogos:
                return 'mixto'
            return 'dialogo'
        return 'narracion'

    def parsear_segmentos_voz(self, texto_narracion: str) -> list[dict]:
        """
        Convierte texto de escena en segmentos de audio con voz asignada.
        
        Ejemplo:
        Input: 'Hamilton: "¿Qué pasa Julian?" Julián: "Nada, amigo."'
        Output: [
            {"voz": "es-MX-JorgeNeural", "texto": "¿Qué pasa Julian?", "personaje": "Hamilton"},
            {"voz": "es-CO-GonzaloNeural", "texto": "Nada, amigo.", "personaje": "Julián"}
        ]
        """
        segmentos = []
        tipo = self.detectar_tipo_audio(texto_narracion)

        if tipo == 'narracion':
            # Texto de narración → voz del narrador
            segmentos.append({
                "personaje": "Narrador",
                "texto": texto_narracion.strip(),
                "voz": VOCES_POR_PERSONAJE["narrador"],
                "tipo": "narracion"
            })
        else:
            # Buscar todos los diálogos
            matches = list(DIALOGO_PATTERN.finditer(texto_narracion))
            ultimo_fin = 0

            for match in matches:
                # Texto antes del diálogo (narración)
                texto_antes = texto_narracion[ultimo_fin:match.start()].strip()
                if texto_antes:
                    segmentos.append({
                        "personaje": "Narrador",
                        "texto": texto_antes,
                        "voz": VOCES_POR_PERSONAJE["narrador"],
                        "tipo": "narracion"
                    })

                # El diálogo del personaje
                nombre_personaje = match.group(1).strip()
                texto_dialogo = match.group(2).strip()
                voz = self._obtener_voz(nombre_personaje)

                segmentos.append({
                    "personaje": nombre_personaje,
                    "texto": texto_dialogo,
                    "voz": voz,
                    "tipo": "dialogo"
                })
                ultimo_fin = match.end()

            # Texto después del último diálogo
            texto_despues = texto_narracion[ultimo_fin:].strip()
            if texto_despues:
                segmentos.append({
                    "personaje": "Narrador",
                    "texto": texto_despues,
                    "voz": VOCES_POR_PERSONAJE["narrador"],
                    "tipo": "narracion"
                })

        return segmentos if segmentos else [{
            "personaje": "Narrador",
            "texto": texto_narracion,
            "voz": VOCES_POR_PERSONAJE["default"],
            "tipo": "narracion"
        }]

    def _obtener_voz(self, nombre_personaje: str) -> str:
        """Obtiene la voz edge-tts asignada a un personaje."""
        nombre_norm = nombre_personaje.lower().strip()
        # Búsqueda exacta
        if nombre_norm in VOCES_POR_PERSONAJE:
            return VOCES_POR_PERSONAJE[nombre_norm]
        # Búsqueda parcial
        for clave, voz in VOCES_POR_PERSONAJE.items():
            if clave in nombre_norm or nombre_norm in clave:
                return voz
        return VOCES_POR_PERSONAJE["default"]

    def obtener_voz_principal(self, texto_narracion: str) -> str:
        """
        Para compatibilidad con el sistema actual de una sola voz.
        Retorna la voz del primer personaje que habla (o narrador).
        """
        segmentos = self.parsear_segmentos_voz(texto_narracion)
        if segmentos:
            return segmentos[0]["voz"]
        return VOCES_POR_PERSONAJE["default"]

    def calcular_duracion_texto(self, texto: str, palabras_por_segundo: float = 2.5) -> float:
        """
        Estima la duración en segundos de un texto hablado.
        Promedio: 2.5 palabras/segundo para español.
        Mínimo: 3 segundos. Máximo: 8 segundos.
        """
        num_palabras = len(texto.split())
        duracion = num_palabras / palabras_por_segundo
        return max(3.0, min(8.0, duracion))

    def preparar_escenas_para_ensamblaje(self, escenas: list[dict]) -> list[dict]:
        """
        Pre-procesa las escenas para el ensamblaje final.
        Añade metadatos de audio y transición.
        """
        escenas_prep = []
        for i, escena in enumerate(escenas):
            escena_prep = dict(escena)
            texto = escena.get("texto_narracion", "")

            # Parsear segmentos de voz
            segmentos = self.parsear_segmentos_voz(texto)
            escena_prep["segmentos_audio"] = segmentos
            escena_prep["voz_principal"] = self.obtener_voz_principal(texto)
            escena_prep["tipo_audio"] = self.detectar_tipo_audio(texto)

            # Tipo de transición
            escena_prep["transicion_entrada"] = "fade" if i == 0 else "crossfade"
            escena_prep["transicion_salida"] = "fade" if i == len(escenas) - 1 else "crossfade"

            escenas_prep.append(escena_prep)
            print(f"[ASSEMBLY] 🎬 Escena {escena_prep.get('numero', i+1)}: "
                  f"tipo_audio={escena_prep['tipo_audio']}, "
                  f"voz={escena_prep['voz_principal'].split('-')[1]}, "
                  f"segmentos={len(segmentos)}")

        return escenas_prep


# Instancia global
assembly_agent = AssemblyAgent()
