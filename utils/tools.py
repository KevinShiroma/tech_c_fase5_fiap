import json
import logging
from datetime import datetime
from typing import Dict, Any, List
from .catalog import obter_fotos_imovel

logger = logging.getLogger("bot_sdr")

def get_tools_definition() -> List[Dict[str, Any]]:
    """Retorna os schemas de todas as ferramentas disponíveis para os agentes do LangChain."""
    return [
        {
            "type": "function",
            "function": {
                "name": "buscar_imoveis",
                "description": "Consulta o catálogo de imóveis com filtros por modalidade (compra/aluguel/investimento), região/bairro, tipo, preço máximo e quartos.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "modalidade": {
                            "type": "string",
                            "enum": ["compra", "aluguel", "investimento"],
                            "description": "Modalidade do negócio."
                        },
                        "regiao": {
                            "type": "string",
                            "description": "Zona ou bairro de interesse (ex: Zona Sul, Moema, Vila Mariana, Pinheiros)."
                        },
                        "tipo": {
                            "type": "string",
                            "description": "Tipo de imóvel (ex: apartamento, studio, casa, cobertura)."
                        },
                        "preco_max": {
                            "type": "number",
                            "description": "Preço máximo de compra ou valor máximo de aluguel mensal."
                        },
                        "quartos": {
                            "type": "integer",
                            "description": "Quantidade mínima de dormitórios."
                        }
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "consultar_agenda_corretores",
                "description": "Verifica os corretores e horários livres na agenda para propor opções de visita presencial ou reunião com o consultor.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "especialidade": {
                            "type": "string",
                            "description": "Especialidade desejada (ex: compra, locacao, investimentos, residencial)."
                        }
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "confirmar_agendamento",
                "description": "Registra e confirma a visita presencial ou reunião de consultoria na base de dados com o corretor responsável.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "corretor_nome": {
                            "type": "string",
                            "description": "Nome do corretor que atenderá o cliente."
                        },
                        "data_hora": {
                            "type": "string",
                            "description": "Data e horário confirmado em formato ISO (ex: 2026-09-08T10:00:00)."
                        },
                        "imovel_id": {
                            "type": "string",
                            "description": "Código do imóvel selecionado (ex: IMO-001)."
                        },
                        "tipo_visita": {
                            "type": "string",
                            "enum": ["presencial", "reuniao_online"],
                            "description": "Tipo da visita ou encontro agendado."
                        }
                    },
                    "required": ["corretor_nome", "data_hora"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "atualizar_lead_sdr",
                "description": "Atualiza os critérios de qualificação (score, urgência, orçamento) e gera um resumo executivo estruturado para o corretor.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "intencao": {
                            "type": "string",
                            "enum": ["compra", "aluguel", "investimento"]
                        },
                        "score": {
                            "type": "integer",
                            "description": "Score de qualificação comercial de 0 a 100."
                        },
                        "criterios": {
                            "type": "object",
                            "description": "Mapa com critérios levantados: orcamento, quartos, regiao, urgencia, garantia_preferida."
                        },
                        "resumo_corretor": {
                            "type": "string",
                            "description": "Resumo inteligente para o corretor humano entender o perfil, pontos de atenção e próximas ações recomendadas."
                        }
                    },
                    "required": ["intencao", "score", "resumo_corretor"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "enviar_fotos_imovel",
                "description": "Localiza e enfileira fotos oficiais em alta resolução de um imóvel pelo código ou termo de busca para envio imediato no Telegram.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "imovel_id": {
                            "type": "string",
                            "description": "ID do imóvel (ex: IMO-001, IMO-002)."
                        },
                        "bairro_ou_termo": {
                            "type": "string",
                            "description": "Bairro ou nome do imóvel para busca reversa das fotos."
                        }
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "transferir_para_especialista",
                "description": "Transfere o atendimento do lead para um dos agentes especialistas ('compra', 'aluguel' ou 'investimento') após identificar sua necessidade.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "especialidade": {
                            "type": "string",
                            "enum": ["compra", "aluguel", "investimento"],
                            "description": "Especialidade do agente de destino para o qual transferir o atendimento."
                        },
                        "motivo": {
                            "type": "string",
                            "description": "Breve justificativa do roteamento baseado no que o cliente informou."
                        }
                    },
                    "required": ["especialidade"]
                }
            }
        }
    ]

