"""
Módulo de Memoria - SQLite para HERMATRON
Almacenamiento persistente de conversaciones y proyectos
"""
import aiosqlite
from datetime import datetime
from typing import Optional
from app.config import DATABASE_PATH


class MemoriaDB:
    """Gestor de memoria con SQLite asíncrono"""
    
    def __init__(self, db_path: str = str(DATABASE_PATH)):
        self.db_path = db_path
        self._initialized = False
    
    async def init(self):
        """Inicializar la base de datos"""
        if self._initialized:
            return
            
        async with aiosqlite.connect(self.db_path) as db:
            # Tabla de historial de chat (con modo y proyecto)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    modo TEXT DEFAULT 'general',
                    proyecto TEXT DEFAULT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabla de proyectos
            await db.execute("""
                CREATE TABLE IF NOT EXISTS proyectos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT UNIQUE NOT NULL,
                    descripcion TEXT,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabla de personajes
            await db.execute("""
                CREATE TABLE IF NOT EXISTS personajes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT UNIQUE NOT NULL,
                    descripcion_fisica TEXT NOT NULL,
                    prompt_referencia TEXT,
                    imagen_path TEXT,
                    voz_edge_tts TEXT DEFAULT 'es-MX-JorgeNeural',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Tabla de escenografías (entornos y fondos)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS escenografias (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT UNIQUE NOT NULL,
                    descripcion TEXT NOT NULL,
                    clima TEXT DEFAULT 'despejado',
                    hora_dia TEXT DEFAULT 'dia',
                    material_suelo TEXT DEFAULT 'asfalto',
                    imagen_path TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabla de configuración
            await db.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            
            # Tabla de conversaciones
            await db.execute("""
                CREATE TABLE IF NOT EXISTS conversaciones (
                    id TEXT PRIMARY KEY,
                    titulo TEXT NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabla de usuarios
            await db.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    plan TEXT DEFAULT 'gratis',
                    videos_creados INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Tabla de sesiones (Login)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sesiones (
                    token TEXT PRIMARY KEY,
                    email TEXT NOT NULL,
                    expires_at DATETIME NOT NULL
                )
            """)
            
            # Y agregar conversacion_id a chat_history
            try:
                await db.execute("ALTER TABLE chat_history ADD COLUMN conversacion_id TEXT DEFAULT 'default'")
            except:
                pass

            # Migración: agregar columna voz_edge_tts si no existe (BD existentes)
            try:
                await db.execute("ALTER TABLE personajes ADD COLUMN voz_edge_tts TEXT DEFAULT 'es-MX-JorgeNeural'")
                print("[DB] ✅ Columna voz_edge_tts agregada a personajes")
            except:
                pass  # Ya existía, no pasa nada

            await db.execute("UPDATE chat_history SET conversacion_id = 'default' WHERE conversacion_id IS NULL")
            await db.execute("INSERT OR IGNORE INTO conversaciones (id, titulo) VALUES ('default', 'Chat Principal')")
            
            # Sembrar personajes por defecto si la tabla está vacía
            async with db.execute("SELECT COUNT(*) FROM personajes") as cursor:
                row = await cursor.fetchone()
                if row and row[0] == 0:
                    personajes_semilla = [
                        (
                            "Julián",
                            "Niño afrocolombiano de raza negra, de 8 años, con suéter amarillo limpio, pelo corto y rizado negro, expresión inocente y alegre.",
                            "8-year-old Afro-Colombian black boy, short curly black hair, innocent expressive face, clean yellow sweater, 3d style",
                            "/static/personajes/Julian.png",
                            "es-CO-GonzaloNeural"    # Voz: niño colombiano
                        ),
                        (
                            "Hamilton",
                            "Joven mestizo y trigeño (mayor que Julián), muy elegante con camisa blanca impecable, ojos claros expresivos de color verde.",
                            "Elegant light-skinned young Colombian boy, neat short dark hair, expressive light green eyes, neat white shirt, 3d style",
                            "/static/personajes/Hamilton.png",
                            "es-MX-JorgeNeural"      # Voz: joven masculino
                        ),
                        (
                            "El Zarco",
                            "Joven mulato/trigeño de mirada intensa con ojos muy claros (celestes), bien vestido con chaqueta oscura moderna, junto a una moto Calima 175 azul.",
                            "Young Colombian mulatto guy, intense light blue eyes, stylish dark jacket, standing next to a classic blue Calima 175 motorcycle, 3d style",
                            "/static/personajes/El_Zarco.png",
                            "es-US-AlonsoNeural"     # Voz: urbano juvenil
                        ),
                        (
                            "Rosalba",
                            "Madre de Julián, mujer de 43 años, afrocolombiana, bonita, elegante, de vestir sobrio y sonrisa maternal, muy sociable.",
                            "43-year-old Afro-Colombian woman, beautiful warm smile, elegant neat hair, modest nice dress, motherly expression, 3d style",
                            "/static/personajes/Rosalba.png",
                            "es-CO-SalomeNeural"     # Voz: femenina colombiana
                        ),
                        (
                            "Carlos",
                            "Padre de Julián, electricista de 45 años, afrocolombiano, contextura trabajadora, reparando neveras en su taller hogareño.",
                            "45-year-old Afro-Colombian man, working class physique, repairing domestic appliances in a home garage, 3d style",
                            "/static/personajes/Carlos.png",
                            "es-ES-AlvaroNeural"     # Voz: masculino maduro
                        ),
                        (
                            "Vanessa",
                            "Hermana mayor de Julián, de 18 años, bonita con piel clara/trigeña y ojos color miel, vistiendo camiseta veraniega y shorts.",
                            "18-year-old Colombian young woman, light brown skin, honey-colored eyes, summer casual clothing, 3d style",
                            "/static/personajes/Vanessa.png",
                            "es-MX-DaliaNeural"      # Voz: femenina joven
                        ),
                        (
                            "Valentina",
                            "Hermana menor de Julián, de 15 años, afrocolombiana de raza negra, vistiendo uniforme escolar limpio de la escuela Gabriel García Márquez.",
                            "15-year-old Afro-Colombian schoolgirl, wearing a neat school uniform, holding notebooks, 3d style",
                            "/static/personajes/Valentina.png",
                            "es-MX-DaliaNeural"      # Voz: femenina adolescente
                        ),
                        (
                            "Don Nelson",
                            "Vecino de 55 años, misterioso, de tez madura, parado junto a una puerta vieja de madera tallada de lujo, vistiendo camisa a cuadros, gafas y anillo de sello grande.",
                            "55-year-old mature Colombian man, wearing a plaid shirt, reading glasses, large signet ring, standing next to a luxurious weathered old wooden door, 3d style",
                            "/static/personajes/Don_Nelson.png",
                            "es-ES-AlvaroNeural"     # Voz: masculino mayor
                        )
                    ]
                    await db.executemany("""
                        INSERT INTO personajes (nombre, descripcion_fisica, prompt_referencia, imagen_path, voz_edge_tts)
                        VALUES (?, ?, ?, ?, ?)
                    """, personajes_semilla)

            # Sembrar escenografías por defecto si la tabla está vacía
            async with db.execute("SELECT COUNT(*) FROM escenografias") as cursor:
                row = await cursor.fetchone()
                if row and row[0] == 0:
                    escenografias_semilla = [
                        (
                            "Esquina",
                            "Una típica esquina de un barrio de bajos recursos, con un poste de luz de energía que tiene cables enredados, una lámpara de sodio con iluminación cálida de color naranja y paredes de ladrillo expuesto.",
                            "nublado",
                            "noche",
                            "pavimento",
                            "/static/escenografias/esquina.png"
                        ),
                        (
                            "La Tienda",
                            "Una tradicional tienda de barrio, con vitrinas de madera llenas de productos de consumo local, estanterías con latas y arroz, y una vieja nevera de Coca-Cola en la esquina.",
                            "despejado",
                            "dia",
                            "baldosas",
                            "/static/escenografias/tienda.png"
                        ),
                        (
                            "Taller de Carlos",
                            "Un pequeño taller doméstico improvisado en un garaje abierto. Hay herramientas de refrigeración, cables, pinzas y repuestos de neveras en estantes rústicos de madera.",
                            "despejado",
                            "dia",
                            "cemento",
                            "/static/escenografias/taller.png"
                        )
                    ]
                    await db.executemany("""
                        INSERT INTO escenografias (nombre, descripcion, clima, hora_dia, material_suelo, imagen_path)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, escenografias_semilla)

            await db.commit()
        self._initialized = True
    
    async def agregar_mensaje(self, role: str, content: str, modo: str = "general", proyecto: str = None, conversacion_id: str = "default"):
        """Guardar un mensaje en el historial con modo y proyecto"""
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE conversaciones SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (conversacion_id,))
            await db.execute(
                "INSERT INTO chat_history (role, content, modo, proyecto, conversacion_id) VALUES (?, ?, ?, ?, ?)",
                (role, content, modo, proyecto, conversacion_id)
            )
            await db.commit()
    
    async def obtener_historial(self, limit: int = 50, modo: str = None, conversacion_id: str = "default") -> list[dict]:
        """Obtener últimos mensajes del historial, opcionalmente filtrados por modo"""
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if modo:
                async with db.execute(
                    "SELECT role, content, modo, proyecto, timestamp FROM chat_history WHERE modo = ? AND conversacion_id = ? ORDER BY id DESC LIMIT ?",
                    (modo, conversacion_id, limit)
                ) as cursor:
                    rows = await cursor.fetchall()
            else:
                async with db.execute(
                    "SELECT role, content, modo, proyecto, timestamp FROM chat_history WHERE conversacion_id = ? ORDER BY id DESC LIMIT ?",
                    (conversacion_id, limit)
                ) as cursor:
                    rows = await cursor.fetchall()
            return [
                {"role": row["role"], "content": row["content"], "modo": row["modo"], "proyecto": row["proyecto"], "timestamp": row["timestamp"]}
                for row in reversed(rows)
            ]
    
    async def limpiar_historial(self, modo: str = None, conversacion_id: str = "default"):
        """Borrar historial de chat, opcionalmente solo de un modo específico"""
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            if modo:
                await db.execute("DELETE FROM chat_history WHERE modo = ? AND conversacion_id = ?", (modo, conversacion_id))
            else:
                await db.execute("DELETE FROM chat_history WHERE conversacion_id = ?", (conversacion_id,))
            await db.commit()
    
    async def crear_conversacion(self, id: str, titulo: str):
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT OR IGNORE INTO conversaciones (id, titulo) VALUES (?, ?)", (id, titulo))
            await db.commit()

    async def obtener_conversaciones(self) -> list[dict]:
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM conversaciones ORDER BY updated_at DESC") as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def eliminar_conversacion(self, id: str):
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM conversaciones WHERE id = ?", (id,))
            await db.execute("DELETE FROM chat_history WHERE conversacion_id = ?", (id,))
            await db.commit()

    # --- Gestión de Usuarios ---
    
    async def crear_usuario(self, email: str, password_hash: str) -> bool:
        """Crea un nuevo usuario. Retorna True si tuvo éxito, False si el email ya existe."""
        await self.init()
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "INSERT INTO usuarios (email, password_hash) VALUES (?, ?)",
                    (email, password_hash)
                )
                await db.commit()
                return True
        except aiosqlite.IntegrityError:
            return False

    async def obtener_usuario(self, email: str) -> Optional[dict]:
        """Obtiene un usuario por su email."""
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM usuarios WHERE email = ?", (email,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def incrementar_video_uso(self, email: str) -> int:
        """Incrementa el contador de videos y retorna el nuevo valor."""
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            await db.execute("UPDATE usuarios SET videos_creados = videos_creados + 1 WHERE email = ?", (email,))
            await db.commit()
            async with db.execute("SELECT videos_creados FROM usuarios WHERE email = ?", (email,)) as cursor:
                row = await cursor.fetchone()
                return row["videos_creados"] if row else 0
            
    async def guardar_proyecto(self, nombre: str, descripcion: str = "", metadata: dict = None):
        """Guardar o actualizar un proyecto"""
        await self.init()
        import json
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO proyectos (nombre, descripcion, metadata, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (nombre, descripcion, json.dumps(metadata or {})))
            await db.commit()
    
    async def obtener_proyecto(self, nombre: str) -> Optional[dict]:
        """Obtener información de un proyecto"""
        await self.init()
        import json
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM proyectos WHERE nombre = ?", (nombre,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        "nombre": row["nombre"],
                        "descripcion": row["descripcion"],
                        "metadata": json.loads(row["metadata"]),
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"]
                    }
                return None
    
    async def obtener_todos_proyectos(self) -> list[dict]:
        """Obtener lista de todos los proyectos"""
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM proyectos ORDER BY updated_at DESC") as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def contar_mensajes(self, conversacion_id: str = "default") -> int:
        """Contar total de mensajes en el historial"""
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM chat_history WHERE conversacion_id = ?", (conversacion_id,)) as cursor:
                result = await cursor.fetchone()
                return result[0]

    async def exportar_historial(self, formato: str = "json", modo: str = None, conversacion_id: str = "default") -> str:
        """Exportar historial de chat a JSON o CSV"""
        import json
        import csv
        import io
        from datetime import datetime

        historial = await self.obtener_historial(modo=modo, conversacion_id=conversacion_id)

        if formato == "json":
            return json.dumps(historial, indent=2, ensure_ascii=False)
        elif formato == "csv":
            output = io.StringIO()
            if historial:
                writer = csv.DictWriter(output, fieldnames=["timestamp", "role", "content", "modo", "proyecto"])
                writer.writeheader()
                writer.writerows(historial)
            return output.getvalue()
        else:
            return json.dumps(historial, indent=2, ensure_ascii=False)

    async def guardar_personaje(self, nombre: str, descripcion_fisica: str, prompt_referencia: str, imagen_path: str = None):
        """Guardar o actualizar un personaje"""
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO personajes (nombre, descripcion_fisica, prompt_referencia, imagen_path)
                VALUES (?, ?, ?, ?)
            """, (nombre, descripcion_fisica, prompt_referencia, imagen_path))
            await db.commit()

    async def obtener_personaje(self, nombre: str) -> Optional[dict]:
        """Obtener un personaje por su nombre"""
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM personajes WHERE nombre = ?", (nombre,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def obtener_todos_personajes(self) -> list[dict]:
        """Obtener todos los personajes de la base de datos"""
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM personajes ORDER BY nombre ASC") as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def eliminar_personaje(self, nombre: str):
        """Eliminar un personaje"""
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM personajes WHERE nombre = ?", (nombre,))
            await db.commit()

    async def actualizar_voz_personaje(self, nombre: str, voz_edge_tts: str):
        """Actualizar la voz edge-tts asignada a un personaje"""
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE personajes SET voz_edge_tts = ? WHERE nombre = ?",
                (voz_edge_tts, nombre)
            )
            await db.commit()
            print(f"[DB] 🎙️ Voz de '{nombre}' actualizada a: {voz_edge_tts}")

    async def guardar_escenografia(self, nombre: str, descripcion: str, clima: str = "despejado", hora_dia: str = "dia", material_suelo: str = "asfalto", imagen_path: str = None):
        """Guardar o actualizar una escenografía/entorno de fondo"""
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO escenografias (nombre, descripcion, clima, hora_dia, material_suelo, imagen_path)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (nombre, descripcion, clima, hora_dia, material_suelo, imagen_path))
            await db.commit()
            print(f"[DB] 🏞️ Escenografía '{nombre}' guardada/actualizada")

    async def obtener_escenografia(self, nombre: str) -> Optional[dict]:
        """Obtener una escenografía por su nombre"""
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM escenografias WHERE nombre = ?", (nombre,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def obtener_todas_escenografias(self) -> list[dict]:
        """Obtener todas las escenografías de la base de datos"""
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM escenografias ORDER BY nombre ASC") as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def eliminar_escenografia(self, nombre: str):
        """Eliminar una escenografía"""
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM escenografias WHERE nombre = ?", (nombre,))
            await db.commit()
            print(f"[DB] 🗑️ Escenografía '{nombre}' eliminada")


# Instancia global
memoria = MemoriaDB()
