# 🤖 HERMATRON - Agente Creativo Profesional

Un asistente de IA profesional con voz, memoria persistente y interfaz moderna, construido con **FastAPI** y **Edge TTS**.

## ✨ Características

- 🎯 **Chat inteligente** con Groq (Llama 3.1)
- 🗣️ **Voz neuronal** con Edge TTS (voces en español)
- 💾 **Memoria persistente** con SQLite
- 🎨 **Interfaz moderna** estilo dark mode
- ⚡ **Arquitectura profesional** asíncrona
- 🔧 **Fácil configuración** con variables de entorno

## 📁 Estructura del Proyecto

```
hermatron_agent/
├── app/
│   ├── __init__.py
│   ├── main.py          # Aplicación FastAPI
│   ├── config.py        # Configuración
│   ├── memoria.py       # Módulo SQLite
│   └── voz.py           # Módulo TTS
├── static/
│   ├── styles.css       # Estilos
│   └── app.js           # JavaScript
├── templates/
│   └── index.html       # Frontend
├── audio/               # Archivos de audio generados
├── .env                 # Variables de entorno (NO committear)
├── .env.example         # Ejemplo de variables
├── requirements.txt     # Dependencias
└── README.md
```

## 🚀 Instalación

### 1. Clonar o descargar el proyecto

```bash
cd hermatron_agent
```

### 2. Crear entorno virtual (recomendado)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar API Key de Groq

1. Ve a https://console.groq.com
2. Crea una cuenta y genera una API Key
3. Copia la API Key en el archivo `.env`:

```bash
GROQ_API_KEY=tu_api_key_aqui
```

### 5. Ejecutar el servidor

```bash
# Desde la raíz del proyecto
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 5002
```

O simplemente:

```bash
python -m app.main
```

### 6. Abrir en el navegador

Ve a: **http://localhost:5002**

## 📖 Uso

### Chat básico

1. Escribe tu mensaje en el input
2. Presiona `Enter` para enviar
3. HERMATRON responderá con su personalidad única

### Audio

- El audio se genera automáticamente con cada respuesta
- Usa el botón 🔊 para activar/desactivar
- Se reproduce automáticamente al recibir la respuesta

### Memoria

- Todas las conversaciones se guardan en SQLite
- Usa el botón "Limpiar" para borrar el historial
- La memoria persiste entre sesiones

## ⚙️ Configuración

El archivo `.env` contiene todas las configuraciones:

```bash
# API de Groq
GROQ_API_KEY=tu_api_key_aqui

# Servidor
PORT=5002
HOST=0.0.0.0
DEBUG=True

# Modelo (opcional)
GROQ_MODEL=llama-3.1-70b-versatile

# Voz TTS (opcional)
TTS_VOICE=es-MX-JorgeNeural
```

### Voces disponibles

| Voz | País | Género |
|-----|------|--------|
| `es-ES-AlvaroNeural` | España | Masculino |
| `es-ES-ElviraNeural` | España | Femenino |
| `es-MX-DaliaNeural` | México | Femenino |
| `es-CO-SalomeNeural` | Colombia | Femenino 🇨🇴 |
| `es-CO-GonzaloNeural` | Colombia | Masculino 🇨🇴 |
| `es-AR-ElenaNeural` | Argentina | Femenino |

## 🔌 API Endpoints

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/` | GET | Interfaz web |
| `/api/chat` | POST | Enviar mensaje |
| `/api/audio/ultimo` | GET | Obtener último audio |
| `/api/memoria` | GET | Ver estado de memoria |
| `/api/limpiar` | POST | Limpiar historial |
| `/api/health` | GET | Health check |
| `/api/voces` | GET | Listar voces TTS |

## 🛠️ Desarrollo

### Agregar nuevas características

1. **Nuevo endpoint**: Agregar en `app/main.py`
2. **Nueva voz**: Modificar `app/voz.py`
3. **Estilos**: Editar `static/styles.css`
4. **Frontend**: Modificar `templates/index.html`

### Debug mode

Con `DEBUG=True` en `.env`, el servidor se recarga automáticamente.

## 📝 Ejemplo de uso con Python

```python
import httpx

async def chatear():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            'http://localhost:5000/api/chat',
            json={'prompt': '¡Hola HERMATRON! ¿Cómo estás?', 'generar_audio': True}
        )
        data = response.json()
        print(data['respuesta'])
```

## 🐛 Solución de problemas

### "API key no configurada"

- Verifica que el archivo `.env` exista
- Asegúrate de que `GROQ_API_KEY` tenga un valor válido
- Reinicia el servidor

### "Error generando audio"

- Verifica tu conexión a internet (Edge TTS requiere conexión)
- Prueba cambiando la voz en `.env`

### Puerto ya en uso

- Cambia el `PORT` en `.env`
- O mata el proceso: `netstat -ano | findstr :5000`

## 📄 Licencia

MIT License - Siéntete libre de usar y modificar.

## 🤝 Contribuciones

¡Las contribuciones son bienvenidas! Abre un issue o PR.

---

**Hecho con ❤️ por tu pana desarrollador**

*HERMATRON © 2026*
