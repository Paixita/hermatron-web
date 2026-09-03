"""
HERMATRON v6.2 — Servicios Avanzados del Agente
================================================
Nuevas facultades para la IA interna, 100% gratuitas y con código abierto:

1. 📁 SISTEMA DE ARCHIVOS DEL PC: listar carpetas, leer/escribir archivos,
   crear/copiar/mover/eliminar y buscar archivos (solo stdlib de Python).
2. 🐙 GITHUB: buscar repos, leer código de cualquier repo público, listar
   contenido y descargar repos (API REST gratuita, sin token requerido).
3. 🧠 BASE DE CONOCIMIENTO: memoria permanente actualizable — HERMATRON puede
   guardar, buscar y refrescar conocimiento desde la web/GitHub.
4. 🩺 AUTO-REPARACIÓN (modo propose-only): diagnóstico de errores y propuesta
   de parche sobre su propio código. NUNCA aplica cambios sin aprobación.

Seguridad:
- Las operaciones destructivas protegen rutas críticas del sistema.
- El auto-arreglo SOLO propone (modo seguro por defecto).
- GitHub usa la API pública gratuita (GITHUB_TOKEN opcional en .env).
"""

import os
import io
import re
import json
import shutil
import zipfile
from pathlib import Path
from typing import Optional

import httpx

from app.config import BASE_DIR, GITHUB_TOKEN, ALLOW_FILE_ACCESS

# ─────────────────────────────────────────────────────────────────────────────
# UTILIDADES DE SEGURIDAD
# ─────────────────────────────────────────────────────────────────────────────

_RUTAS_CRITICAS_PROTEGIDAS = (
    "hermatron.db",
    ".venv",
    "venv",
    ".env",
    ".git",
)


def _rutas_protegidas_absolutas() -> list[Path]:
    """Rutas que nunca se deben eliminar/sobrescribir (integridad de HERMATRON)."""
    rutas = [
        Path.home(),
        Path.home() / "Desktop",
        Path.home() / "Escritorio",
        BASE_DIR,
    ]
    for nombre in _RUTAS_CRITICAS_PROTEGIDAS:
        rutas.append(BASE_DIR / nombre)
    return rutas


def _es_ruta_protegida(ruta: Path, para_eliminar: bool = False) -> bool:
    """True si la ruta es crítica o (para eliminación) es la raíz del sistema."""
    try:
        ruta_resuelta = ruta.resolve()
    except Exception:
        ruta_resuelta = ruta.absolute()
    for protegida in _rutas_protegidas_absolutas():
        try:
            if ruta_resuelta == protegida.resolve():
                return True
        except Exception:
            pass
    # Nunca permitir eliminar la raíz de un disco o la carpeta de inicio
    if para_eliminar:
        if ruta_resuelta == Path(ruta_resuelta.anchor):
            return True
    return False


def _limpiar_ruta(ruta: str) -> Path:
    """Normaliza una ruta y expande variables del sistema (~, %USERPROFILE%)."""
    ruta = (ruta or "").strip().strip('"').strip("'")
    if not ruta:
        raise ValueError("Ruta vacía.")
    ruta = os.path.expandvars(os.path.expanduser(ruta))
    return Path(ruta)


def _formatear_tamano(num_bytes: int) -> str:
    if num_bytes < 1024:
        return f"{num_bytes} B"
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    if num_bytes < 1024 * 1024 * 1024:
        return f"{num_bytes / (1024 * 1024):.1f} MB"
    return f"{num_bytes / (1024 * 1024 * 1024):.2f} GB"


# ─────────────────────────────────────────────────────────────────────────────
# 1. SISTEMA DE ARCHIVOS DEL PC
# ─────────────────────────────────────────────────────────────────────────────

def listar_carpeta(ruta: str = str(BASE_DIR), max_items: int = 200) -> dict:
    """Lista el contenido de una carpeta (archivos y subcarpetas)."""
    try:
        p = _limpiar_ruta(ruta)
        if not p.exists():
            return {"status": "error", "mensaje": f"La ruta no existe: {p}"}
        if not p.is_dir():
            return {"status": "error", "mensaje": f"No es una carpeta: {p}"}

        entradas = []
        for item in sorted(p.iterdir()):
            if len(entradas) >= max_items:
                entradas.append({"nombre": "...", "tipo": "truncado", "nota": f"límite de {max_items} elementos"})
                break
            try:
                es_dir = item.is_dir()
                stat = item.stat()
                entradas.append({
                    "nombre": item.name,
                    "tipo": "carpeta" if es_dir else "archivo",
                    "tamano": "-" if es_dir else _formatear_tamano(stat.st_size),
                    "modificado": __import__("time").strftime("%Y-%m-%d %H:%M", __import__("time").localtime(stat.st_mtime)),
                })
            except Exception:
                entradas.append({"nombre": item.name, "tipo": "desconocido"})

        return {
            "status": "success",
            "ruta": str(p),
            "es_raiz": True,
            "elementos": entradas,
            "total": len(entradas),
        }
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}


