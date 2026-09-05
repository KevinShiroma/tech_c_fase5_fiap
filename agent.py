import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

# Importações dos módulos especializados da pasta utils/
from utils.catalog import FOTOS_CATALOGO_MAP, obter_fotos_imovel
from utils.prompts import (
    get_system_prompt_for_agent,
    get_triagem_prompt,
    get_compra_prompt,
    get_aluguel_prompt,
    get_investimento_prompt
)
from utils.tools import (
    get_tools_definition,
    tool_buscar_imoveis,
    tool_consultar_agenda,
    tool_confirmar_agendamento,
    tool_atualizar_lead,
    tool_enviar_fotos_imovel,
    tool_transferir_para_especialista
)
from utils.voice import transcrever_audio, converter_para_wav

load_dotenv()
logger = logging.getLogger("bot_sdr")

from utils.helpers import (
    load_json,
    save_json,
    registrar_mensagem_historico,
    BASE_DIR,
    DATA_DIR,
    CONVERSAS_DIR,
    IMOVEIS_PATH,
    CORRETORES_PATH,
    LEADS_PATH
)

class SDRImobiliarioAgent:
    """Orquestrador Central Multiagente LangChain (Sofia, Camila, Verônica, Rodrigo)."""

    def __init__(self):
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1-mini")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")

        if self.endpoint and self.api_key:
            logger.info("Conectando ao Azure OpenAI via LangChain (AzureChatOpenAI)...")
            self.llm = AzureChatOpenAI(
                azure_endpoint=self.endpoint,
                api_key=self.api_key,
                azure_deployment=self.deployment_name,
                api_version=self.api_version,
                temperature=0.7
            )
        else:
            logger.warning("Credenciais Azure OpenAI não detectadas. Operando em modo de simulação.")
            self.llm = None

        self.sessions: Dict[int, List[Any]] = {}
        self.fotos_pendentes: Dict[int, List[Dict[str, str]]] = {}
        self.agente_ativo: Dict[int, str] = {}

    def get_system_prompt_for_agent(self, telegram_id: int, user_name: str) -> str:
        """Retorna o system prompt do especialista ativo para o lead."""
        return get_system_prompt_for_agent(self.agente_ativo, telegram_id, user_name)

    def get_tools_definition(self) -> List[Dict[str, Any]]:
        """Retorna os schemas de Function Calling disponíveis para os agentes."""
        return get_tools_definition()

    def get_fotos_pendentes(self, telegram_id: int) -> List[Dict[str, str]]:
        """Retorna e esvazia a fila de fotos prontas para envio no Telegram."""
        return self.fotos_pendentes.pop(telegram_id, [])

    async def transcrever_audio(self, audio_file_path: str) -> Optional[str]:
        """Delega a transcrição de voz para o módulo utils.voice."""
        return await transcrever_audio(audio_file_path)

    async def process_message(self, telegram_id: int, user_name: str, message_text: str, tipo: str = "texto") -> str:
        """Processa a mensagem com os Multiagentes LangChain utilizando Function Calling e Handoff dinâmico."""
        registrar_mensagem_historico(telegram_id, user_name, "user", message_text, tipo)

        if not self.llm:
            return (
                f"Olá, {user_name}! Recebi sua mensagem: '{message_text}'.\n\n"
                "ℹ️ **Modo de Configuração:** Por favor, adicione as chaves `AZURE_OPENAI_ENDPOINT` "
                "e `AZURE_OPENAI_API_KEY` no arquivo `.env` para iniciar o modelo de IA!"
            )

        if telegram_id not in self.agente_ativo:
            self.agente_ativo[telegram_id] = "triagem"

        prompt_ativo = self.get_system_prompt_for_agent(telegram_id, user_name)

        if telegram_id not in self.sessions:
            self.sessions[telegram_id] = [SystemMessage(content=prompt_ativo)]
            json_file = os.path.join(CONVERSAS_DIR, f"chat_{telegram_id}.json")
            if os.path.exists(json_file):
                try:
                    chat_dados = load_json(json_file)
                    msgs_todas = chat_dados.get("mensagens", [])
                    idx_inicio = 0
                    for i, m in enumerate(msgs_todas):
                        if m.get("tipo") == "sistema" or "NOVO ATENDIMENTO" in m.get("conteudo", ""):
                            idx_inicio = i + 1
                    for m in msgs_todas[idx_inicio:][-10:]:
                        role = m.get("role", "user")
                        conteudo = m.get("conteudo", "")
                        if role == "user": self.sessions[telegram_id].append(HumanMessage(content=conteudo))
                        elif role == "assistant": self.sessions[telegram_id].append(AIMessage(content=conteudo))
                except Exception:
                    pass
        else:
            if self.sessions[telegram_id] and isinstance(self.sessions[telegram_id][0], SystemMessage):
                self.sessions[telegram_id][0] = SystemMessage(content=prompt_ativo)

        history = self.sessions[telegram_id]
        history.append(HumanMessage(content=message_text))

        if len(history) > 22:
            system_msg = history[0]
            resto = history[-20:]
            while resto and isinstance(resto[0], ToolMessage): resto.pop(0)
            history = [system_msg] + resto
            self.sessions[telegram_id] = history

        try:
            llm_with_tools = self.llm.bind_tools(self.get_tools_definition())
            response_msg = llm_with_tools.invoke(history)
            tool_calls = getattr(response_msg, "tool_calls", [])

            if tool_calls:
                history.append(response_msg)
                for tool_call in tool_calls:
                    function_name = tool_call.get("name", "")
                    call_id = tool_call.get("id", "call_default")
                    args = tool_call.get("args", {})
                    if isinstance(args, str):
                        try: args = json.loads(args)
                        except Exception: args = {}

                    if function_name == "transferir_para_especialista":
                        tool_result = tool_transferir_para_especialista(telegram_id, user_name, args, self.agente_ativo, LEADS_PATH, load_json, save_json)
                        history[0] = SystemMessage(content=self.get_system_prompt_for_agent(telegram_id, user_name))
                    elif function_name == "buscar_imoveis":
                        tool_result = tool_buscar_imoveis(args, IMOVEIS_PATH, load_json)
                    elif function_name == "consultar_agenda_corretores":
                        tool_result = tool_consultar_agenda(args, CORRETORES_PATH, load_json)
                    elif function_name == "confirmar_agendamento":
                        tool_result = tool_confirmar_agendamento(telegram_id, user_name, args, LEADS_PATH, load_json, save_json)
                    elif function_name == "atualizar_lead_sdr":
                        tool_result = tool_atualizar_lead(telegram_id, user_name, args, LEADS_PATH, load_json, save_json)
                    elif function_name == "enviar_fotos_imovel":
                        tool_result = tool_enviar_fotos_imovel(telegram_id, args, IMOVEIS_PATH, self.fotos_pendentes, load_json)
                    else:
                        tool_result = json.dumps({"erro": "Ferramenta desconhecida"})

                    history.append(ToolMessage(content=tool_result, tool_call_id=call_id, name=function_name))

                final_response = self.llm.invoke(history)
                final_content = str(final_response.content)
                history.append(AIMessage(content=final_content))
                registrar_mensagem_historico(telegram_id, user_name, "assistant", final_content, "texto")
                return final_content
            else:
                reply_content = str(response_msg.content)
                history.append(AIMessage(content=reply_content))
                registrar_mensagem_historico(telegram_id, user_name, "assistant", reply_content, "texto")
                return reply_content
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {e}")
            return "Desculpe, tive um contratempo na conexão com a inteligência. Poderia tentar novamente?"

    def gerar_mensagem_followup(self, telegram_id: int) -> Dict[str, Any]:
        """Gera mensagem de follow-up proativo mantendo estritamente o contexto histórico."""
        leads = load_json(LEADS_PATH)
        lead = next((l for l in leads if str(l.get("telegram_id")) == str(telegram_id)), None)
        user_name = lead.get("nome", "Cliente") if lead else "Cliente"

        json_file = os.path.join(CONVERSAS_DIR, f"chat_{telegram_id}.json")
        mensagens_anteriores = []
        if os.path.exists(json_file):
            try:
                chat_data = load_json(json_file)
                mensagens_anteriores = chat_data.get("mensagens", [])
            except Exception: pass

        transcricao = "\n".join([f"- {m.get('autor', 'Pessoa')}: {m.get('conteudo', '')}" for m in mensagens_anteriores[-6:]])

        prompt = f"""Você é Sofia, consultora SDR da Imobiliária Prime. Retome contato com {user_name} sobre {lead.get('intencao', 'imóveis')}.
        Contexto recente: {transcricao}
        Objetivo: Reengajar com simpatia, trazer novidade relevante e convidar para uma ação curta.
        Retorne APENAS o texto da mensagem."""

        if not self.llm:
            return {"sucesso": True, "nome": user_name, "telegram_id": telegram_id, "mensagem": "Olá, tudo bem? Como está a busca pelo seu imóvel?", "gancho": "fallback", "metodo": "offline"}

        response = self.llm.invoke([SystemMessage(content="Consultora SDR de elite."), HumanMessage(content=prompt)])
        return {"sucesso": True, "nome": user_name, "telegram_id": telegram_id, "mensagem": str(response.content).strip(), "gancho": "followup", "metodo": "langchain"}
