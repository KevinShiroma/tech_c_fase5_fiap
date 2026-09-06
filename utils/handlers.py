import os
import logging
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes
from agent import SDRImobiliarioAgent
from .helpers import (
    is_user_allowed,
    get_nome_agente_log,
    AUDIO_TEMP_DIR,
    registrar_mensagem_historico,
    load_json,
    save_json,
    LEADS_PATH
)
from .followup import executar_followup_lead

logger = logging.getLogger("bot_sdr")

# Instância compartilhada do Agente SDR Multiagente LangChain
agent = SDRImobiliarioAgent()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler do comando /start: reinicia sessão do lead para a triagem primária (Sofia) e zera histórico anterior."""
    user = update.effective_user
    user_id = user.id if user else 0
    user_name = user.first_name if user else "Cliente"

    logger.info(f"==> [/start] Usuário conectado: {user_name} (ID: {user_id})")

    # Reinicia o fluxo de atendimento: volta para o Agente Primário (Sofia - Triagem)
    agent.agente_ativo[user_id] = "triagem"
    agent.sessions.pop(user_id, None)

    # Reseta o registro do lead no leads.json para não misturar com atendimentos anteriores
    try:
        leads = load_json(LEADS_PATH)
        lead = next((l for l in leads if str(l.get("telegram_id")) == str(user_id)), None)
        if lead:
            lead["intencao"] = "triagem"
            lead["status"] = "em_triagem"
            lead["score_qualificacao"] = 50
            lead["criterios"] = {}
            lead["agendamento"] = None
            lead["resumo_corretor"] = "Novo atendimento iniciado. Triagem em andamento com Sofia."
            lead["agente_responsavel"] = "Sofia (Triagem)"
            lead["ultima_interacao"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            lead["necessita_follow_up"] = False
            lead["status_followup"] = "Aguardando Interação"
            lead["tentativas_followup"] = 0
            lead["data_ultimo_followup"] = None
            save_json(LEADS_PATH, leads)
            logger.info(f"🧹 [RESET LEADS]: Lead {user_name} ({user_id}) resetado com sucesso no leads.json para novo atendimento.")
    except Exception as ex_reset:
        logger.error(f"Erro ao resetar lead no leads.json no /start: {ex_reset}")

    # Registra o marco divisório no histórico para separação clara dos atendimentos
    registrar_mensagem_historico(
        telegram_id=user_id,
        user_name=user_name,
        role="system",
        content="🔄 --- NOVO ATENDIMENTO INICIADO (/start) ---",
        tipo="sistema"
    )

    if not is_user_allowed(user_id):
        await update.message.reply_text(
            f"⛔ Olá, {user_name}. Este bot está em fase de homologação restrita e seu ID ({user_id}) não está autorizado."
        )
        return

    welcome_text = (
        f"Olá, {user_name}! Seja muito bem-vindo(a) à **Imobiliária Prime**! 🏢✨\n\n"
        "Sou a Sofia, sua consultora imobiliária virtual. Estou aqui para te ajudar a encontrar "
        "a melhor oportunidade no mercado — seja para **comprar seu novo lar**, **investir para obter renda** "
        "ou **alugar um imóvel**.\n\n"
        "💡 *Dica:* Você pode conversar comigo enviando mensagens de **texto** ou gravando **mensagens de voz**! 🎙️\n\n"
        "Me conta: o que você está procurando hoje?"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para mensagens de texto comuns."""
    user = update.effective_user
    user_id = user.id if user else 0
    user_name = user.first_name if user else "Cliente"
    text = update.message.text

    if not is_user_allowed(user_id):
        await update.message.reply_text("⛔ Acesso não autorizado.")
        return

    logger.info(f"👤 [CLIENTE: {user_name} | {user_id}]: {text}")

    # Simula status de 'digitando...'
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    # Processa pelo cérebro do Agente SDR Multiagente LangChain
    response = await agent.process_message(user_id, user_name, text)
    agente_ativo_nome = get_nome_agente_log(agent, user_id)
    
    logger.info(f"🤖 [{agente_ativo_nome}]: {response.strip()}")
    await update.message.reply_text(response)

    # Envia fotos do imóvel caso a IA tenha acionado a tool enviar_fotos_imovel
    fotos_pendentes = agent.get_fotos_pendentes(user_id)
    if fotos_pendentes:
        logger.info(f"📸 Enviando {len(fotos_pendentes)} fotos do imóvel para {user_name} no Telegram...")
        for f in fotos_pendentes:
            try:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=f["url"],
                    caption=f.get("legenda", "📸 Foto do Imóvel")
                )
            except Exception as ex_foto:
                logger.warning(f"Erro ao enviar foto no Telegram: {ex_foto}")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler de Voice AI: Transcreve o áudio do usuário via Azure Speech e processa com o Agente."""
    user = update.effective_user
    user_id = user.id if user else 0
    user_name = user.first_name if user else "Cliente"

    if not is_user_allowed(user_id):
        await update.message.reply_text("⛔ Acesso não autorizado.")
        return

    logger.info(f"🎙️ [VOICE AI INICIADO] De {user_name} ({user_id})")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    local_audio_path = None
    try:
        voice_file = await context.bot.get_file(update.message.voice.file_id)
        local_audio_path = os.path.join(AUDIO_TEMP_DIR, f"voice_{user_id}_{update.message.id}.ogg")
        await voice_file.download_to_drive(local_audio_path)

        # Transcrição com Azure Cognitive Services Speech
        transcribed_text = await agent.transcrever_audio(local_audio_path)

        if not transcribed_text:
            logger.warning(f"Transcrição falhou ou não compreendeu áudio de {user_name}")
            await update.message.reply_text(
                "🎙️ Não consegui compreender o seu áudio com clareza. Você poderia enviar novamente falando mais perto do microfone ou enviar por texto?"
            )
            return

        logger.info(f"🎙️ [VOICE AI TRANSCRIÇÃO]: '{transcribed_text}'")
        await update.message.reply_text(f"🎙️ _Entendi:_ \"{transcribed_text}\"", parse_mode="Markdown")

        # Processa o texto transcrito pelo Agente SDR Multiagente LangChain
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        response = await agent.process_message(user_id, user_name, transcribed_text, tipo="audio_voz")
        agente_ativo_nome = get_nome_agente_log(agent, user_id)
        
        logger.info(f"🤖 [{agente_ativo_nome}]: {response.strip()}")
        await update.message.reply_text(response)

        # Envia fotos caso acionado pela IA
        fotos_pendentes = agent.get_fotos_pendentes(user_id)
        if fotos_pendentes:
            logger.info(f"📸 Enviando {len(fotos_pendentes)} fotos do imóvel para {user_name} no Telegram...")
            for f in fotos_pendentes:
                try:
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=f["url"],
                        caption=f.get("legenda", "📸 Foto do Imóvel")
                    )
                except Exception as ex_foto:
                    logger.warning(f"Erro ao enviar foto no Telegram: {ex_foto}")

    except Exception as e:
        logger.error(f"Erro ao processar mensagem de voz: {e}")
        await update.message.reply_text("Tive um problema ao ouvir sua mensagem de voz. Poderia tentar novamente ou enviar por texto?")
    finally:
        if local_audio_path and os.path.exists(local_audio_path):
            try:
                os.remove(local_audio_path)
            except Exception:
                pass

async def followup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando /followup para demonstração imediata do Exemplo 3 do Tech Challenge.
    Permite acionar a rotina de reengajamento inteligente instantaneamente no chat.
    """
    user = update.effective_user
    user_id = user.id if user else 0
    user_name = user.first_name if user else "Cliente"

    await update.message.reply_text("⏳ *Sofia SDR:* Analisando o histórico da nossa conversa para gerar o reengajamento com IA...", parse_mode="Markdown")
    
    res = await executar_followup_lead(context.bot, agent, user_id, user_name)
    if not res.get("sucesso"):
        await update.message.reply_text(f"⚠️ Não foi possível executar o follow-up automático: {res.get('erro')}")
