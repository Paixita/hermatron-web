# Usar una imagen oficial de Python 3.11 ligera
FROM python:3.11-slim

# Instalar dependencias del sistema requeridas (FFmpeg para procesar video)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Crear un usuario no-root 'user' con UID 1000 requerido por Hugging Face
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Establecer directorio de trabajo
WORKDIR $HOME/app

# Copiar requirements.txt e instalar dependencias de Python
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Copiar el código fuente al contenedor con los permisos del usuario
COPY --chown=user:user . .

# Exponer el puerto por defecto de Hugging Face Spaces
EXPOSE 7860

# Comando para ejecutar el servidor uvicorn en el puerto 7860
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
