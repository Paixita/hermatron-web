"""
Módulo de Búsqueda Web para HERMATRON
Permite buscar en Internet y descargar contenido profundo
"""
import os
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from typing import Optional, List

class BuscadorWeb:
    """Buscador web y extractor de contenido usando DuckDuckGo (100% Gratis) y BeautifulSoup"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SERPER_API_KEY", "")
        self.configurado = bool(self.api_key)
    
    def buscar(self, query: str, num_resultados: int = 5) -> dict:
        """Busca en Internet usando DuckDuckGo (100% Gratis y sin API Key)"""
        try:
            print(f"🔎 [BÚSQUEDA] Buscando en DuckDuckGo: '{query}'")
            resultados_procesados = []
            with DDGS() as ddgs:
                results = ddgs.text(query, max_results=num_resultados)
                for resultado in results:
                    resultados_procesados.append({
                        "titulo": resultado.get("title", ""),
                        "link": resultado.get("href", ""),
                        "snippet": resultado.get("body", "")
                    })
            
            return {
                "query": query,
                "resultados": resultados_procesados,
                "total_encontrados": len(resultados_procesados),
                "fuente": "duckduckgo"
            }
            
        except Exception as e:
            print(f"❌ [ERROR BÚSQUEDA]: {e}")
            # Fallback al scraper original si la librería falla
            return self._buscar_duckduckgo(query, num_resultados=num_resultados)

    def _buscar_duckduckgo(self, query: str, num_resultados: int = 5) -> dict:
        """Búsqueda web gratis vía DuckDuckGo HTML (sin API key)."""
        try:
            print(f"[BUSQUEDA GRATIS] DuckDuckGo: '{query}'")
            url = "https://duckduckgo.com/html/"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"
            }
            resp = requests.get(url, params={"q": query}, headers=headers, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            resultados = []
            for r in soup.select(".result")[: max(num_resultados * 2, num_resultados)]:
                a = r.select_one("a.result__a")
                if not a:
                    continue
                titulo = a.get_text(" ", strip=True)
                link = a.get("href", "")
                snippet_el = r.select_one(".result__snippet")
                snippet = snippet_el.get_text(" ", strip=True) if snippet_el else ""
                if titulo and link:
                    resultados.append({"titulo": titulo, "link": link, "snippet": snippet})
                if len(resultados) >= num_resultados:
                    break

            return {
                "query": query,
                "resultados": resultados,
                "total_encontrados": len(resultados),
                "fuente": "duckduckgo"
            }
        except Exception as e:
            print(f"[ERROR BUSQUEDA GRATIS]: {e}")
            return {"error": str(e), "resultados": [], "fuente": "duckduckgo"}

    def obtener_suscriptores_youtube(self, canal: str) -> dict:
        """
        Intento GRATIS (sin API) para obtener suscriptores de un canal:
        - Busca el canal en YouTube
        - Extrae el texto de suscriptores desde la página de resultados
        Nota: YouTube cambia el HTML a veces; si falla, devolvemos explicación.
        """
        try:
            q = f"{canal} canal youtube suscriptores"
            print(f"[YOUTUBE] Buscando suscriptores: '{canal}'")
            url = "https://www.youtube.com/results"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36",
                "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
            }
            resp = requests.get(url, params={"search_query": canal}, headers=headers, timeout=15)
            resp.raise_for_status()
            html = resp.text

            # Extraer primer "subscriberCountText" que aparezca
            import re
            m = re.search(r"\"subscriberCountText\"\\s*:\\s*\\{[^}]*?\"simpleText\"\\s*:\\s*\"([^\"]+)\"", html)
            if not m:
                # Algunas veces viene en runs
                m = re.search(r"\"subscriberCountText\"\\s*:\\s*\\{[^}]*?\"runs\"\\s*:\\s*\\[\\{[^}]*?\"text\"\\s*:\\s*\"([^\"]+)\"", html)

            if m:
                return {"exito": True, "canal": canal, "suscriptores_texto": m.group(1), "fuente": "youtube_scrape"}

            return {
                "exito": False,
                "canal": canal,
                "error": "No pude extraer suscriptores desde YouTube (HTML cambió o bloqueo).",
                "sugerencia": "Intenta buscar esta información en Google/DuckDuckGo de forma manual.",
                "fuente": "youtube_scrape"
            }
        except Exception as e:
            return {"exito": False, "canal": canal, "error": str(e), "fuente": "youtube_scrape"}

    def descargar_contenido(self, url: str) -> dict:
        """
        ¡NUEVA HABILIDAD!
        Entra al enlace, descarga la página web y extrae el texto real
        para análisis de profundidad científica.
        """
        print(f"📥 [DESCARGA] Absorbiendo datos de: {url}")
        try:
            # Nos hacemos pasar por un navegador normal para que no nos bloqueen
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            respuesta = requests.get(url, headers=headers, timeout=10)
            respuesta.raise_for_status() # Verifica que la página sí cargó
            
            # BeautifulSoup limpia todo el código HTML feo y nos deja solo el texto puro
            soup = BeautifulSoup(respuesta.text, 'html.parser')
            
            # Borramos scripts y menús ocultos
            for script in soup(["script", "style", "nav", "footer"]):
                script.decompose()
                
            texto_limpio = soup.get_text(separator=' ', strip=True)
            
            return {
                "exito": True,
                "url": url,
                # Le pasamos a Groq los primeros 5000 caracteres (aprox 1000 palabras) para no saturar su memoria
                "contenido_descargado": texto_limpio[:5000] 
            }
        except Exception as e:
            print(f"❌ [ERROR DESCARGA]: No se pudo leer {url}. Razón: {e}")
            return {"exito": False, "error": str(e)}

    def buscar_youtube(self, canal: str) -> dict:
        """Buscar información específica de un canal de YouTube"""
        query = f"YouTube canal {canal} videos suscriptores analiticas"
        return self.buscar(query, num_resultados=3)

# Instancia global lista para usarse
buscador = BuscadorWeb()