#!/bin/bash
set -e

echo "========================================="
echo "   Iniciando instalación de Hermatron"
echo "========================================="

# 1. Actualizar sistema y paquetes básicos
echo "-> Actualizando paquetes del sistema..."
sudo apt update
sudo apt install -y python3-pip python3-venv git ffmpeg sqlite3 nginx curl

# 2. Configurar memoria Swap (4GB) para que FFmpeg no crashee
echo "-> Configurando Memoria Swap (4GB)..."
if [ ! -f /swapfile ]; then
    sudo fallocate -l 4G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    sudo sysctl vm.swappiness=10
    echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
else
    echo "Swap ya configurada."
fi

# 3. Clonar repositorio
echo "-> Clonando código de Hermatron..."
if [ -d "hermatron-web" ]; then
    echo "El directorio hermatron-web ya existe, actualizando..."
    cd hermatron-web
    git pull
else
    git clone https://github.com/Paixita/hermatron-web.git
    cd hermatron-web
fi

# 4. Crear entorno virtual e instalar dependencias
echo "-> Instalando entorno virtual de Python..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 5. Crear archivo .env vacío para que el usuario lo llene luego
if [ ! -f .env ]; then
    touch .env
    echo "GROQ_API_KEY=" >> .env
    echo "PEXELS_API_KEY=" >> .env
    echo "ELEVENLABS_API_KEY=" >> .env
    echo "UNSPLASH_ACCESS_KEY=" >> .env
fi

# 6. Configurar Systemd para que inicie automáticamente
echo "-> Configurando servicio de auto-arranque..."
cat << 'EOF' | sudo tee /etc/systemd/system/hermatron.service
[Unit]
Description=Hermatron AI Web App
After=network.target

[Service]
User=root
WorkingDirectory=/home/root/hermatron-web
ExecStart=/home/root/hermatron-web/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 80
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Ajustar los paths del usuario en base a quién ejecuta el script
USER_HOME=$(eval echo ~$SUDO_USER)
if [ -z "$USER_HOME" ]; then
    USER_HOME=$HOME
fi
sudo sed -i "s|/home/root|${USER_HOME}|g" /etc/systemd/system/hermatron.service

sudo systemctl daemon-reload
sudo systemctl enable hermatron
sudo systemctl start hermatron

echo "========================================="
echo " ¡INSTALACIÓN COMPLETADA EXITOSAMENTE! "
echo "========================================="
echo "La app ya debería estar corriendo en el puerto 80."
echo "Puedes verla entrando a la IP externa de la máquina virtual en tu navegador."
