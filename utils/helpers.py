import os
import logging
from typing import Any

# Diretório base do projeto e pasta temporária para arquivos de áudio
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO_TEMP_DIR = os.path.join(BASE_DIR, "temp_audio")
os.makedirs(AUDIO_TEMP_DIR, exist_ok=True)

def configurar_logger(log_filename: str = "bot.log") -> logging.Logger:
    """Configura o sistema de logging com saída simultânea no console e em arquivo."""
    log_path = os.path.join(BASE_DIR, log_filename)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
    file_handler.setFormatter(formatter)

    logger = logging.getLogger("bot_sdr")
    logger.setLevel(logging.INFO)
    logger.handlers = [console_handler, file_handler]
    return logger

def is_user_allowed(user_id: int) -> bool:
    """Verifica se o usuário do Telegram está autorizado na whitelist do .env (se configurada)."""
    allowed = os.getenv("ALLOWED_TELEGRAM_USERS", "").strip()
    if not allowed:
        return True
    allowed_ids = [uid.strip() for uid in allowed.split(",") if uid.strip()]
    return str(user_id) in allowed_ids

def get_nome_agente_log(agent_instance: Any, user_id: int) -> str:
    """Retorna o nome formatado do agente especialista ativo para exibição nos logs."""
    esp = agent_instance.agente_ativo.get(user_id, "triagem").lower()
    mapa = {
        "compra": "VERÔNICA (COMPRA)",
        "aluguel": "CAMILA (LOCAÇÃO)",
        "investimento": "RODRIGO (INVESTIMENTO)",
        "triagem": "SOFIA (TRIAGEM)"
    }
    return mapa.get(esp, "SOFIA (TRIAGEM)")

# =========================================================================================
# Persistência e Caminhos de Dados (CRM Simulado)
# =========================================================================================
import json
from datetime import datetime

DATA_DIR = os.path.join(BASE_DIR, "data")
CONVERSAS_DIR = os.path.join(BASE_DIR, "conversas")
os.makedirs(CONVERSAS_DIR, exist_ok=True)

IMOVEIS_PATH = os.path.join(DATA_DIR, "imoveis.json")
CORRETORES_PATH = os.path.join(DATA_DIR, "corretores.json")
LEADS_PATH = os.path.join(DATA_DIR, "leads.json")

def load_json(filepath: str) -> Any:
    """Carrega dados estruturados de um arquivo JSON."""
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_json(filepath: str, data: Any):
    """Salva dados estruturados em arquivo JSON formatado."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def registrar_mensagem_historico(telegram_id: int, user_name: str, role: str, content: str, tipo: str = "texto"):
    """Salva a mensagem no histórico individual do usuário na pasta conversas/ em formato JSON e TXT."""
    json_file = os.path.join(CONVERSAS_DIR, f"chat_{telegram_id}.json")
    txt_file = os.path.join(CONVERSAS_DIR, f"chat_{telegram_id}.txt")
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if role == "user":
        autor = user_name
    elif role == "system":
        autor = "Sistema"
    else:
        autor = "Sofia (SDR)"

    dados = {"lead_id": f"LEAD-{telegram_id}", "telegram_id": telegram_id, "nome": user_name, "mensagens": []}
    if os.path.exists(json_file):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                dados = json.load(f)
        except Exception:
            pass

    dados["mensagens"].append({"timestamp": timestamp_str, "role": role, "autor": autor, "tipo": tipo, "conteudo": content})
    save_json(json_file, dados)

    if tipo == "sistema" or role == "system":
        linha_txt = f"\n[{timestamp_str}] 🔄 ==================== NOVO ATENDIMENTO INICIADO (/start) ====================\n\n"
    else:
        prefixo = "🎙️ [ÁUDIO]" if tipo == "audio_voz" else "💬"
        linha_txt = f"[{timestamp_str}] {prefixo} {autor}: {content}\n"

    try:
        with open(txt_file, "a", encoding="utf-8") as f:
            f.write(linha_txt)
    except Exception:
        pass

