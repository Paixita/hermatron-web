import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Request, Response, HTTPException, status
from app.memoria import memoria

# --- CONFIGURACIÓN ---
# Tiempo de expiración de sesión (días)
SESSION_DAYS = 7
# Nombre de la cookie
COOKIE_NAME = "hermatron_session"

# --- FUNCIONES DE HASHEO ---
def hash_password(password: str, salt: str = None) -> str:
    """Hashea una contraseña con SHA-256 y un salt aleatorio."""
    if not salt:
        salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return f"{salt}${pwd_hash.hex()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si la contraseña plana coincide con el hash."""
    try:
        salt, _ = hashed_password.split('$')
        return hash_password(plain_password, salt) == hashed_password
    except ValueError:
        return False

# --- GESTIÓN DE SESIONES EN SQLITE ---
async def create_session(email: str) -> str:
    """Crea un token de sesión seguro y lo guarda en la base de datos."""
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=SESSION_DAYS)
    
    await memoria.init()
    import aiosqlite
    async with aiosqlite.connect(memoria.db_path) as db:
        # Primero eliminamos sesiones antiguas de este usuario
        await db.execute("DELETE FROM sesiones WHERE email = ?", (email,))
        await db.execute(
            "INSERT INTO sesiones (token, email, expires_at) VALUES (?, ?, ?)",
            (token, email, expires_at.isoformat())
        )
        await db.commit()
    return token

async def get_user_from_session(request: Request) -> Optional[dict]:
    """Obtiene el usuario actual a partir de la cookie de sesión."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None

    await memoria.init()
    import aiosqlite
    async with aiosqlite.connect(memoria.db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT email, expires_at FROM sesiones WHERE token = ?", (token,)
        ) as cursor:
            row = await cursor.fetchone()
            
            if not row:
                return None
                
            expires_at = datetime.fromisoformat(row["expires_at"])
            if datetime.utcnow() > expires_at:
                # Sesión expirada
                await db.execute("DELETE FROM sesiones WHERE token = ?", (token,))
                await db.commit()
                return None
                
            email = row["email"]
            
        # Obtenemos los datos completos del usuario
        async with db.execute("SELECT id, email, plan, videos_creados FROM usuarios WHERE email = ?", (email,)) as cursor:
            user_row = await cursor.fetchone()
            return dict(user_row) if user_row else None

async def login_user(response: Response, email: str, password: str) -> bool:
    """Verifica credenciales, crea sesión y setea la cookie."""
    user = await memoria.obtener_usuario(email)
    if not user or not verify_password(password, user["password_hash"]):
        return False
        
    token = await create_session(email)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=SESSION_DAYS * 24 * 60 * 60,
        httponly=True,  # Protege contra XSS
        samesite='lax'
    )
    return True

async def logout_user(response: Response, request: Request):
    """Elimina la sesión actual de la DB y limpia la cookie."""
    token = request.cookies.get(COOKIE_NAME)
    if token:
        await memoria.init()
        import aiosqlite
        async with aiosqlite.connect(memoria.db_path) as db:
            await db.execute("DELETE FROM sesiones WHERE token = ?", (token,))
            await db.commit()
            
    response.delete_cookie(COOKIE_NAME)

def get_current_user():
    """Dependencia de FastAPI para obtener el usuario actual. Retorna None si no hay sesión."""
    async def deps(request: Request) -> Optional[dict]:
        from app.config import HERMATRON_ADMIN_MODE
        if HERMATRON_ADMIN_MODE:
            # En modo admin local, se bypassea el login devolviendo un usuario falso super-admin
            return {"email": "admin@local", "plan": "pro_ilimitado", "videos_creados": 0}
            
        user = await get_user_from_session(request)
        if user and user.get("email") == "fieraintro@gmail.com":
            # Llave maestra para el dueño del proyecto
            user["plan"] = "pro_ilimitado"
            
        return user
    return deps
