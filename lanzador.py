import os
import subprocess
import sys
import time

# --- MÁXIMA PORTABILIDAD ---
# Detectamos la carpeta real donde está parado el archivo
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

os.chdir(BASE_DIR)

print("====================================================")
print("     CENTRO DE ARRANQUE AUTOMÁTICO - FULA MOTOS     ")
print("====================================================")

# 1. Arrancar el Servidor Web (Flask)
print("\n[1/3] Encendiendo Servidor Web (Celulares)...")
# CAMBIO SEGURO: Usamos "python" directo para evitar el bucle infinito
subprocess.Popen(["python", "servidor_web.py"], creationflags=subprocess.CREATE_NEW_CONSOLE)
time.sleep(2)

# 2. Arrancar Ngrok amarrado a tu dominio fijo
print("[2/3] Levantando puente de Internet (Ngrok)...")
ngrok_exe = os.path.join(BASE_DIR, "ngrok.exe")
cmd_ngrok = ["http", "5000", "--domain=unabasing-sharan-dolly.ngrok-free.dev"]

if os.path.exists(ngrok_exe):
    subprocess.Popen([ngrok_exe] + cmd_ngrok, creationflags=subprocess.CREATE_NEW_CONSOLE)
else:
    subprocess.Popen(["ngrok"] + cmd_ngrok, creationflags=subprocess.CREATE_NEW_CONSOLE)
time.sleep(2)

print("\n🔗 Enlace listo para los celulares:")
print("👉 https://unabasing-sharan-dolly.ngrok-free.dev")
print("====================================================")

# 3. Arrancar el Filtro de Seguridad (Login)
print("[3/3] Abriendo Pantalla de Inicio de Sesión...")
# CAMBIO SEGURO: Usamos "python" para abrir la interfaz gráfica
subprocess.run(["python", "login.py"])