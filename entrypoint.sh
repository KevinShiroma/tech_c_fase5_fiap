#!/bin/bash
set -e

echo "=== Iniciando Agente SDR Imobiliário no Azure Container Apps ==="

# 1. Iniciar o Bot Telegram em background
echo "Iniciando Bot Telegram..."
python bot.py &
BOT_PID=$!
echo "Bot Telegram iniciado com PID: $BOT_PID"

# 2. Iniciar o Dashboard Streamlit no foreground (porta 8501)
echo "Iniciando Dashboard Streamlit na porta 8501..."
exec streamlit run dashboard.py \
    --server.port 8501 \
    --server.address 0.0.0.0 \
    --server.headless true \
    --server.enableCORS false \
    --server.enableXsrfProtection false
