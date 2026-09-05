import os
from dotenv import load_dotenv
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters
)
from utils.helpers import configurar_logger
from utils.handlers import start, handle_text, handle_voice, followup_command
from utils.followup import rotina_verificar_followups

# Carrega variáveis do arquivo .env
load_dotenv()

# Configura logger centralizado
logger = configurar_logger("bot.log")

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("ERRO: TELEGRAM_BOT_TOKEN não configurado no arquivo .env!")
        return

    logger.info("Iniciando Bot SDR Imobiliário com gravação em bot.log...")
    app = ApplicationBuilder().token(token).build()

    # Handlers principais (comandos, texto e notas de voz)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("followup", followup_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    # Configuração da Job Queue para verificar inatividades a cada 20 segundos
    if app.job_queue:
        app.job_queue.run_repeating(rotina_verificar_followups, interval=20, first=10)
        logger.info("🕒 Job Queue de Follow-up 100% Automático ativada (checagem a cada 20s).")

    app.run_polling()

if __name__ == "__main__":
    main()


