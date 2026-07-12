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
                
            await db.execute("UPDATE chat_history SET conversacion_id = 'default' WHERE conversacion_id IS NULL")
            await db.execute("INSERT OR IGNORE INTO conversaciones (id, titulo) VALUES ('default', 'Chat Principal')")
            
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


# Instancia global
memoria = MemoriaDB()