def leer_archivo(ruta: str, max_lineas: int = 300) -> dict:
    """Lee el contenido de un archivo de texto (con límite de líneas)."""
    try:
        p = _limpiar_ruta(ruta)
        if not p.exists():
            return {"status": "error", "mensaje": f"El archivo no existe: {p}"}
        if not p.is_file():
            return {"status": "error", "mensaje": f"No es un archivo: {p}"}

        max_lineas = int(max_lineas or 300)
        max_lineas = max(1, min(max_lineas, 2000))
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            lineas = []
            for i, linea in enumerate(f):
                if i >= max_lineas:
                    lineas.append(f"... (archivo truncado a {max_lineas} líneas)")
                    break
                lineas.append(linea.rstrip("\n"))

        return {
            "status": "success",
            "ruta": str(p),
            "lineas": len(lineas),
            "contenido": "\n".join(lineas),
        }
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}


def escribir_archivo(ruta: str, contenido: str) -> dict:
    """Crea o sobrescribe un archivo con el contenido dado (crea carpetas si falta)."""
    if not ALLOW_FILE_ACCESS:
        return {"status": "error", "mensaje": "ALLOW_FILE_ACCESS=False: la escritura de archivos está desactivada."}
    try:
        p = _limpiar_ruta(ruta)
        if _es_ruta_protegida(p):
            return {"status": "error", "mensaje": f"La ruta está protegida (integridad de HERMATRON): {p}"}
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(contenido or "")
        return {"status": "success", "ruta": str(p), "mensaje": "Archivo escrito correctamente."}
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}


def crear_carpeta(ruta: str) -> dict:
    """Crea una carpeta (y sus carpetas padre si es necesario)."""
    if not ALLOW_FILE_ACCESS:
        return {"status": "error", "mensaje": "ALLOW_FILE_ACCESS=False: crear carpetas está desactivado."}
    try:
        p = _limpiar_ruta(ruta)
        p.mkdir(parents=True, exist_ok=True)
        return {"status": "success", "ruta": str(p), "mensaje": "Carpeta creada correctamente."}
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}


def copiar_elemento(origen: str, destino: str) -> dict:
    """Copia un archivo o carpeta a otra ubicación."""
    if not ALLOW_FILE_ACCESS:
        return {"status": "error", "mensaje": "ALLOW_FILE_ACCESS=False: copiar está desactivado."}
    try:
        src = _limpiar_ruta(origen)
        dst = _limpiar_ruta(destino)
        if not src.exists():
            return {"status": "error", "mensaje": f"El origen no existe: {src}"}
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        return {"status": "success", "origen": str(src), "destino": str(dst), "mensaje": "Copia completada."}
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}


def mover_elemento(origen: str, destino: str) -> dict:
    """Mueve o renombra un archivo/carpeta."""
    if not ALLOW_FILE_ACCESS:
        return {"status": "error", "mensaje": "ALLOW_FILE_ACCESS=False: mover/renombrar está desactivado."}
    try:
        src = _limpiar_ruta(origen)
        dst = _limpiar_ruta(destino)
        if not src.exists():
            return {"status": "error", "mensaje": f"El origen no existe: {src}"}
        if _es_ruta_protegida(src) or _es_ruta_protegida(dst):
            return {"status": "error", "mensaje": "Una de las rutas está protegida (integridad de HERMATRON)."}
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        return {"status": "success", "origen": str(src), "destino": str(dst), "mensaje": "Movido correctamente."}
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}


def eliminar_elemento(ruta: str, es_carpeta: bool = False) -> dict:
    """Elimina un archivo o carpeta (protegiendo rutas críticas)."""
    if not ALLOW_FILE_ACCESS:
        return {"status": "error", "mensaje": "ALLOW_FILE_ACCESS=False: eliminar está desactivado."}
    try:
        p = _limpiar_ruta(ruta)
        if not p.exists():
            return {"status": "error", "mensaje": f"La ruta no existe: {p}"}
        if _es_ruta_protegida(p, para_eliminar=True):
            return {"status": "error", "mensaje": f"Ruta protegida, no puedo eliminarla: {p}"}

        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
        else:
            p.unlink()
        return {"status": "success", "ruta": str(p), "mensaje": "Elemento eliminado."}
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}


