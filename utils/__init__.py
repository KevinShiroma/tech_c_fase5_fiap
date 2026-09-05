"""
Módulo de utilitários e serviços do Bot SDR Imobiliário Prime.
Componentes modulares para atendimento, IA, ferramentas e persistência.
"""

from .helpers import (
    configurar_logger,
    is_user_allowed,
    get_nome_agente_log,
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
from .catalog import FOTOS_CATALOGO_MAP, obter_fotos_imovel
from .prompts import (
    get_system_prompt_for_agent,
    get_triagem_prompt,
    get_compra_prompt,
    get_aluguel_prompt,
    get_investimento_prompt
)
from .tools import get_tools_definition
from .voice import transcrever_audio, converter_para_wav

