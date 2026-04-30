@echo off
echo ========================================
echo    HERMATRON - Agente Creativo
echo    Instalando dependencias...
echo ========================================
echo.

python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo ========================================
echo    Instalacion completada!
echo ========================================
echo.
echo Ahora edita el archivo .env con tu API key de Groq
echo Luego ejecuta: iniciar.bat
echo.
pause
