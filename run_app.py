import subprocess
import sys
import time
import os

print("=== Iniciando Agente SDR Imobiliário na Nuvem ===", flush=True)

# 1. Iniciar o Bot Telegram em segundo plano
print("Iniciando Bot Telegram (bot.py)...", flush=True)
bot_proc = subprocess.Popen([sys.executable, "bot.py"])

# 2. Iniciar o Dashboard Streamlit na porta 8501
print("Iniciando Portal do Corretor (Streamlit)...", flush=True)
cmd_streamlit = [
    sys.executable, "-m", "streamlit", "run", "dashboard.py",
    "--server.port", "8501",
    "--server.address", "0.0.0.0",
    "--server.headless", "true",
    "--server.enableCORS", "false",
    "--server.enableXsrfProtection", "false"
]

streamlit_proc = subprocess.Popen(cmd_streamlit)

try:
    # Mantém o processo principal vivo monitorando o Streamlit
    streamlit_proc.wait()
except KeyboardInterrupt:
    print("Encerrando processos...", flush=True)
    bot_proc.terminate()
    streamlit_proc.terminate()