def tool_transferir_para_especialista(
    telegram_id: int,
    user_name: str,
    args: Dict[str, Any],
    agente_ativo_dict: dict,
    leads_path: str,
    load_json_fn,
    save_json_fn
) -> str:
    """Executa a transição de agente (Handoff Multiagente LangChain)."""
    especialidade = args.get("especialidade", "triagem").lower()
    motivo = args.get("motivo", "Intenção identificada durante o atendimento")

    mapa_nomes = {
        "compra": "Verônica (Agente de Compra)",
        "aluguel": "Camila (Agente de Locação)",
        "investimento": "Rodrigo (Agente de Investimentos)"
    }
    nome_agente = mapa_nomes.get(especialidade, "Agente Especialista")

    mapa_apresentacao = {
        "compra": "Olá, sou a Verônica, agente especializada em compra residencial da Imobiliária Prime...",
        "aluguel": "Olá, sou a Camila, agente especializada em locação da Imobiliária Prime...",
        "investimento": "Olá, sou o Rodrigo, agente especializado em investimentos imobiliários da Imobiliária Prime..."
    }
    frase_abertura = mapa_apresentacao.get(especialidade, f"Olá, sou o agente especialista em {especialidade}...")

    # Atualiza o agente ativo em memória para este cliente
    agente_ativo_dict[telegram_id] = especialidade

    # Persiste a alteração no leads.json para sincronização em tempo real com o Dashboard
    leads = load_json_fn(leads_path)
    lead = next((l for l in leads if str(l.get("telegram_id")) == str(telegram_id)), None)
    if lead:
        lead["intencao"] = especialidade
        lead["agente_responsavel"] = nome_agente
        lead["ultima_interacao"] = datetime.now().isoformat()
        save_json_fn(leads_path, leads)
    else:
        novo_lead = {
            "lead_id": f"LEAD-{telegram_id}",
            "telegram_id": telegram_id,
            "nome": user_name,
            "data_recebimento": datetime.now().strftime("%Y-%m-%d"),
            "ultima_interacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "intencao": especialidade,
            "agente_responsavel": nome_agente,
            "score_qualificacao": 60,
            "criterios": {},
            "resumo_corretor": f"Cliente encaminhado para {nome_agente} via triagem inteligente LangChain. Motivo: {motivo}."
        }
        leads.append(novo_lead)
        save_json_fn(leads_path, leads)

    logger.info(f"🔀 [ROTEAMENTO MULTIAGENTE LANGCHAIN]: Lead {user_name} ({telegram_id}) transferido para {nome_agente}. Motivo: {motivo}")

    return json.dumps({
        "status": "sucesso",
        "especialidade": especialidade,
        "agente_responsavel": nome_agente,
        "mensagem": (
            f"Transferência concluída com sucesso para {nome_agente}! "
            f"REGRA MANDATÓRIA: Sua resposta ao cliente DEVE OBRIGATORIAMENTE se iniciar com a apresentação: "
            f"'{frase_abertura}'. Em seguida, aprofunde nas preferências de {especialidade} do cliente {user_name} "
            f"e recomende opções ou pergunte detalhes para preparar a visita com nosso corretor humano responsável."
        )
    }, ensure_ascii=False)

def tool_buscar_imoveis(args: Dict[str, Any], imoveis_path: str, load_json_fn) -> str:
    """Busca imóveis com filtros por modalidade, região, tipo, preço e dormitórios."""
    imoveis = load_json_fn(imoveis_path)
    modalidade = args.get("modalidade")
    regiao = args.get("regiao", "").lower()
    tipo = args.get("tipo", "").lower()
    preco_max = args.get("preco_max")
    quartos = args.get("quartos")

    resultados = []
    for im in imoveis:
        if modalidade and modalidade not in im.get("modalidade", []):
            continue
        if tipo and tipo not in im.get("tipo", "").lower():
            continue
        if regiao:
            texto_busca = f"{im.get('regiao', '')} {im.get('bairro', '')}".lower()
            if regiao not in texto_busca:
                continue
        if preco_max:
            preco_imovel = im.get("preco") or im.get("preco_aluguel") or 0
            if preco_imovel > preco_max:
                continue
        if quartos and im.get("quartos", 0) < quartos:
            continue
        resultados.append(im)

    if not resultados:
        return json.dumps({
            "mensagem": "Nenhum imóvel encontrado exatamente com esses filtros. Apresente os imóveis mais próximos da base.",
            "sugestoes_disponiveis": imoveis[:3]
        }, ensure_ascii=False)

    return json.dumps(resultados, ensure_ascii=False)

def tool_consultar_agenda(args: Dict[str, Any], corretores_path: str, load_json_fn) -> str:
    """Retorna corretores e seus horários disponíveis filtrados por especialidade."""
    corretores = load_json_fn(corretores_path)
    especialidade = args.get("especialidade", "").lower()
    if especialidade:
        filtrados = [c for c in corretores if especialidade in c.get("especialidade", "").lower()]
        if filtrados:
            return json.dumps(filtrados, ensure_ascii=False)
    return json.dumps(corretores, ensure_ascii=False)

