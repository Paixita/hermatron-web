@echo off
cd /d "%~dp0"
echo Abriendo Estudio de Video...
start http://localhost:5001/videos
py -m app.main
pause