def buscar_archivos(ruta: str = str(BASE_DIR), patron: str = "*", max_resultados: int = 50) -> dict:
    """Busca archivos/carpetas recursivamente por nombre (patrón glob, ej: '*.py', 'video*')."""
    try:
        p = _limpiar_ruta(ruta)
        if not p.exists():
            return {"status": "error", "mensaje": f"La ruta no existe: {p}"}

        patron = (patron or "*").strip()
        max_resultados = int(max_resultados or 50)
        max_resultados = max(1, min(max_resultados, 200))

        resultados = []
        for item in p.rglob(patron):
            try:
                resultados.append({
                    "ruta": str(item.relative_to(p)),
                    "tipo": "carpeta" if item.is_dir() else "archivo",
                    "tamano": "-" if item.is_dir() else _formatear_tamano(item.stat().st_size),
                })
            except Exception:
                pass
            if len(resultados) >= max_resultados:
                break

        return {
            "status": "success",
            "carpeta_base": str(p),
            "patron": patron,
            "resultados": resultados,
            "total": len(resultados),
        }
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}


def info_ruta(ruta: str) -> dict:
    """Información detallada de un archivo o carpeta (tamaño, fechas, tipo)."""
    try:
        p = _limpiar_ruta(ruta)
        if not p.exists():
            return {"status": "error", "mensaje": f"La ruta no existe: {p}"}
        stat = p.stat()
        import time as _time
        return {
            "status": "success",
            "ruta": str(p),
            "absoluta": str(p.resolve()),
            "tipo": "carpeta" if p.is_dir() else "archivo",
            "tamano": _formatear_tamano(stat.st_size),
            "tamano_bytes": stat.st_size,
            "creado": _time.strftime("%Y-%m-%d %H:%M:%S", _time.localtime(stat.st_ctime)),
            "modificado": _time.strftime("%Y-%m-%d %H:%M:%S", _time.localtime(stat.st_mtime)),
            "extension": p.suffix,
            "carpeta_padre": str(p.parent),
        }
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# 2. GITHUB (API pública gratuita)
# ─────────────────────────────────────────────────────────────────────────────

_GH_API = "https://api.github.com"
_GH_RAW = "https://raw.githubusercontent.com"
_GH_DL = "https://codeload.github.com"


def _gh_headers() -> dict:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "HERMATRON-Agent"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


async def github_buscar_repos(query: str, max_resultados: int = 10) -> dict:
    """Busca repositorios públicos en GitHub (API gratuita)."""
    try:
        if not query or not query.strip():
            return {"status": "error", "mensaje": "Consulta vacía."}
        max_resultados = int(max_resultados or 10)
        max_resultados = max(1, min(max_resultados, 30))
        async with httpx.AsyncClient(timeout=20) as cliente:
            resp = await cliente.get(
                f"{_GH_API}/search/repositories",
                params={"q": query, "per_page": max_resultados, "sort": "stars"},
                headers=_gh_headers(),
            )
            if resp.status_code == 403:
                return {"status": "error", "mensaje": "Límite de la API de GitHub alcanzado (gratis). Espera un minuto o agrega GITHUB_TOKEN en .env."}
            if resp.status_code != 200:
                return {"status": "error", "mensaje": f"GitHub respondió {resp.status_code}: {resp.text[:300]}"}
            data = resp.json()
            repos = []
            for r in data.get("items", [])[:max_resultados]:
                repos.append({
                    "nombre": r.get("full_name", ""),
                    "descripcion": (r.get("description") or "")[:300],
                    "estrellas": r.get("stargazers_count", 0),
                    "lenguaje": r.get("language"),
                    "actualizado": r.get("updated_at", ""),
                    "url": r.get("html_url", ""),
                    "rama_default": r.get("default_branch", "main"),
                })
            return {"status": "success", "consulta": query, "total_github": data.get("total_count", 0), "repos": repos}
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}


