"""Probar voces del sistema Windows"""
import pyttsx3
import os

engine = pyttsx3.init()

# Voz 1: Sabina (la que ya usas)
print("=== PROBANDO SABINA (Femenina) ===")
engine.setProperty('voice', 'HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Speech\\Voices\\Tokens\\TTS_MS_ES-MX_SABINA_11.0')
engine.setProperty('rate', 170)
engine.setProperty('volume', 0.95)
engine.save_to_file("Hola, soy Sabina, la voz femenina de Microsoft. Esta es una prueba de narración para tu video.", "audio/test_sabina.mp3")
engine.runAndWait()
print("Guardado: audio/test_sabina.mp3")

# Voz 2: Raul (masculina)
print("\n=== PROBANDO RAUL (Masculina) ===")
engine.setProperty('voice', 'HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Speech_OneCore\\Voices\\Tokens\\TTS_MS_ES-MX_Raul_11.0')
engine.setProperty('rate', 170)
engine.setProperty('volume', 0.95)
engine.save_to_file("Hola, soy Raul, la voz masculina de Microsoft. Esta es una prueba de narración para tu video.", "audio/test_raul.mp3")
engine.runAndWait()
print("Guardado: audio/test_raul.mp3")

print("\n=== COMPARA LAS DOS VOCES ===")
print("Abre los archivos en audio/ para escuchar")
