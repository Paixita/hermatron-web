"""
🎨 Style Agent — Detección Automática de Estilo Visual
Inspirado en repositorios de prompts de GitHub (awesome-stable-diffusion-prompts).

Detecta automáticamente si el usuario quiere:
  - 🎬 Cinematográfico (live action por defecto)
  - 🧊 3D Animado (Pixar/Disney style)
  - 🌸 Anime (Studio Ghibli / Makoto Shinkai)
  - 🎨 Caricatura (DreamWorks / cartoon)
  - 📸 Realista (fotografía documental)

Y aplica los prompts técnicos correctos para cada estilo.
"""
import re
import unicodedata


def normalizar(texto: str) -> str:
    """Quita tildes y pasa a minúsculas para comparaciones."""
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    ).lower()


# ── Biblioteca de Estilos (inspirada en awesome-stable-diffusion-prompts) ────

ESTILOS = {

    # ── 3D ANIMADO (Pixar / Disney) ──────────────────────────────────────────
    "3d_animado": {
        "nombre": "3D Animado",
        "emoji": "🧊",
        "keywords": [
            "3d", "tres dimensiones", "pixar", "disney", "animacion 3d",
            "animado 3d", "3d style", "render 3d", "cgi"
        ],
        # Prompt prefix de alta calidad para Pixar/3D — basado en research GitHub
        "prompt_prefix": (
            "Pixar 3D animation style, high-end CGI, "
            "expressive stylized characters, smooth subsurface scattering on skin, "
            "vibrant saturated colors, cinematic rim lighting, "
            "shallow depth of field, 85mm lens, "
            "detailed hair strands, oversized expressive eyes, "
            "Disney/Pixar aesthetic, 4K render, masterwork"
        ),
        # Negative prompt — evita el uncanny valley
        "prompt_negativo": (
            "photorealistic, hyperrealistic, ugly, deformed, "
            "bad anatomy, uncanny valley, scary, dark, grim, "
            "low quality, blurry, noisy, flat colors"
        ),
        # Instrucción para el LLM al generar escenas
        "instruccion_llm": (
            "STYLE: Generate all visual descriptions in high-end Pixar 3D animation style. "
            "Characters must have expressive oversized eyes, smooth stylized skin, "
            "vibrant colors, and cinematic lighting. "
            "Describe every character as a beautifully rendered 3D CGI character."
        )
    },

    # ── ANIME (Studio Ghibli / Makoto Shinkai) ────────────────────────────────
    "anime": {
        "nombre": "Anime",
        "emoji": "🌸",
        "keywords": [
            "anime", "ghibli", "studio ghibli", "manga", "japones", "japanese",
            "makoto shinkai", "shinkai", "cel shading", "animacion japonesa",
            "animacion anime"
        ],
        # Prompt prefix detallado para anime/Ghibli — basado en research GitHub
        "prompt_prefix": (
            "Studio Ghibli anime style, hand-drawn cel animation, "
            "soft watercolor textures, gouache background painting, "
            "traditional Japanese illustration, warm nostalgic color palette, "
            "golden hour sunlight, intricate foliage details, "
            "1990s anime film still quality, masterpiece, high quality"
        ),
        "prompt_negativo": (
            "photorealistic, 3d render, plastic, neon, harsh shadows, "
            "low quality, blurry, distorted, messy, deformed, "
            "digital art, sharp edges, western cartoon"
        ),
        "instruccion_llm": (
            "STYLE: Generate all visual descriptions in Studio Ghibli anime style. "
            "Use hand-drawn cel animation aesthetic, soft watercolor backgrounds, "
            "warm nostalgic lighting. Characters should have anime-style expressive faces, "
            "detailed hair, and be placed in beautifully painted environments."
        )
    },

    # ── CARICATURA / CARTOON ──────────────────────────────────────────────────
    "caricatura": {
        "nombre": "Caricatura",
        "emoji": "🎨",
        "keywords": [
            "caricatura", "cartoon", "dibujos animados", "dreamworks",
            "toon", "ilustracion", "comic", "caricaturas"
        ],
        "prompt_prefix": (
            "vibrant cartoon illustration style, DreamWorks animation, "
            "bold outlines, flat cel shading, bright saturated colors, "
            "exaggerated proportions, fun stylized characters, "
            "clean vector art aesthetic, children's animation quality"
        ),
        "prompt_negativo": (
            "photorealistic, dark, grim, scary, uncanny valley, "
            "low quality, blurry, messy lines"
        ),
        "instruccion_llm": (
            "STYLE: Generate all visual descriptions in vibrant cartoon/caricature style. "
            "Bold outlines, exaggerated fun proportions, bright colors. "
            "Think DreamWorks or Cartoon Network aesthetic."
        )
    },

    # ── REALISTA / DOCUMENTAL ─────────────────────────────────────────────────
    "realista": {
        "nombre": "Realista",
        "emoji": "📸",
        "keywords": [
            "realista", "real", "documental", "fotografico", "fotografia",
            "live action", "hiperealista", "fotorrealista"
        ],
        "prompt_prefix": (
            "hyper-realistic photography, cinematic shot, "
            "shot on Sony A7R, 85mm lens, bokeh depth of field, "
            "natural lighting, documentary style, 8K resolution, "
            "high detail textures, professional photography"
        ),
        "prompt_negativo": (
            "cartoon, anime, 3d render, painted, illustrated, "
            "low quality, blurry, distorted"
        ),
        "instruccion_llm": (
            "STYLE: Generate all visual descriptions as hyper-realistic photography. "
            "Cinematic shots with natural lighting, bokeh depth of field. "
            "Describe scenes as if shot on a professional cinema camera."
        )
    },

    # ── CINEMATOGRÁFICO (por defecto) ─────────────────────────────────────────
    "cinematografico": {
        "nombre": "Cinematográfico",
        "emoji": "🎬",
        "keywords": [],  # Default — no necesita keywords
        "prompt_prefix": (
            "cinematic shot, dramatic lighting, "
            "anamorphic lens, shallow depth of field, "
            "film grain, professional color grading, "
            "8K resolution, masterwork"
        ),
        "prompt_negativo": (
            "low quality, blurry, distorted, amateur, flat lighting"
        ),
        "instruccion_llm": (
            "STYLE: Generate all visual descriptions with cinematic quality. "
            "Dramatic lighting, professional camera angles, film-quality aesthetics."
        )
    }
}


