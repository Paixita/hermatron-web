@echo off
cd /d "%~dp0"
echo Encendiendo el motor de Hermatron...
timeout /t 2 >nul
start http://localhost:5001
py -m app.main
pause