def tool_confirmar_agendamento(
    telegram_id: int,
    user_name: str,
    args: Dict[str, Any],
    leads_path: str,
    load_json_fn,
    save_json_fn
) -> str:
    """Registra a visita/reunião agendada na base de leads."""
    leads = load_json_fn(leads_path)
    lead = next((l for l in leads if l.get("telegram_id") == telegram_id), None)
    if not lead:
        lead = {
            "lead_id": f"LEAD-{telegram_id}",
            "telegram_id": telegram_id,
            "nome": user_name,
            "status": "visita_agendada",
            "agendamento": args,
            "ultima_interacao": datetime.now().isoformat()
        }
        leads.append(lead)
    else:
        lead["status"] = "visita_agendada"
        lead["agendamento"] = args
        lead["ultima_interacao"] = datetime.now().isoformat()

    save_json_fn(leads_path, leads)
    return json.dumps({"status": "sucesso", "mensagem": "Agendamento registrado com sucesso na base de dados!"}, ensure_ascii=False)

def tool_atualizar_lead(
    telegram_id: int,
    user_name: str,
    args: Dict[str, Any],
    leads_path: str,
    load_json_fn,
    save_json_fn
) -> str:
    """Atualiza a qualificação e o resumo executivo do lead para os corretores."""
    leads = load_json_fn(leads_path)
    lead = next((l for l in leads if l.get("telegram_id") == telegram_id), None)
    if not lead:
        lead = {
            "lead_id": f"LEAD-{telegram_id}",
            "telegram_id": telegram_id,
            "nome": user_name,
            "intencao": args.get("intencao"),
            "status": "qualificado",
            "score_qualificacao": args.get("score", 85),
            "criterios": args.get("criterios", {}),
            "resumo_corretor": args.get("resumo_corretor"),
            "ultima_interacao": datetime.now().isoformat(),
            "necessita_follow_up": False
        }
        leads.append(lead)
    else:
        lead["intencao"] = args.get("intencao", lead.get("intencao"))
        lead["status"] = "qualificado"
        if "score" in args:
            lead["score_qualificacao"] = args["score"]
        if "criterios" in args:
            lead["criterios"] = args["criterios"]
        lead["resumo_corretor"] = args.get("resumo_corretor", lead.get("resumo_corretor"))
        lead["ultima_interacao"] = datetime.now().isoformat()
        lead["necessita_follow_up"] = False

    save_json_fn(leads_path, leads)
    return json.dumps({"status": "sucesso", "mensagem": "Lead qualificado e resumo salvo com sucesso!"}, ensure_ascii=False)

def tool_enviar_fotos_imovel(
    telegram_id: int,
    args: Dict[str, Any],
    imoveis_path: str,
    fotos_pendentes_dict: dict,
    load_json_fn
) -> str:
    """Localiza o imóvel e enfileira fotos oficiais para despacho no Telegram."""
    imoveis = load_json_fn(imoveis_path)
    imovel_id = args.get("imovel_id", "").strip()
    bairro_termo = args.get("bairro_ou_termo", "").strip().lower()

    imovel_alvo = None
    if imovel_id:
        imovel_alvo = next((im for im in imoveis if im.get("id", "").upper() == imovel_id.upper()), None)
    
    if not imovel_alvo and bairro_termo:
        imovel_alvo = next((im for im in imoveis if bairro_termo in im.get("bairro", "").lower() or bairro_termo in im.get("titulo", "").lower()), None)
    
    if not imovel_alvo and imoveis:
        imovel_alvo = imoveis[0]

    if imovel_alvo:
        fotos = obter_fotos_imovel(imovel_alvo)
        titulo = imovel_alvo.get("titulo", "Imóvel Prime")
        fotos_pendentes_dict[telegram_id] = [
            {"url": f, "legenda": f"📸 {titulo} ({imovel_alvo.get('id')})"}
            for f in fotos
        ]
        return json.dumps({
            "status": "sucesso",
            "imovel_id": imovel_alvo.get("id"),
            "imovel_titulo": titulo,
            "qtd_fotos": len(fotos),
            "mensagem": f"As {len(fotos)} fotos oficiais do imóvel '{titulo}' foram despachadas com sucesso para o Telegram do cliente! Convide-o para agendar visita."
        }, ensure_ascii=False)
    else:
        return json.dumps({"status": "erro", "mensagem": "Imóvel não encontrado para envio de fotos."}, ensure_ascii=False)
