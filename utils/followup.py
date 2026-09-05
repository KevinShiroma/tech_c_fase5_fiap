import os
import logging
from datetime import datetime
from telegram.ext import ContextTypes
from .helpers import (
    is_user_allowed,
    registrar_mensagem_historico,
    load_json,
    save_json,
    LEADS_PATH,
    CONVERSAS_DIR
)

logger = logging.getLogger("bot_sdr")

async def executar_followup_lead(bot_instance, agent_instance, telegram_id: int, user_name: str = "Cliente") -> dict:
    """
    Executa o ciclo completo de Follow-up (Exemplo 3 do Tech Challenge):
    1. Gera mensagem personalizada via IA mantendo estritamente o contexto.
    2. Envia a mensagem no Telegram do cliente.
    3. Registra no histórico conversas/chat_{id}.json e atualiza data/leads.json.
    """
    logger.info(f"🔄 Iniciando ciclo de Follow-up para {user_name} (ID: {telegram_id})...")

    res = agent_instance.gerar_mensagem_followup(telegram_id)
    if not res.get("sucesso"):
        return {"sucesso": False, "erro": "Falha ao gerar mensagem com a IA"}

    msg_texto = res.get("mensagem", "")

    try:
        # Envia a mensagem proativamente no Telegram do cliente
        await bot_instance.send_message(
            chat_id=telegram_id,
            text=f"🔔 *Mensagem da Sofia (Imobiliária Prime)*\n\n{msg_texto}",
            parse_mode="Markdown"
        )
    except Exception as e_send:
        logger.warning(f"Erro ao enviar com markdown ({e_send}), tentando em texto puro...")
        try:
            await bot_instance.send_message(
                chat_id=telegram_id,
                text=f"🔔 Mensagem da Sofia (Imobiliária Prime)\n\n{msg_texto}"
            )
        except Exception as e_final:
            logger.error(f"Erro crítico ao enviar mensagem de follow-up no Telegram: {e_final}")
            return {"sucesso": False, "erro": str(e_final)}

    # Registra no histórico de conversa
    registrar_mensagem_historico(telegram_id, user_name, "assistant", msg_texto, tipo="followup_automatico")

    # Atualiza status no arquivo de leads
    try:
        leads = load_json(LEADS_PATH)
        for l in leads:
            if str(l.get("telegram_id")) == str(telegram_id):
                l["status_followup"] = "Follow-up Enviado"
                l["data_ultimo_followup"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                l["tentativas_followup"] = l.get("tentativas_followup", 0) + 1
                break
        save_json(LEADS_PATH, leads)
    except Exception as e_save:
        logger.error(f"Erro ao salvar status do follow-up em leads.json: {e_save}")

    logger.info(f"✅ [FOLLOW-UP ENVIADO COM SUCESSO] Para {user_name} ({telegram_id})")
    return {"sucesso": True, "mensagem": msg_texto}

async def rotina_verificar_followups(context: ContextTypes.DEFAULT_TYPE):
    """
    Tarefa periódica 100% AUTOMÁTICA (Job Queue em segundo plano):
    Detecta clientes que interagiram no Telegram, receberam uma resposta/proposta da IA
    e não responderam após X minutos de inatividade.
    O bot retoma o contato sozinho, sem intervenção manual do corretor.
    """
    from .handlers import agent

    MINUTOS_INATIVIDADE = float(os.getenv("FOLLOWUP_INATIVIDADE_MINUTOS", "60.0"))

    try:
        leads = load_json(LEADS_PATH)
        agora = datetime.now()

        for lead in leads:
            tid = lead.get("telegram_id")
            if not tid or not is_user_allowed(tid):
                continue

            # Se o lead já concluiu o agendamento de visita, não dispara follow-up
            if lead.get("agendamento"):
                continue

            # Limite de tentativas para não cansar o lead
            if lead.get("tentativas_followup", 0) >= 2:
                continue

            # Verifica o arquivo de conversa real do Telegram
            chat_file = os.path.join(CONVERSAS_DIR, f"chat_{tid}.json")
            if not os.path.exists(chat_file):
                continue

            chat_data = load_json(chat_file)
            mensagens = chat_data.get("mensagens", [])
            if not mensagens:
                continue

            ultima_msg = mensagens[-1]
            ts_str = ultima_msg.get("timestamp")
            
            # Se a última mensagem partiu da assistente (cliente não respondeu)
            # e a última mensagem NÃO foi o próprio follow-up recente
            if ultima_msg.get("role") == "assistant" and ultima_msg.get("tipo") != "followup_automatico":
                try:
                    dt_ultima = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                    diferenca_minutos = (agora - dt_ultima).total_seconds() / 60.0

                    if diferenca_minutos >= MINUTOS_INATIVIDADE:
                        dt_ult_f_str = lead.get("data_ultimo_followup")
                        if dt_ult_f_str:
                            dt_ult_f = datetime.strptime(dt_ult_f_str, "%Y-%m-%d %H:%M:%S")
                            if (agora - dt_ult_f).total_seconds() / 60.0 < 2.0:
                                continue

                        logger.info(f"⏰ [DISPARO AUTOMÁTICO] Cliente {lead.get('nome')} ({tid}) inativo há {diferenca_minutos:.1f} min. Sofia enviando follow-up...")
                        await executar_followup_lead(context.bot, agent, int(tid), lead.get("nome", "Cliente"))
                except Exception as ex_dt:
                    logger.warning(f"Erro ao calcular inatividade do lead {tid}: {ex_dt}")

    except Exception as e:
        logger.error(f"Erro na rotina periódica de follow-up: {e}")