class StyleAgent:
    """
    Agente de Detección de Estilo Visual.

    Analiza el prompt del usuario y detecta automáticamente
    qué estilo visual usar para las imágenes del video.
    """

    def detectar_estilo(self, prompt_usuario: str, tema: str = "") -> dict:
        """
        Detecta el estilo visual a partir del prompt y tema del usuario.

        Returns: dict del estilo detectado con 'id', 'nombre', 'prompt_prefix', etc.
        """
        texto_completo = normalizar(prompt_usuario + " " + tema)

        for estilo_id, datos in ESTILOS.items():
            if estilo_id == "cinematografico":
                continue  # Es el default, lo chequeamos al final
            for keyword in datos["keywords"]:
                if normalizar(keyword) in texto_completo:
                    print(f"[STYLE AGENT] 🎨 Estilo detectado: {datos['emoji']} {datos['nombre']} "
                          f"(keyword: '{keyword}')")
                    return {"id": estilo_id, **datos}

        # Default
        print(f"[STYLE AGENT] 🎬 Estilo por defecto: Cinematográfico")
        return {"id": "cinematografico", **ESTILOS["cinematografico"]}

    def get_prompt_prefix(self, estilo_id: str) -> str:
        """Retorna el prompt prefix para un estilo dado."""
        return ESTILOS.get(estilo_id, ESTILOS["cinematografico"])["prompt_prefix"]

    def get_instruccion_llm(self, estilo_id: str) -> str:
        """Retorna la instrucción para el LLM al generar escenas en este estilo."""
        return ESTILOS.get(estilo_id, ESTILOS["cinematografico"])["instruccion_llm"]

    def get_prompt_negativo(self, estilo_id: str) -> str:
        """Retorna el negative prompt para evitar artefactos de estilo."""
        return ESTILOS.get(estilo_id, ESTILOS["cinematografico"])["prompt_negativo"]

    def listar_estilos(self) -> list[dict]:
        """Retorna todos los estilos disponibles para la UI."""
        return [
            {
                "id": eid,
                "nombre": datos["nombre"],
                "emoji": datos["emoji"],
                "keywords_ejemplo": datos["keywords"][:3] if datos["keywords"] else ["por defecto"]
            }
            for eid, datos in ESTILOS.items()
        ]


# Instancia global
style_agent = StyleAgent()
