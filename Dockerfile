# Imagem base oficial do Python 3.12 Slim
FROM python:3.12-slim

# Evitar prompts interativos durante instalação de pacotes
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Diretório de trabalho da aplicação
WORKDIR /app

# Instalar dependências de sistema necessárias (ffmpeg, áudio e certificados)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libasound2 \
    libsndfile1 \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar pacotes Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar código-fonte da aplicação
COPY . .

# Garantir permissão de execução do entrypoint e conversão de finais de linha
RUN chmod +x entrypoint.sh

# Expor a porta do Dashboard Streamlit
EXPOSE 8501

# Healthcheck do Streamlit
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Comando de entrada
ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]