async def github_leer_archivo(repo: str, ruta: str, rama: str = "main") -> dict:
    """Lee el contenido de un archivo de cualquier repo público de GitHub."""
    try:
        repo = (repo or "").strip().strip("/")
        ruta = (ruta or "").strip().strip("/")
        rama = (rama or "main").strip().strip("/")
        if "/" not in repo:
            return {"status": "error", "mensaje": "Formato de repo inválido. Usa 'usuario/repo' (ej: 'openai/whisper')."}
        if not ruta:
            return {"status": "error", "mensaje": "Indica la ruta del archivo dentro del repo."}

        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as cliente:
            resp = await cliente.get(f"{_GH_RAW}/{repo}/{rama}/{ruta}", headers={"User-Agent": "HERMATRON-Agent"})
            if resp.status_code == 404:
                return {"status": "error", "mensaje": f"No encontré '{ruta}' en {repo} (rama {rama}). Verifica la ruta o intenta otra rama."}
            if resp.status_code != 200:
                return {"status": "error", "mensaje": f"GitHub respondió {resp.status_code}."}

        contenido = resp.text
        lineas = contenido.count("\n") + 1
        if len(contenido) > 60000:
            contenido = contenido[:60000] + "\n... (contenido truncado a 60 KB)"

        return {
            "status": "success",
            "repo": repo,
            "ruta": ruta,
            "rama": rama,
            "lineas": lineas,
            "tamano": _formatear_tamano(len(contenido.encode("utf-8"))),
            "contenido": contenido,
        }
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}


async def github_listar_contenido(repo: str, ruta: str = "", rama: str = "main") -> dict:
    """Lista el contenido (archivos y carpetas) de un repo o subcarpeta."""
    try:
        repo = (repo or "").strip().strip("/")
        ruta = (ruta or "").strip().strip("/")
        rama = (rama or "main").strip().strip("/")
        if "/" not in repo:
            return {"status": "error", "mensaje": "Formato de repo inválido. Usa 'usuario/repo'."}

        async with httpx.AsyncClient(timeout=20) as cliente:
            resp = await cliente.get(
                f"{_GH_API}/repos/{repo}/contents/{ruta}",
                params={"ref": rama},
                headers=_gh_headers(),
            )
            if resp.status_code == 403:
                return {"status": "error", "mensaje": "Límite de la API de GitHub alcanzado. Espera o agrega GITHUB_TOKEN en .env."}
            if resp.status_code == 404:
                return {"status": "error", "mensaje": f"No encontré '{ruta}' en {repo} (rama {rama})."}
            if resp.status_code != 200:
                return {"status": "error", "mensaje": f"GitHub respondió {resp.status_code}."}

            data = resp.json()
            if isinstance(data, list):
                elementos = [
                    {"nombre": e.get("name", ""), "tipo": e.get("type", ""), "tamano": e.get("size", 0)}
                    for e in data
                ]
                return {"status": "success", "repo": repo, "ruta": ruta or "/", "elementos": elementos, "total": len(elementos)}
            if isinstance(data, dict):
                return {"status": "success", "repo": repo, "ruta": ruta, "archivo": data.get("name"), "tamano": data.get("size"), "descarga": data.get("download_url")}
            return {"status": "error", "mensaje": "Respuesta inesperada de GitHub."}
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}


async def github_descargar_repo(repo: str, destino: str, rama: str = "main") -> dict:
    """Descarga (clona en ZIP) un repo público de GitHub a una carpeta local."""
    if not ALLOW_FILE_ACCESS:
        return {"status": "error", "mensaje": "ALLOW_FILE_ACCESS=False: descargar repos está desactivado."}
    try:
        repo = (repo or "").strip().strip("/")
        rama = (rama or "main").strip().strip("/")
        if "/" not in repo:
            return {"status": "error", "mensaje": "Formato de repo inválido. Usa 'usuario/repo'."}

        p_destino = _limpiar_ruta(destino)
        if _es_ruta_protegida(p_destino):
            return {"status": "error", "mensaje": f"Ruta destino protegida: {p_destino}"}
        p_destino.mkdir(parents=True, exist_ok=True)

        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as cliente:
            resp = await cliente.get(f"{_GH_DL}/{repo}/zip/refs/heads/{rama}", headers={"User-Agent": "HERMATRON-Agent"})
            if resp.status_code == 404:
                return {"status": "error", "mensaje": f"No encontré el repo {repo} o la rama {rama}."}
            if resp.status_code != 200:
                return {"status": "error", "mensaje": f"GitHub respondió {resp.status_code}."}

        with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
            z.extractall(p_destino)

        # Mover el contenido de la carpeta raíz del zip (nombre-carpeta) directo al destino
        extraidos = list(p_destino.iterdir())
        if len(extraidos) == 1 and extraidos[0].is_dir():
            carpeta_interna = extraidos[0]
            for item in list(carpeta_interna.iterdir()):
                shutil.move(str(item), str(p_destino / item.name))
            try:
                carpeta_interna.rmdir()
            except Exception:
                pass

        return {
            "status": "success",
            "repo": repo,
            "rama": rama,
            "destino": str(p_destino),
            "mensaje": "Repo descargado correctamente.",
        }
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}


async def github_buscar_codigo(query: str, max_resultados: int = 10) -> dict:
    """Busca código dentro de repos públicos (requiere GITHUB_TOKEN)."""
    try:
        if not GITHUB_TOKEN:
            return {
                "status": "error",
                "mensaje": "La búsqueda de código de GitHub requiere un token gratuito. Agrega GITHUB_TOKEN en .env (https://github.com/settings/tokens). Mientras tanto usa github_buscar_repos o github_leer_archivo.",
            }
        query = (query or "").strip()
        if not query:
            return {"status": "error", "mensaje": "Consulta vacía."}
        max_resultados = int(max_resultados or 10)
        max_resultados = max(1, min(max_resultados, 20))
        async with httpx.AsyncClient(timeout=20) as cliente:
            resp = await cliente.get(
                f"{_GH_API}/search/code",
                params={"q": query, "per_page": max_resultados},
                headers=_gh_headers(),
            )
            if resp.status_code != 200:
                return {"status": "error", "mensaje": f"GitHub respondió {resp.status_code}: {resp.text[:300]}"}
            items = [
                {
                    "nombre": i.get("name", ""),
                    "ruta": i.get("path", ""),
                    "repo": (i.get("repository") or {}).get("full_name", ""),
                    "url": i.get("html_url", ""),
                }
                for i in resp.json().get("items", [])[:max_resultados]
            ]
            return {"status": "success", "consulta": query, "resultados": items, "total": len(items)}
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# 3. BASE DE CONOCIMIENTO (memoria permanente actualizable)
# ─────────────────────────────────────────────────────────────────────────────

async def guardar_conocimiento(titulo: str, contenido: str, categoria: str = "general", fuente: str = "") -> dict:
    """Guarda o actualiza una entrada de conocimiento en la memoria permanente."""
    try:
        from app.memoria import memoria
        titulo = (titulo or "").strip()
        contenido = (contenido or "").strip()
        if not titulo or not contenido:
            return {"status": "error", "mensaje": "Título y contenido son obligatorios."}
        if len(contenido) > 100000:
            contenido = contenido[:100000]
        await memoria.guardar_conocimiento(titulo, contenido, categoria or "general", fuente or "")
        total = await memoria.contar_conocimientos()
        return {"status": "success", "mensaje": f"Conocimiento '{titulo}' guardado. Total en memoria: {total}"}
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}


async def buscar_conocimiento(consulta: str, limit: int = 10) -> dict:
    """Busca en la base de conocimiento de HERMATRON."""
    try:
        from app.memoria import memoria
        consulta = (consulta or "").strip()
        if not consulta:
            return {"status": "error", "mensaje": "Consulta vacía."}
        resultados = await memoria.buscar_conocimientos(consulta, limit=int(limit or 10))
        return {"status": "success", "consulta": consulta, "resultados": resultados, "total": len(resultados)}
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}


async def actualizar_conocimiento_web(tema: str, num_resultados: int = 5) -> dict:
    """Busca en la web información actual sobre un tema y la guarda en la memoria permanente."""
    try:
        tema = (tema or "").strip()
        if not tema:
            return {"status": "error", "mensaje": "Indica el tema a investigar."}

        from app.busqueda import buscador
        res = buscador.buscar(tema, num_resultados=num_resultados)
        resultados = res.get("resultados", [])
        if not resultados:
            return {"status": "error", "mensaje": f"No encontré información sobre '{tema}'.", "detalle": res}

        # Construir un resumen con los hallazgos principales
        lineas = [f"Resumen de información actual sobre: {tema}", ""]
        fuentes = []
        for i, r in enumerate(resultados, 1):
            titulo = r.get("titulo", "")
            link = r.get("link", "")
            snippet = r.get("snippet", "")
            if titulo and link:
                fuentes.append(link)
            lineas.append(f"{i}. {titulo}")
            lineas.append(f"   URL: {link}")
            if snippet:
                lineas.append(f"   Resumen: {snippet}")
            lineas.append("")

        contenido = "\n".join(lineas)
        titulo_conocimiento = f"Web: {tema}"
        await guardar_conocimiento(
            titulo_conocimiento,
            contenido,
            categoria="web",
            fuente="; ".join(fuentes[:5]),
        )
        return {
            "status": "success",
            "mensaje": f"Conocimiento actualizado desde la web ({len(resultados)} fuentes).",
            "tema": tema,
            "guardado_como": titulo_conocimiento,
            "fuentes": fuentes[:5],
        }
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# 4. AUTO-REPARACIÓN (modo propose-only: NUNCA aplica cambios)
# ─────────────────────────────────────────────────────────────────────────────

def leer_codigo_proyecto(archivo: str) -> dict:
    """Lee el código fuente del propio proyecto HERMATRON para auto-diagnóstico."""
    try:
        archivo = (archivo or "").strip().strip("/")
        if not archivo:
            return {"status": "error", "mensaje": "Indica qué archivo del proyecto leer (ej: app/main.py)."}
        # Evitar escape del proyecto
        p = (BASE_DIR / archivo).resolve()
        if not str(p).startswith(str(BASE_DIR.resolve())):
            return {"status": "error", "mensaje": "Solo puedo leer archivos dentro del proyecto HERMATRON."}
        if not p.exists() or not p.is_file():
            return {"status": "error", "mensaje": f"Archivo no encontrado en el proyecto: {archivo}"}
        return leer_archivo(str(p), max_lineas=400)
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}


async def proponer_arreglo(error: str, contexto: str = "", archivo: str = "", client=None) -> dict:
    """
    Diagnostica un error del propio HERMATRON y PROPONE un parche (diff).
    Modo seguro (propose-only): nunca modifica archivos, solo propone.
    """
    try:
        error = (error or "").strip()
        if not error:
            return {"status": "error", "mensaje": "Describe el error a diagnosticar."}

        codigo = ""
        if archivo:
            leido = leer_codigo_proyecto(archivo)
            if leido.get("status") == "success":
                codigo = leido.get("contenido", "")

        if client is None:
            # Sin LLM: devolvemos una guía básica de auto-reparación
            return {
                "status": "success",
                "modo": "propose-only",
                "diagnostico": "No hay LLM configurado para generar el parche.",
                "causa_probable": error[:500],
                "parche_propuesto": "(Revisa manualmente el archivo indicado y aplica la corrección.)",
                "archivo_sugerido": archivo,
                "aplicado": False,
                "nota": "HERMATRON nunca aplica cambios sin tu aprobación (modo propose-only).",
            }

        prompt_usuario = f"""Eres un ingeniero experto que diagnostica y repara el proyecto HERMATRON (FastAPI).
ERROR REPORTADO:
{error[:2000]}

CONTEXTO ADICIONAL:
{contexto[:2000]}

ARCHIVO RELACIONADO: {archivo or '(no especificado)'}
CÓDIGO DEL ARCHIVO:
{codigo[:20000]}

Responde SOLO con JSON válido con esta estructura:
{{
  "diagnostico": "explicación clara de la causa raíz",
  "causa_probable": "resumen corto",
  "parche_propuesto": "pasos o diff concreto para corregirlo",
  "archivo_sugerido": "ruta del archivo a modificar"
}}"""

        try:
            completion = client.chat.completions.create(
                model=os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b"),
                messages=[
                    {"role": "system", "content": "Eres un ingeniero de software senior que diagnostica errores y propone parches. Siempre respondes JSON válido."},
                    {"role": "user", "content": prompt_usuario},
                ],
                temperature=0.2,
                max_tokens=1500,
            )
            texto = completion.choices[0].message.content or "{}"
            # Extraer JSON robustamente
            start = texto.find("{")
            end = texto.rfind("}")
            if start != -1 and end != -1:
                parche = json.loads(texto[start:end + 1])
            else:
                parche = {"diagnostico": texto[:1000]}
        except Exception as e:
            parche = {"diagnostico": f"No pude generar el parche con el LLM: {str(e)[:300]}"}

        return {
            "status": "success",
            "modo": "propose-only",
            **parche,
            "aplicado": False,
            "nota": "HERMATRON nunca aplica cambios sin tu aprobación (modo propose-only). Revisa la propuesta y pídeme aplicarla si estás de acuerdo.",
        }
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}