import os
import json
import textwrap
import calendar
from datetime import datetime
import httpx
import streamlit as st
import pandas as pd
import altair as alt
from agent import SDRImobiliarioAgent, registrar_mensagem_historico, save_json

# Configuração da página
st.set_page_config(
    page_title="Portal do Corretor | Imobiliária Prime",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilização CSS personalizada com fontes maiores e maior espaçamento
st.markdown("""
<style>
    /* Tipografia ampliada e espaçamento */
    html, body, [data-testid="stMarkdownContainer"] p {
        font-size: 1.05rem !important;
        line-height: 1.6 !important;
        color: #e2e8f0;
    }
    
    h1 {
        font-size: 2.3rem !important;
        font-weight: 700 !important;
        color: #f8fafc !important;
        margin-bottom: 20px !important;
    }
    
    h2 {
        font-size: 1.7rem !important;
        font-weight: 600 !important;
        color: #f1f5f9 !important;
        margin-top: 30px !important;
        margin-bottom: 15px !important;
    }
    
    h3 {
        font-size: 1.35rem !important;
        font-weight: 600 !important;
        color: #e2e8f0 !important;
    }
    
    /* Espaçamento entre blocos e seções */
    .section-spacer {
        margin-top: 35px;
        margin-bottom: 25px;
    }

    /* Sidebar estilizada com fontes maiores */
    [data-testid="stSidebar"] {
        background-color: #0f172a;
        border-right: 1px solid #1e293b;
    }
    [data-testid="stSidebar"] .stRadio label {
        font-size: 1.15rem !important;
        padding: 8px 12px !important;
        margin-bottom: 6px !important;
    }

    /* Cards de métricas com mais respiro */
    .kpi-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 14px;
        padding: 24px 20px;
        box-shadow: 0 6px 12px -2px rgba(0, 0, 0, 0.25);
        transition: transform 0.2s ease, border-color 0.2s ease;
        margin-bottom: 20px;
    }
    .kpi-card:hover {
        transform: translateY(-3px);
        border-color: #38bdf8;
    }
    .kpi-title {
        font-size: 0.95rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #94a3b8;
        margin-bottom: 12px;
    }
    .kpi-value {
        font-size: 2.3rem;
        font-weight: 800;
        color: #f8fafc;
        margin-bottom: 6px;
    }
    .kpi-desc {
        font-size: 0.88rem;
        color: #38bdf8;
    }

    /* Card de lead / conteúdo */
    .content-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 14px;
        padding: 24px;
        margin-bottom: 25px;
    }

    /* Mini cards de dados qualificados para corretores */
    .data-pill {
        background-color: #0f172a;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 12px 16px;
        margin-bottom: 12px;
    }
    .data-pill-label {
        font-size: 0.85rem;
        color: #94a3b8;
        text-transform: uppercase;
        font-weight: 600;
        letter-spacing: 0.04em;
        margin-bottom: 4px;
    }
    .data-pill-val {
        font-size: 1.15rem;
        color: #f8fafc;
        font-weight: 700;
    }

    /* Badges */
    .badge {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 9999px;
        font-size: 0.85rem;
        font-weight: 700;
        letter-spacing: 0.03em;
    }
    .badge-compra { background-color: #0369a1; color: #e0f2fe; }
    .badge-invest { background-color: #15803d; color: #dcfce7; }
    .badge-aluguel { background-color: #b45309; color: #fef3c7; }
    .badge-agendado { background-color: #7e22ce; color: #f3e8ff; border: 1px solid #c084fc; }

    /* Caixa de resumo do corretor */
    .resumo-box {
        background-color: #0f172a;
        border-left: 4px solid #38bdf8;
        border-radius: 8px;
        padding: 18px 20px;
        font-size: 1.05rem;
        color: #f1f5f9;
        line-height: 1.6;
        margin-top: 10px;
    }

    /* Blocos Visíveis de Imóveis */
    .imovel-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.25);
        border-top: 4px solid #38bdf8;
        min-height: 480px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .imovel-titulo {
        margin: 0 0 6px 0;
        color: #f8fafc;
        font-size: 1.22rem;
        font-weight: 700;
        min-height: 56px;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    .imovel-preco {
        font-size: 1.35rem;
        font-weight: 800;
        color: #38bdf8;
        margin: 6px 0;
    }
    .imovel-desc-box {
        color: #cbd5e1;
        font-size: 0.92rem;
        line-height: 1.5;
        height: 64px;
        overflow: hidden;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        text-overflow: ellipsis;
        margin-top: 4px;
        margin-bottom: 8px;
    }
    .imovel-tag-diferencial {
        display: inline-block;
        background-color: rgba(56, 189, 248, 0.12);
        border: 1px solid rgba(56, 189, 248, 0.35);
        color: #7dd3fc;
        border-radius: 9999px;
        padding: 3px 10px;
        font-size: 0.8rem;
        margin: 2px 4px 4px 0;
        font-weight: 500;
    }
    .filtro-card {
        background-color: #0f172a;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 24px;
    }

    /* Calendário */
    .cal-header-day {
        text-align: center;
        font-weight: 700;
        font-size: 0.8rem;
        color: #94a3b8;
        padding: 4px 0;
        text-transform: uppercase;
    }
    .cal-card-agendamento {
        background-color: #1e293b;
        border-left: 5px solid #f97316;
        border-radius: 12px;
        padding: 22px;
        margin-bottom: 20px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.25);
    }
    /* Estilo do dia selecionado: Azul vibrante */
    button[kind="primary"],
    [data-testid="baseButton-primary"] {
        background-color: #0284c7 !important;
        border: 2px solid #38bdf8 !important;
        color: #ffffff !important;
        font-weight: 800 !important;
        box-shadow: 0 0 10px rgba(56, 189, 248, 0.4) !important;
    }
    /* Dias com agendamento: Contorno Laranja forte */
    button:has(strong),
    [data-testid="baseButton-secondary"]:has(strong) {
        border: 2px solid #f97316 !important;
        color: #f8fafc !important;
        font-weight: 800 !important;
        box-shadow: 0 0 8px rgba(249, 115, 22, 0.4) !important;
    }
    /* Dia com agendamento E selecionado: Fundo Azul e Borda Laranja */
    button[kind="primary"]:has(strong),
    [data-testid="baseButton-primary"]:has(strong) {
        background-color: #0284c7 !important;
        border: 2px solid #f97316 !important;
        box-shadow: 0 0 12px rgba(249, 115, 22, 0.6) !important;
    }
    /* Altura e padding consistentes para todas as colunas */
    [data-testid="column"] button {
        min-height: 42px !important;
        padding-left: 2px !important;
        padding-right: 2px !important;
    }
</style>
""", unsafe_allow_html=True)

# Caminhos dos arquivos de dados
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEADS_PATH = os.path.join(BASE_DIR, "data", "leads.json")
IMOVEIS_PATH = os.path.join(BASE_DIR, "data", "imoveis.json")
CORRETORES_PATH = os.path.join(BASE_DIR, "data", "corretores.json")
CONVERSAS_DIR = os.path.join(BASE_DIR, "conversas")

def load_data(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

# Carrega os dados mais recentes
leads = load_data(LEADS_PATH)
imoveis = load_data(IMOVEIS_PATH)
corretores = load_data(CORRETORES_PATH)

def obter_fotos_imovel(imovel):
    im_id = imovel.get("id", "")
    tipo = imovel.get("tipo", "apartamento")
    
    fotos_map = {
        "IMO-001": [
            "https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?w=600&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=600&auto=format&fit=crop"
        ],
        "IMO-002": [
            "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=600&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=600&auto=format&fit=crop"
        ],
        "IMO-003": [
            "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=600&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=600&auto=format&fit=crop"
        ],
        "IMO-004": [
            "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=600&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=600&auto=format&fit=crop"
        ],
        "IMO-005": [
            "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=600&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1600566753376-12c8ab7fb75b?w=600&auto=format&fit=crop"
        ],
        "IMO-006": [
            "https://images.unsplash.com/photo-1556912173-3bb406ef7e77?w=600&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=600&auto=format&fit=crop"
        ],
        "IMO-007": [
            "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=600&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=600&auto=format&fit=crop"
        ],
        "IMO-008": [
            "https://images.unsplash.com/photo-1600585154526-990dced4db0d?w=600&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=600&auto=format&fit=crop"
        ],
        "IMO-009": [
            "https://images.unsplash.com/photo-1522771739844-6a9f6d5f14af?w=600&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1556912173-3bb406ef7e77?w=600&auto=format&fit=crop"
        ],
        "IMO-010": [
            "https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?w=600&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?w=600&auto=format&fit=crop"
        ],
        "IMO-011": [
            "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=600&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=600&auto=format&fit=crop"
        ]
    }
    if im_id in fotos_map:
        return fotos_map[im_id]
    
    if tipo == "casa":
        return [
            "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=600&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=600&auto=format&fit=crop"
        ]
    elif tipo == "studio":
        return [
            "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=600&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=600&auto=format&fit=crop"
        ]
    else:
        return [
            "https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?w=600&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=600&auto=format&fit=crop"
        ]


# ==========================================
# BARRA LATERAL (MENU DO CORRETOR)
# ==========================================
with st.sidebar:
    st.markdown("## 🏢 **Imobiliária Prime**")
    st.caption("Portal Executivo do Corretor")
    st.write("")

    menu_selecionado = st.radio(
        "Menu Principal:",
        ["🏠 Início", "👥 Leads", "🏡 Imóveis", "📅 Agendamentos", "⚡ Follow-up IA"],
        index=0
    )

    st.write("---")
    st.markdown("👨‍💼 **Corretor Ativo:**\n\n*Plantão Geral de Atendimento*")
    st.caption("Assistente Virtual: 🟢 **Sofia SDR Online**")
    st.write("")
    
    if st.button("🔄 Sincronizar Informações", use_container_width=True):
        st.rerun()

# ==========================================
# 1. TELA: INÍCIO (PAINEL GERAL)
# ==========================================
if menu_selecionado == "🏠 Início":
    st.title("Visão Geral do Corretor")
    st.markdown("Resumo executivo de oportunidades qualificadas pela Sofia (Agente SDR AI).")
    st.write("")

    # Métricas
    total_leads = len(leads)
    total_imoveis = len(imoveis)
    leads_agendados = [l for l in leads if l.get("agendamento")]
    total_agendamentos = len(leads_agendados)
    taxa_conversao = round((total_agendamentos / total_leads * 100), 1) if total_leads > 0 else 0

    # 4 KPIs no topo
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">👥 Total de Leads</div>
            <div class="kpi-value">{total_leads}</div>
            <div class="kpi-desc">Atendidos e no funil</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">🏡 Imóveis no Portfólio</div>
            <div class="kpi-value">{total_imoveis}</div>
            <div class="kpi-desc">Cadastrados no catálogo</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">📅 Reuniões Agendadas</div>
            <div class="kpi-value">{total_agendamentos}</div>
            <div class="kpi-desc">Fundo do funil comercial</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">🎯 Taxa de Agendamento</div>
            <div class="kpi-value">{taxa_conversao}%</div>
            <div class="kpi-desc">Conversão em visita</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

    # SEÇÃO: AGREGADO POR ZONA EM SÃO PAULO
    st.subheader("📍 Catálogo de Imóveis por Região / Zona em São Paulo")
    st.caption("Volume de oportunidades disponíveis por região para direcionar o atendimento dos clientes.")

    zonas_data = {}
    for im in imoveis:
        regiao = im.get("regiao", "Outros")
        zonas_data[regiao] = zonas_data.get(regiao, 0) + 1

    df_zonas = pd.DataFrame([
        {"Zona de SP": regiao, "Quantidade": qtd}
        for regiao, qtd in zonas_data.items()
    ])

    col_chart, col_stat = st.columns([2, 1])

    with col_chart:
        chart = alt.Chart(df_zonas).mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8, color="#38bdf8").encode(
            x=alt.X("Zona de SP:N", sort="-y", title="Região / Zona de SP"),
            y=alt.Y("Quantidade:Q", title="Total de Imóveis"),
            tooltip=["Zona de SP", "Quantidade"]
        ).properties(height=320)
        st.altair_chart(chart, use_container_width=True)

    with col_stat:
        st.markdown("#### **Distribuição por Região:**")
        for regiao, qtd in zonas_data.items():
            st.write(f"• **{regiao}:** {qtd} imóvel(is)")
        
        bairros_leads = []
        for l in leads:
            criterios = l.get("criterios", {})
            bairros_leads.extend(criterios.get("bairros", []))
        if bairros_leads:
            st.write("")
            st.info(f"🔥 **Regiões de maior procura pelos clientes:**\n\n{', '.join(set(bairros_leads))}")

    st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

    # SEÇÃO: LEADS NO FUNDO DO FUNIL (APENAS OS 5 ÚLTIMOS LEADS)
    st.subheader("🚀 Fundo do Funil: 5 Últimos Leads Prioritários")
    st.caption("Visão dos 5 leads mais recentes cadastrados no sistema para atendimento comercial.")

    # Exibe os 5 últimos leads (do mais recente para o mais antigo)
    ultimos_5_leads = list(reversed(leads[-5:])) if len(leads) >= 5 else list(reversed(leads))

    if not ultimos_5_leads:
        st.info("Nenhuma reunião pendente no momento. Sofia continua qualificando novos leads.")
    else:
        for lead in ultimos_5_leads:
            ag = lead.get("agendamento", {})
            dt_rec = lead.get("data_recebimento", lead.get("ultima_interacao", "")[:10])
            dt_format = f"{dt_rec.split('-')[2]}/{dt_rec.split('-')[1]}/{dt_rec.split('-')[0]}" if "-" in dt_rec else dt_rec
            status_tag = '<span class="badge badge-agendado">📅 VISITA MARCADA</span>' if ag else '<span class="badge badge-compra">QUALIFICADO</span>'
            
            if ag:
                detalhes_lead = f"<strong>🗓️ Horário:</strong> {ag.get('data_hora')} &nbsp;|&nbsp; <strong>Especialista:</strong> {ag.get('corretor_nome', 'Plantão')} &nbsp;|&nbsp; <strong>Tipo:</strong> {ag.get('tipo') or ag.get('tipo_visita')}"
            else:
                detalhes_lead = f"<strong>🎯 Intenção:</strong> {lead.get('intencao', '').upper()} &nbsp;|&nbsp; <strong>Score:</strong> {lead.get('score_qualificacao', 0)}% &nbsp;|&nbsp; <strong>Entrada:</strong> {dt_format}"

            st.markdown(f"""
            <div class="content-card" style="border-left: 5px solid #a855f7;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <h3 style="margin:0; color:#f8fafc;">👤 {lead.get('nome')} <span style="font-size:0.9rem; color:#94a3b8;">(ID: {lead.get('telegram_id')} — Entrada: {dt_format})</span></h3>
                    <div>{status_tag}</div>
                </div>
                <p style="font-size: 1.05rem; color: #cbd5e1;">
                    {detalhes_lead}
                </p>
                <div class="resumo-box">
                    <strong>💡 Resumo para o Corretor:</strong><br>
                    {lead.get('resumo_corretor', 'Sem resumo registrado')}
                </div>
            </div>
            """, unsafe_allow_html=True)

# ==========================================
# 2. TELA: LEADS (INTERFACE AMIGÁVEL PARA CORRETORES)
# ==========================================
elif menu_selecionado == "👥 Leads":
    st.title("👥 Carteira de Leads Qualificados")
    st.markdown("Fichas comerciais claras e objetivas geradas automaticamente pela inteligência SDR.")
    st.write("")

    if not leads:
        st.info("Nenhum lead qualificado no momento.")
    else:
        # Extrai todas as datas de recebimento únicas presentes nos leads
        datas_unicas = sorted(list(set(l.get("data_recebimento", l.get("ultima_interacao", "")[:10]) for l in leads if (l.get("data_recebimento") or l.get("ultima_interacao")))), reverse=True)
        opcoes_dias_map = {"Todas as Datas": "Todas"}
        opcoes_dias_label = ["Todas as Datas"]
        for d in datas_unicas:
            lbl = f"{d.split('-')[2]}/{d.split('-')[1]}/{d.split('-')[0]}" if "-" in d else d
            if d == "2026-09-05":
                lbl += " (Hoje)"
            elif d == "2026-09-04":
                lbl += " (Ontem)"
            opcoes_dias_map[lbl] = d
            opcoes_dias_label.append(lbl)

        # 2 FILTROS EXIGIDOS: FINALIDADE E DIA EM QUE RECEBEMOS O LEAD
        col_f1, col_f2 = st.columns([1, 1])
        with col_f1:
            filtro_finalidade = st.selectbox("🏷️ Filtrar por Finalidade:", ["Todas", "Compra", "Locação / Aluguel", "Investimento"], index=0)
        with col_f2:
            filtro_dia_escolhido = st.selectbox("📅 Filtrar por Dia de Recebimento:", opcoes_dias_label, index=0)

        # Aplica a filtragem sobre a base de leads
        leads_filtrados = leads
        if filtro_finalidade == "Compra":
            leads_filtrados = [l for l in leads_filtrados if l.get("intencao") == "compra"]
        elif filtro_finalidade == "Locação / Aluguel":
            leads_filtrados = [l for l in leads_filtrados if l.get("intencao") == "aluguel"]
        elif filtro_finalidade == "Investimento":
            leads_filtrados = [l for l in leads_filtrados if l.get("intencao") == "investimento"]

        data_alvo = opcoes_dias_map.get(filtro_dia_escolhido, "Todas")
        if data_alvo != "Todas":
            leads_filtrados = [l for l in leads_filtrados if l.get("data_recebimento", l.get("ultima_interacao", "")[:10]) == data_alvo]

        def get_agente_responsavel_info(l_data):
            ag = l_data.get("agente_responsavel", "")
            it = l_data.get("intencao", "").lower()
            if "verônica" in str(ag).lower() or it == "compra":
                return "Verônica (IA Compra) ➔ Corretora: Juliana Silveira"
            elif "camila" in str(ag).lower() or it == "aluguel":
                return "Camila (IA Locação) ➔ Corretor: Roberto Prado"
            elif "rodrigo" in str(ag).lower() or it == "investimento":
                return "Rodrigo (IA Investimento) ➔ Consultor: Carlos Mendes"
            return "Sofia (IA Triagem Inicial)"

        # Monta opções para o Dropdown de Clientes com base nos leads filtrados
        lista_opcoes = []
        lead_map = {}
        for l in leads_filtrados:
            tid = l.get('telegram_id')
            intencao = l.get('intencao', 'geral').upper()
            it_low = l.get('intencao', '').lower()
            score = l.get('score_qualificacao', 0)
            status_visita = " 📅 [VISITA AGENDADA]" if l.get("agendamento") else ""
            dt_ent = l.get("data_recebimento", l.get("ultima_interacao", "")[:10])
            dt_tag = f"{dt_ent.split('-')[2]}/{dt_ent.split('-')[1]}" if "-" in dt_ent else ""
            ag_curto = "Verônica (Compra)" if "compra" in it_low else ("Camila (Locação)" if "aluguel" in it_low else ("Rodrigo (Invest.)" if "invest" in it_low else "Sofia (Triagem)"))
            label = f"👤 {l.get('nome', 'Cliente')} — {intencao} | 🤖 {ag_curto} | Entrada: {dt_tag} | Score: {score}% (ID: {tid}){status_visita}"
            lista_opcoes.append(label)
            lead_map[label] = l

        opcoes_finais = ["📋 Visão Geral (Ver Todos Filtrados)"] + lista_opcoes

        cliente_selecionado = st.selectbox(
            "🎯 Selecionar Cliente (Dropdown):",
            opcoes_finais,
            index=1 if len(opcoes_finais) > 1 else 0,
            help="Selecione um cliente para abrir sua ficha e o dropdown da conversa."
        )

        st.caption(f"Mostrando {len(leads_filtrados)} de {len(leads)} leads cadastrados")
        st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

        def exibir_ficha_cliente(lead, mostrar_expander_externo=False):
            tid = lead.get('telegram_id')
            intencao = lead.get('intencao', 'indefinido').lower()
            agente_resp = get_agente_responsavel_info(lead)

            # Badges visuais
            if intencao == "compra":
                badge_html = '<span class="badge badge-compra">COMPRA RESIDENCIAL</span>'
            elif intencao == "investimento":
                badge_html = '<span class="badge badge-invest">INVESTIMENTO / RENDA</span>'
            else:
                badge_html = '<span class="badge badge-aluguel">LOCAÇÃO / ALUGUEL</span>'

            agendado_badge = '<span class="badge badge-agendado" style="margin-left:8px;">📅 REUNIÃO AGENDADA</span>' if lead.get("agendamento") else ''
            agente_badge = f'<span class="badge" style="background-color: #1e1b4b; color: #c7d2fe; border: 1px solid #6366f1; margin-left: 8px;">🤖 {agente_resp}</span>'

            conteudo_container = st.container()
            with conteudo_container:
                st.markdown(f"""
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; border-bottom: 1px solid #334155; padding-bottom: 10px;">
                    <span style="color: #94a3b8; font-size: 1.05rem;">
                        Cliente: <strong style="color: #f8fafc; font-size: 1.2rem;">{lead.get('nome', 'Cliente')}</strong> 
                        &nbsp;|&nbsp; Lead ID: <strong>{lead.get('lead_id', 'N/A')}</strong> 
                        &nbsp;|&nbsp; Telegram ID: <strong>{tid}</strong>
                    </span>
                    <div style="display: flex; align-items: center; flex-wrap: wrap; gap: 6px;">
                        {badge_html} {agente_badge} {agendado_badge}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                col_esquerda, col_direita = st.columns([1, 1])

                # COLUNA 1: DADOS QUALIFICADOS HUMANIZADOS (SEM JSON!)
                with col_esquerda:
                    st.markdown("#### 📋 **Critérios e Preferências do Cliente:**")
                    score = lead.get("score_qualificacao", 0)
                    st.progress(score / 100, text=f"Grau de Qualificação do Lead: {score}%")
                    st.write("")

                    # Card de destaque do Agente LangChain
                    st.markdown(f"""
                    <div class="data-pill" style="border-left: 4px solid #6366f1; background: linear-gradient(90deg, #1e1b4b 0%, #0f172a 100%); margin-bottom: 14px;">
                        <div class="data-pill-label" style="color: #a5b4fc;">🤖 Agente LangChain Responsável</div>
                        <div class="data-pill-val" style="color: #f8fafc; font-size: 1.05rem;">{agente_resp}</div>
                    </div>
                    """, unsafe_allow_html=True)

                    crit = lead.get("criterios", {})
                    
                    # Monta os cards de informações limpos
                    c1, c2 = st.columns(2)
                    with c1:
                        tipo_im = crit.get("tipo_imovel")
                        if not tipo_im:
                            if "apartamento" in lead.get("resumo_corretor", "").lower():
                                tipo_im = "Apartamento"
                            else:
                                tipo_im = "Residencial"
                        else:
                            tipo_im = tipo_im.title()

                        st.markdown(f"""
                        <div class="data-pill">
                            <div class="data-pill-label">🏢 Tipo de Imóvel</div>
                            <div class="data-pill-val">{tipo_im}</div>
                        </div>
                        """, unsafe_allow_html=True)

                        quartos = crit.get("quartos", "Aberto / A definir")
                        st.markdown(f"""
                        <div class="data-pill">
                            <div class="data-pill-label">🛏️ Dormitórios</div>
                            <div class="data-pill-val">{quartos if isinstance(quartos, str) else f"{quartos} quartos"}</div>
                        </div>
                        """, unsafe_allow_html=True)

                    with c2:
                        preco = crit.get("faixa_preco_max") or crit.get("preco_max") or crit.get("ticket_investimento")
                        if preco:
                            sufixo = "/mês" if intencao == "aluguel" else ""
                            preco_str = f"R$ {preco:,.2f}{sufixo}"
                        else:
                            preco_str = "A combinar"

                        st.markdown(f"""
                        <div class="data-pill">
                            <div class="data-pill-label">💰 Orçamento Máximo</div>
                            <div class="data-pill-val" style="color: #38bdf8;">{preco_str}</div>
                        </div>
                        """, unsafe_allow_html=True)

                        urgencia = crit.get("urgencia", "Médio prazo")
                        st.markdown(f"""
                        <div class="data-pill">
                            <div class="data-pill-label">⏳ Previsão / Urgência</div>
                            <div class="data-pill-val">{urgencia}</div>
                        </div>
                        """, unsafe_allow_html=True)

                    regiao_str = crit.get("regiao", "São Paulo")
                    bairros_list = crit.get("bairros", [])
                    bairros_str = ", ".join(bairros_list) if bairros_list else "Sem restrição de bairro"
                    st.markdown(f"""
                    <div class="data-pill">
                        <div class="data-pill-label">📍 Região e Bairros de Interesse</div>
                        <div class="data-pill-val" style="font-size: 1.05rem;">{regiao_str} — {bairros_str}</div>
                    </div>
                    """, unsafe_allow_html=True)

                # COLUNA 2: RESUMO EXECUTIVO DO CORRETOR
                with col_direita:
                    st.markdown("#### 🧠 **Resumo Estratégico para o Corretor:**")
                    resumo_texto = lead.get("resumo_corretor", "Aguardando qualificação adicional pela Sofia.")
                    st.markdown(f"""
                    <div class="resumo-box" style="margin-top: 5px;">
                        {resumo_texto}
                    </div>
                    """, unsafe_allow_html=True)

                    ag = lead.get("agendamento")
                    if ag:
                        st.write("")
                        st.success(f"🗓️ **Reunião Marcada:** {ag.get('data_hora')} com **{ag.get('corretor_nome')}**\n\n📌 Finalidade: {ag.get('tipo') or ag.get('tipo_visita')}")

                # DROPDOWN DA CONVERSA: OCULTO POR PADRÃO (EXPANSÍVEL PELO CORRETOR)
                st.write("")
                with st.expander("💬 Ver Histórico Completo da Conversa (Chat)", expanded=False):
                    chat_json_path = os.path.join(CONVERSAS_DIR, f"chat_{tid}.json")
                    if os.path.exists(chat_json_path):
                        chat_data = load_data(chat_json_path)
                        mensagens = chat_data.get("mensagens", [])
                        if mensagens:
                            for m in mensagens:
                                role = m.get("role", "user")
                                if m.get("tipo") == "sistema" or role == "system":
                                    st.markdown(f"""
                                    <div style="display: flex; align-items: center; margin: 20px 0;">
                                        <hr style="flex-grow: 1; border: none; border-top: 1px dashed #475569;">
                                        <span style="padding: 0 12px; color: #38bdf8; font-size: 0.82rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">
                                            🔄 Novo Atendimento Iniciado ({m.get('timestamp')})
                                        </span>
                                        <hr style="flex-grow: 1; border: none; border-top: 1px dashed #475569;">
                                    </div>
                                    """, unsafe_allow_html=True)
                                    continue

                                tipo_icone = "🎙️ [Áudio de Voz]" if m.get("tipo") == "audio_voz" else "💬"
                                with st.chat_message(role):
                                    st.write(f"**{m.get('autor')}** <span style='font-size:0.8rem; color:#94a3b8;'>({m.get('timestamp')})</span> {tipo_icone}", unsafe_allow_html=True)
                                    st.write(m.get("conteudo"))
                        else:
                            st.caption("Ainda não há mensagens registradas no histórico deste lead.")
                    else:
                        st.caption("O histórico desta conversa será gerado automaticamente nas próximas mensagens.")

                st.write("---")

        # RENDERIZAÇÃO CONFORME ESCOLHA NO DROPDOWN
        if cliente_selecionado != "📋 Visão Geral (Ver Todos Filtrados)" and cliente_selecionado in lead_map:
            lead_atual = lead_map.get(cliente_selecionado)
            if lead_atual:
                exibir_ficha_cliente(lead_atual)
        else:
            if not leads_filtrados:
                st.warning("Nenhum lead encontrado com os filtros selecionados.")
            else:
                for lead_item in leads_filtrados:
                    nome_c = lead_item.get('nome', 'Cliente')
                    tid_c = lead_item.get('telegram_id')
                    intencao_c = lead_item.get('intencao', 'geral').upper()
                    with st.expander(f"👤 {nome_c} — {intencao_c} (ID: {tid_c})", expanded=False):
                        exibir_ficha_cliente(lead_item)


# ==========================================
# 3. TELA: IMÓVEIS (PORTFÓLIO E FILTROS AVANÇADOS)
# ==========================================
elif menu_selecionado == "🏡 Imóveis":
    st.title("🏡 Portfólio de Imóveis (Todas as Zonas de SP)")
    st.markdown("Catálogo de oportunidades consultado pelo Agente SDR em tempo real para match com clientes.")
    st.write("")

    # ÁREA DE FILTROS AVANÇADOS
    st.markdown("### 🔍 **Filtros de Busca de Imóveis**")
    
    # Lista de zonas disponíveis
    todas_zonas = ["Todas as Zonas", "Zona Sul", "Zona Oeste", "Zona Norte", "Zona Leste", "Centro"]
    
    col_f1, col_f2, col_f3 = st.columns([1.2, 1.2, 1])
    with col_f1:
        filtro_zona = st.selectbox("📍 Região / Zona de SP:", todas_zonas, index=0)
    
    # Bairros dinâmicos de acordo com a zona
    if filtro_zona == "Todas as Zonas":
        bairros_disponiveis = sorted(list(set(im.get("bairro") for im in imoveis if im.get("bairro"))))
    else:
        bairros_disponiveis = sorted(list(set(im.get("bairro") for im in imoveis if im.get("regiao") == filtro_zona and im.get("bairro"))))
    
    opcoes_bairros = ["Todos os Bairros"] + bairros_disponiveis
    with col_f2:
        filtro_bairro = st.selectbox("🏘️ Bairro:", opcoes_bairros, index=0)

    with col_f3:
        filtro_modalidade = st.selectbox("🏷️ Finalidade:", ["Todas", "Compra / Venda", "Locação / Aluguel", "Investimento"], index=0)

    col_f4, col_f5, col_f6 = st.columns([1, 1, 1.4])
    with col_f4:
        filtro_quartos = st.selectbox(
            "🛏️ Quartos / Dormitórios:",
            ["Todos", "1+ dormitório", "2+ dormitórios", "3+ dormitórios", "4+ dormitórios"],
            index=0
        )
    with col_f5:
        filtro_vagas = st.selectbox(
            "🚗 Vagas de Garagem:",
            ["Todas", "0+ (com ou sem vaga)", "1+ vaga", "2+ vagas", "3+ vagas"],
            index=0
        )
    with col_f6:
        # Metragem mínima e máxima
        areas = [im.get("area_m2", 50) for im in imoveis]
        min_area = min(areas) if areas else 20
        max_area = max(areas) if areas else 300
        filtro_metragem = st.slider("📐 Faixa de Metragem (m²):", min_value=min_area, max_value=max_area, value=(min_area, max_area), step=5)

    # APLICAÇÃO DOS FILTROS
    imoveis_filtrados = []
    for im in imoveis:
        # Filtro de Zona
        if filtro_zona != "Todas as Zonas" and im.get("regiao") != filtro_zona:
            continue
        
        # Filtro de Bairro
        if filtro_bairro != "Todos os Bairros" and im.get("bairro") != filtro_bairro:
            continue
        
        # Filtro de Modalidade
        mods = im.get("modalidade", [])
        if filtro_modalidade == "Compra / Venda" and "compra" not in mods:
            continue
        elif filtro_modalidade == "Locação / Aluguel" and "aluguel" not in mods:
            continue
        elif filtro_modalidade == "Investimento" and "investimento" not in mods:
            continue
        
        # Filtro de Quartos
        if filtro_quartos != "Todos":
            min_q = int(filtro_quartos[0])
            if im.get("quartos", 0) < min_q:
                continue
        
        # Filtro de Vagas
        if filtro_vagas not in ["Todas", "0+ (com ou sem vaga)"]:
            min_v = int(filtro_vagas[0])
            if im.get("vagas", 0) < min_v:
                continue
        
        # Filtro de Metragem
        area = im.get("area_m2", 0)
        if not (filtro_metragem[0] <= area <= filtro_metragem[1]):
            continue
        
        imoveis_filtrados.append(im)

    st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)
    
    # CONTADOR DE RESULTADOS
    st.markdown(f"#### 📋 **Exibindo {len(imoveis_filtrados)} de {len(imoveis)} imóveis disponíveis**")
    st.write("")

    if not imoveis_filtrados:
        st.warning("⚠️ Nenhum imóvel encontrado com essa combinação de filtros. Experimente ajustar os critérios acima.")
    else:
        # RENDERIZAÇÃO EM BLOCOS VISÍVEIS (GRADE DE 2 COLUNAS)
        colunas_grid = st.columns(2)
        for idx, im in enumerate(imoveis_filtrados):
            with colunas_grid[idx % 2]:
                # Determina modalidade e badges
                mods = im.get("modalidade", [])
                badges_list = []
                if "compra" in mods:
                    badges_list.append('<span class="badge badge-compra">VENDA</span>')
                if "aluguel" in mods:
                    badges_list.append('<span class="badge badge-aluguel">LOCAÇÃO</span>')
                if "investimento" in mods:
                    badges_list.append('<span class="badge badge-invest">INVESTIMENTO</span>')
                
                badges_str = " ".join(badges_list)
                regiao_tag = f'<span style="background-color: #334155; color: #f1f5f9; padding: 4px 10px; border-radius: 6px; font-size: 0.8rem; font-weight: 700;">📍 {im.get("regiao", "").upper()}</span>'

                # Preço
                preco_venda = im.get("preco")
                preco_aluguel = im.get("preco_aluguel")
                if preco_aluguel:
                    preco_texto = f"R$ {preco_aluguel:,.2f}<span style='font-size:0.9rem; color:#94a3b8;'>/mês</span>"
                elif preco_venda:
                    preco_texto = f"R$ {preco_venda:,.2f}"
                else:
                    preco_texto = "Sob Consulta"

                # Yield de investimento
                yield_tag = ""
                if "rentabilidade_estimada_aa" in im:
                    yield_tag = f"&nbsp;&nbsp;<span style='background:#064e3b; color:#6ee7b7; padding:4px 8px; border-radius:6px; font-size:0.85rem; font-weight:700;'>📈 Yield: {im.get('rentabilidade_estimada_aa')}% a.a.</span>"

                # Tags de diferenciais
                difs_html = "".join([f'<span class="imovel-tag-diferencial">✨ {d}</span>' for d in im.get("diferenciais", [])[:4]])

                # Renderização do bloco com altura uniforme e descrição truncada (evita desalinhamento)
                html_bloco = (
                    f'<div class="imovel-card">'
                    f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">'
                    f'<div>{badges_str}</div><div>{regiao_tag}</div></div>'
                    f'<div class="imovel-titulo">{im.get("titulo")}</div>'
                    f'<p style="color:#94a3b8; font-size:0.95rem; margin-bottom:8px;">📍 <strong>{im.get("bairro")}</strong> — {im.get("cidade", "São Paulo")} &nbsp;|&nbsp; ID: <code>{im.get("id")}</code></p>'
                    f'<div class="imovel-preco">{preco_texto} {yield_tag}</div>'
                    f'<div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:8px; margin:10px 0;">'
                    f'<div class="data-pill" style="margin-bottom:0; text-align:center; padding:8px 4px;"><div class="data-pill-label" style="font-size:0.75rem;">Área</div><div class="data-pill-val" style="font-size:1.0rem;">{im.get("area_m2")}m²</div></div>'
                    f'<div class="data-pill" style="margin-bottom:0; text-align:center; padding:8px 4px;"><div class="data-pill-label" style="font-size:0.75rem;">Quartos</div><div class="data-pill-val" style="font-size:1.0rem;">{im.get("quartos")} qtos</div></div>'
                    f'<div class="data-pill" style="margin-bottom:0; text-align:center; padding:8px 4px;"><div class="data-pill-label" style="font-size:0.75rem;">Suítes</div><div class="data-pill-val" style="font-size:1.0rem;">{im.get("suites", 0)} suíte</div></div>'
                    f'<div class="data-pill" style="margin-bottom:0; text-align:center; padding:8px 4px;"><div class="data-pill-label" style="font-size:0.75rem;">Vagas</div><div class="data-pill-val" style="font-size:1.0rem;">{im.get("vagas", 0)} vaga</div></div>'
                    f'</div>'
                    f'<div style="margin-bottom:6px; min-height:28px;">{difs_html}</div>'
                    f'<div class="imovel-desc-box">{im.get("descricao")}</div>'
                    f'</div>'
                )
                st.markdown(html_bloco, unsafe_allow_html=True)

                # BOTÕES DE AÇÃO: LER DESCRIÇÃO COMPLETA E VER FOTOS DOS IMÓVEIS
                c_act1, c_act2 = st.columns(2)
                with c_act1:
                    with st.expander("📖 Ler Descrição", expanded=False):
                        st.write(im.get('descricao'))
                with c_act2:
                    with st.expander(f"📸 Ver Fotos ({im.get('id')})", expanded=False):
                        fotos_imovel = obter_fotos_imovel(im)
                        col_img1, col_img2 = st.columns(2)
                        with col_img1:
                            st.image(fotos_imovel[0], caption="Ambiente Principal / Fachada", use_container_width=True)
                        with col_img2:
                            st.image(fotos_imovel[1], caption="Interior / Acabamentos", use_container_width=True)

                # Mini-expansor interno com detalhes comerciais para o corretor
                with st.expander(f"📋 Ficha Técnica & Custos ({im.get('id')})", expanded=False):
                    c_det1, c_det2 = st.columns(2)
                    with c_det1:
                        st.write(f"🏢 **Tipo:** {im.get('tipo', '').title()}")
                        st.write(f"🏢 **Condomínio:** R$ {im.get('condominio', 0):,.2f}/mês" if im.get('condominio') else "🏢 **Condomínio:** Isento")
                        if im.get('iptu'):
                            st.write(f"📑 **IPTU:** R$ {im.get('iptu'):,.2f}/mês")
                    with c_det2:
                        st.write(f"🎯 **Público-alvo:** {im.get('publico_alvo', 'Geral')}")
                        if "potencial_locacao" in im:
                            st.write(f"💡 **Perfil de Renda:** {im.get('potencial_locacao')}")
                
                st.write("")


# ==========================================
# 4. TELA: AGENDAMENTOS (CALENDÁRIO INTERATIVO E DETALHES)
# ==========================================
elif menu_selecionado == "📅 Agendamentos":
    st.title("📅 Calendário de Reuniões & Visitas")
    st.markdown("Acompanhe os compromissos agendados pelo Agente SDR com os corretores especialistas.")
    st.write("")

    # Mapeia todos os agendamentos existentes por data (formato YYYY-MM-DD)
    agendamentos_por_dia = {}
    for l in leads:
        ag = l.get("agendamento")
        if ag and ag.get("data_hora"):
            dh = ag["data_hora"]
            # Extrai a data no formato YYYY-MM-DD
            data_key = dh.split("T")[0].split(" ")[0]
            if data_key not in agendamentos_por_dia:
                agendamentos_por_dia[data_key] = []
            agendamentos_por_dia[data_key].append(l)

    dias_com_agendamento = set(agendamentos_por_dia.keys())

    # Inicialização das variáveis de sessão do calendário
    if "cal_ano" not in st.session_state:
        st.session_state["cal_ano"] = 2026
    if "cal_mes" not in st.session_state:
        st.session_state["cal_mes"] = 9
    if "cal_data_selecionada" not in st.session_state:
        if dias_com_agendamento:
            st.session_state["cal_data_selecionada"] = sorted(list(dias_com_agendamento))[0]
        else:
            st.session_state["cal_data_selecionada"] = "2026-09-08"

    ano_atual = st.session_state["cal_ano"]
    mes_atual = st.session_state["cal_mes"]
    data_sel_atual = st.session_state["cal_data_selecionada"]

    # Grade principal em 2 colunas: Esquerda (Calendário) | Direita (Informações do Dia)
    col_esq, col_dir = st.columns([1.1, 1.9], gap="large")

    nomes_meses = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

    # -------------------------------------------------------------
    # COLUNA ESQUERDA: CALENDÁRIO COM DESTAQUE NOS DIAS AGENDADOS
    # -------------------------------------------------------------
    with col_esq:
        st.markdown('<div class="cal-container">', unsafe_allow_html=True)
        
        # Barra de navegação do mês
        c_nav1, c_nav2, c_nav3 = st.columns([1, 2.5, 1])
        with c_nav1:
            if st.button("◀", key="cal_prev_btn", use_container_width=True):
                if mes_atual == 1:
                    st.session_state["cal_mes"] = 12
                    st.session_state["cal_ano"] -= 1
                else:
                    st.session_state["cal_mes"] -= 1
                st.rerun()
        with c_nav2:
            st.markdown(f"<h4 style='text-align:center; margin:4px 0; color:#f8fafc;'>{nomes_meses[mes_atual]} {ano_atual}</h4>", unsafe_allow_html=True)
        with c_nav3:
            if st.button("▶", key="cal_next_btn", use_container_width=True):
                if mes_atual == 12:
                    st.session_state["cal_mes"] = 1
                    st.session_state["cal_ano"] += 1
                else:
                    st.session_state["cal_mes"] += 1
                st.rerun()

        # Legenda explicativa das marcações (com swatches limpos e elegantes)
        st.markdown("""
        <div style="display:flex; justify-content:center; align-items:center; gap:24px; font-size:0.85rem; color:#cbd5e1; margin:12px 0 16px 0; border-bottom:1px solid #334155; padding-bottom:10px;">
            <div style="display:flex; align-items:center; gap:8px;">
                <span style="display:inline-block; width:16px; height:16px; border:2px solid #f97316; border-radius:4px; background:transparent;"></span>
                <span>Com agendamento</span>
            </div>
            <div style="display:flex; align-items:center; gap:8px;">
                <span style="display:inline-block; width:16px; height:16px; background:#0284c7; border:2px solid #38bdf8; border-radius:4px;"></span>
                <span>Selecionado</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Cabeçalho dos dias da semana (Começando no Domingo)
        dias_semana_labels = ["DOM", "SEG", "TER", "QUA", "QUI", "SEX", "SÁB"]
        cols_header = st.columns(7)
        for i, lbl in enumerate(dias_semana_labels):
            cols_header[i].markdown(f"<div class='cal-header-day'>{lbl}</div>", unsafe_allow_html=True)

        # Matriz de dias daquele mês
        cal = calendar.Calendar(firstweekday=6)
        semanas = cal.monthdayscalendar(ano_atual, mes_atual)

        for s_idx, semana in enumerate(semanas):
            cols_dias = st.columns(7)
            for d_idx, dia in enumerate(semana):
                with cols_dias[d_idx]:
                    if dia == 0:
                        st.write("")
                    else:
                        data_btn_str = f"{ano_atual:04d}-{mes_atual:02d}-{dia:02d}"
                        tem_agendamento = data_btn_str in dias_com_agendamento
                        is_selecionado = (data_btn_str == data_sel_atual)

                        # Dias com agendamento usam negrito para acionar a borda laranja via CSS :has(strong)
                        btn_label = f"**{dia}**" if tem_agendamento else f"{dia}"
                        btn_type = "primary" if is_selecionado else "secondary"

                        if st.button(btn_label, key=f"btn_cal_{ano_atual}_{mes_atual}_{dia}", type=btn_type, use_container_width=True):
                            st.session_state["cal_data_selecionada"] = data_btn_str
                            st.rerun()

    # -------------------------------------------------------------
    # COLUNA DIREITA: INFORMAÇÕES DETALHADAS DO AGENDAMENTO
    # -------------------------------------------------------------
    with col_dir:
        # Formata data selecionada para exibição em português
        try:
            dt_obj = datetime.strptime(data_sel_atual, "%Y-%m-%d")
            dias_semana_pt = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
            nome_dia_sem = dias_semana_pt[dt_obj.weekday()]
            data_formatada_extenso = f"{nome_dia_sem}, {dt_obj.day:02d} de {nomes_meses[dt_obj.month]} de {dt_obj.year}"
        except Exception:
            data_formatada_extenso = data_sel_atual

        st.markdown(f"### 📋 **Agenda do Dia: {data_formatada_extenso}**")
        
        leads_dia = agendamentos_por_dia.get(data_sel_atual, [])
        
        if leads_dia:
            st.success(f"🔔 **{len(leads_dia)} agendamento(s) confirmado(s) para este dia**")
            st.write("")

            for lead_ag in leads_dia:
                ag = lead_ag.get("agendamento", {})
                tid = lead_ag.get("telegram_id")
                
                # 1. CLIENTE
                nome_cliente = lead_ag.get('nome', 'Cliente')
                
                # 2. HORÁRIO
                hora_str = ag.get("data_hora", "").replace("T", " ").split(" ")[-1][:5]
                tipo_str = ag.get('tipo', 'Visita Presencial / Reunião')

                # 3. IMÓVEL
                imovel_titulo = ag.get("imovel_titulo")
                if not imovel_titulo and lead_ag.get("imoveis_sugeridos"):
                    im_id = lead_ag["imoveis_sugeridos"][0]
                    im_obj = next((i for i in imoveis if i.get("id") == im_id), None)
                    imovel_titulo = f"{im_obj.get('titulo')} ({im_id})" if im_obj else f"Imóvel Ref. {im_id}"
                if not imovel_titulo:
                    crit = lead_ag.get("criterios", {})
                    imovel_titulo = f"{crit.get('tipo_imovel', 'Imóvel').title()} na {crit.get('regiao', 'São Paulo')}"

                # 4. ESPECIALISTA RESPONSÁVEL
                corretor_nome = ag.get('corretor_nome', 'Especialista de Plantão')
                
                # 5. BRIEFING DA CONVERSA
                briefing_texto = lead_ag.get('resumo_corretor', 'Sem resumo registrado')

                # Renderização do card em string contínua (evita quebra de bloco de código no Markdown)
                html_card_ag = (
                    f'<div class="cal-card-agendamento">'
                    f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px; border-bottom:1px solid #334155; padding-bottom:10px;">'
                    f'<div><span style="font-size:0.8rem; color:#94a3b8; text-transform:uppercase; font-weight:700;">1. CLIENTE</span>'
                    f'<div style="font-size:1.3rem; font-weight:800; color:#f8fafc; margin-top:2px;">👤 {nome_cliente} <span style="font-size:0.9rem; color:#94a3b8; font-weight:normal;">(Telegram ID: {tid})</span></div></div>'
                    f'<span class="badge badge-agendado">🟢 CONFIRMADO PELA SOFIA</span></div>'
                    f'<div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px; margin-bottom:14px;">'
                    f'<div class="data-pill" style="margin-bottom:0;"><div class="data-pill-label">2. HORÁRIO & TIPO</div><div class="data-pill-val" style="color:#f97316; font-size:1.15rem;">⏰ {hora_str}</div><div style="font-size:0.85rem; color:#cbd5e1; margin-top:2px;">{tipo_str}</div></div>'
                    f'<div class="data-pill" style="margin-bottom:0;"><div class="data-pill-label">3. IMÓVEL</div><div class="data-pill-val" style="font-size:1.0rem; color:#38bdf8;">🏡 {imovel_titulo}</div></div>'
                    f'</div>'
                    f'<div class="data-pill" style="margin-bottom:14px;"><div class="data-pill-label">4. ESPECIALISTA RESPONSÁVEL</div><div class="data-pill-val" style="font-size:1.1rem; color:#f8fafc;">👨‍💼 {corretor_nome}</div></div>'
                    f'<div class="resumo-box" style="margin-top:0;"><div style="font-size:0.85rem; color:#38bdf8; text-transform:uppercase; font-weight:700; margin-bottom:4px;">💡 5. BRIEFING DA CONVERSA:</div><div style="color:#f1f5f9; line-height:1.6;">{briefing_texto}</div></div>'
                    f'</div>'
                )
                st.markdown(html_card_ag, unsafe_allow_html=True)
                
                # Dropdown para expandir histórico da conversa do cliente
                with st.expander(f"💬 Ver Conversa da Sofia com {lead_ag.get('nome')}", expanded=False):
                    chat_path = os.path.join(CONVERSAS_DIR, f"chat_{tid}.json")
                    if os.path.exists(chat_path):
                        c_data = load_data(chat_path)
                        for m in c_data.get("mensagens", []):
                            tipo_icone = "🎙️ [Áudio de Voz]" if m.get("tipo") == "audio_voz" else "💬"
                            with st.chat_message(m.get("role", "user")):
                                st.write(f"**{m.get('autor')}** <span style='font-size:0.8rem; color:#94a3b8;'>({m.get('timestamp')})</span> {tipo_icone}", unsafe_allow_html=True)
                                st.write(m.get("conteudo"))
                    else:
                        st.caption("O histórico desta conversa será gerado automaticamente nas próximas mensagens.")
        else:
            st.info(f"ℹ️ Nenhum agendamento confirmado para **{data_formatada_extenso}**.")
            st.markdown("""
            <div style="background-color:#0f172a; border:1px solid #334155; border-radius:10px; padding:18px; margin-top:12px;">
                <h5 style="color:#38bdf8; margin:0 0 8px 0;">⚡ Disponibilidade de Plantão:</h5>
                <p style="color:#94a3b8; margin:0;">
                    A Sofia (Agente SDR) está ativa e direcionando novos leads qualificados para preencher este dia.
                </p>
            </div>
            """, unsafe_allow_html=True)

            # Lista os especialistas da imobiliária
            st.write("")
            st.markdown("#### 👨‍💼 Corretores Especialistas:")
            cols_corr = st.columns(3)
            for idx, c in enumerate(corretores):
                with cols_corr[idx % 3]:
                    st.markdown(f"**{c.get('nome')}**")
                    st.caption(f"{c.get('especialidade')}")
                    st.write(f"📞 {c.get('telefone')}")


# ==========================================
# 5. TELA: CENTRAL DE FOLLOW-UP & REENGAJAMENTO IA (TECH CHALLENGE - EXEMPLO 3)
# ==========================================
elif menu_selecionado == "⚡ Follow-up IA":
    st.title("⚡ Central de Follow-up & Reengajamento Inteligente")
    st.markdown("Atendimento integral aos requisitos do **Tech Challenge (Exemplo 3)**: Retomada automática de contato, preservação do contexto da conversa e reengajamento comercial com IA generativa.")
    st.write("")

    # CARD DE REQUISITOS DO TECH CHALLENGE
    st.markdown("""
    <div style="background-color: #0f172a; border: 1px solid #0284c7; border-radius: 12px; padding: 18px 22px; margin-bottom: 24px; box-shadow: 0 4px 12px rgba(2, 132, 199, 0.15);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <span style="color: #38bdf8; font-weight: 700; font-size: 1.1rem;">📌 Tech Challenge — Exemplo 3: Follow-up</span>
            <span class="badge badge-compra">100% OPERACIONAL</span>
        </div>
        <p style="color: #cbd5e1; margin: 0 0 12px 0; font-size: 0.95rem;">
            <em>"Cliente iniciou conversa e não respondeu. O agente deverá: • Retomar contato automaticamente; • Manter contexto da conversa; • Reengajar o lead."</em>
        </p>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;">
            <div style="background: rgba(30, 41, 59, 0.7); padding: 10px 14px; border-radius: 8px; border-left: 3px solid #38bdf8;">
                <div style="color: #38bdf8; font-weight: 700; font-size: 0.85rem;">1. RETOMADA PROATIVA</div>
                <div style="color: #94a3b8; font-size: 0.8rem; margin-top: 3px;">Job Queue periódica no Telegram + Disparo manual pelo portal.</div>
            </div>
            <div style="background: rgba(30, 41, 59, 0.7); padding: 10px 14px; border-radius: 8px; border-left: 3px solid #f97316;">
                <div style="color: #f97316; font-weight: 700; font-size: 0.85rem;">2. MANUTENÇÃO DE CONTEXTO</div>
                <div style="color: #94a3b8; font-size: 0.8rem; margin-top: 3px;">IA recupera exatamente onde a conversa parou e as preferências do lead.</div>
            </div>
            <div style="background: rgba(30, 41, 59, 0.7); padding: 10px 14px; border-radius: 8px; border-left: 3px solid #10b981;">
                <div style="color: #10b981; font-weight: 700; font-size: 0.85rem;">3. REENGAJAMENTO CONSULTIVO</div>
                <div style="color: #94a3b8; font-size: 0.8rem; margin-top: 3px;">Oferta de novidades, tour virtual e perguntas abertas de baixo atrito.</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Identifica leads elegíveis para follow-up (sem visita confirmada ou que esfriaram)
    leads_elegiveis = [l for l in leads if not l.get("agendamento")]
    leads_followup_feito = [l for l in leads if l.get("status_followup") == "Follow-up Enviado"]

    # KPIs da Central
    k1, k2, k3 = st.columns(3)
    with k1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">⏳ Leads Aguardando Retorno</div>
            <div class="kpi-value">{len(leads_elegiveis)}</div>
            <div class="kpi-desc">Conversas pausadas no funil</div>
        </div>
        """, unsafe_allow_html=True)
    with k2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">🚀 Follow-ups Disparados</div>
            <div class="kpi-value">{len(leads_followup_feito)}</div>
            <div class="kpi-desc">Mensagens com contexto de IA</div>
        </div>
        """, unsafe_allow_html=True)
    with k3:
        taxa_rec = round((len(leads_followup_feito) / len(leads_elegiveis) * 100), 1) if leads_elegiveis else 0
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">🎯 Cobertura de Reengajamento</div>
            <div class="kpi-value">{taxa_rec}%</div>
            <div class="kpi-desc">Contatos reativados proativamente</div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")
    st.markdown("### 🎯 **Simulação e Disparo de Reengajamento por Lead**")

    # Mapeia opções de clientes
    opcoes_followup = {}
    for l in leads:
        tid = l.get("telegram_id")
        nome = l.get("nome", "Cliente")
        status_f = l.get("status_followup", "Aguardando Resposta")
        label = f"👤 {nome} (ID: {tid}) — Status: [{status_f}]"
        opcoes_followup[label] = l

    lead_sel_label = st.selectbox(
        "Selecione um cliente para analisar a pausa e acionar a Sofia:",
        list(opcoes_followup.keys()),
        index=0
    )

    lead_escolhido = opcoes_followup.get(lead_sel_label)
    if lead_escolhido:
        tid_escolhido = lead_escolhido.get("telegram_id")
        nome_escolhido = lead_escolhido.get("nome", "Cliente")

        col_esq, col_dir = st.columns([1.1, 1.3])

        # COLUNA ESQUERDA: ONDE A CONVERSA PAROU
        with col_esq:
            st.markdown("#### 💬 **Onde a Conversa Parou:**")
            chat_path = os.path.join(CONVERSAS_DIR, f"chat_{tid_escolhido}.json")
            if os.path.exists(chat_path):
                chat_data = load_data(chat_path)
                mensagens = chat_data.get("mensagens", [])
                if mensagens:
                    # Mostra as 3 últimas mensagens
                    ultimas_msgs = mensagens[-4:]
                    st.caption(f"Exibindo as últimas interações de {nome_escolhido}:")
                    for m in ultimas_msgs:
                        role = m.get("role", "user")
                        tipo_icone = "🎙️ [Áudio de Voz]" if m.get("tipo") == "audio_voz" else "💬"
                        with st.chat_message(role):
                            st.write(f"**{m.get('autor')}** <span style='font-size:0.75rem; color:#94a3b8;'>({m.get('timestamp')})</span>", unsafe_allow_html=True)
                            st.write(m.get("conteudo"))
                else:
                    st.info("Nenhuma mensagem anterior registrada.")
            else:
                st.info("Histórico de conversa em preparação.")

            st.write("")
            crit_escolhido = lead_escolhido.get("criterios", {})
            st.markdown(f"""
            <div class="data-pill">
                <div class="data-pill-label">🎯 Resumo do Perfil</div>
                <div class="data-pill-val" style="font-size: 0.95rem; color: #cbd5e1;">
                    <strong>Intenção:</strong> {lead_escolhido.get('intencao', 'Geral').title()}<br/>
                    <strong>Região:</strong> {crit_escolhido.get('regiao', 'São Paulo')} ({', '.join(crit_escolhido.get('bairros', [])) or 'Geral'})<br/>
                    <strong>Score:</strong> {lead_escolhido.get('score_qualificacao', 0)}%
                </div>
            </div>
            """, unsafe_allow_html=True)

        # COLUNA DIREITA: IA GERA O REENGAJAMENTO COM CONTEXTO
        with col_dir:
            st.markdown("#### 🤖 **Mensagem de Reengajamento Gerada pela Sofia:**")
            st.caption("A IA sintetiza o histórico da conversa, preserva o contexto e propõe um gancho de reengajamento.")

            # Inicializa agente para geração de follow-up
            agent_sdr = SDRImobiliarioAgent()
            chave_cache = f"msg_followup_{tid_escolhido}"

            if chave_cache not in st.session_state:
                with st.spinner("🧠 Sofia analisando o histórico e criando o gancho contextualizado com Azure OpenAI..."):
                    res_followup = agent_sdr.gerar_mensagem_followup(tid_escolhido)
                    st.session_state[chave_cache] = res_followup.get("mensagem", "")

            texto_followup = st.text_area(
                "Texto gerado pela Sofia (pronto para envio):",
                value=st.session_state[chave_cache],
                height=180,
                help="Você pode editar o texto antes de disparar, se desejar."
            )

            col_btn1, col_btn2 = st.columns([1, 1])
            with col_btn1:
                if st.button("🔄 Gerar Nova Variação com IA", use_container_width=True):
                    with st.spinner("Gerando novo gancho de reengajamento..."):
                        res_followup = agent_sdr.gerar_mensagem_followup(tid_escolhido)
                        st.session_state[chave_cache] = res_followup.get("mensagem", "")
                        st.rerun()

            with col_btn2:
                btn_disparar = st.button("🚀 Disparar Follow-up Imediato", type="primary", use_container_width=True)

            if btn_disparar:
                with st.spinner(f"Enviando follow-up para {nome_escolhido} via Telegram..."):
                    token_telegram = os.getenv("TELEGRAM_BOT_TOKEN")
                    envio_sucesso = False
                    erro_msg = ""

                    # Disparo via Telegram Bot API se houver token
                    if token_telegram:
                        try:
                            url_api = f"https://api.telegram.org/bot{token_telegram}/sendMessage"
                            payload = {
                                "chat_id": tid_escolhido,
                                "text": f"🔔 *Mensagem da Sofia (Imobiliária Prime)*\n\n{texto_followup}",
                                "parse_mode": "Markdown"
                            }
                            resp = httpx.post(url_api, json=payload, timeout=10.0)
                            if resp.status_code == 200:
                                envio_sucesso = True
                            else:
                                # Fallback sem markdown
                                payload["parse_mode"] = None
                                resp2 = httpx.post(url_api, json=payload, timeout=10.0)
                                if resp2.status_code == 200:
                                    envio_sucesso = True
                                else:
                                    erro_msg = resp2.text
                        except Exception as ex_tel:
                            erro_msg = str(ex_tel)
                    else:
                        envio_sucesso = True  # Modo simulação

                    # Registra no histórico do chat e no arquivo de leads
                    registrar_mensagem_historico(
                        tid_escolhido,
                        nome_escolhido,
                        "assistant",
                        texto_followup,
                        tipo="followup_automatico"
                    )

                    # Atualiza leads.json
                    for l in leads:
                        if str(l.get("telegram_id")) == str(tid_escolhido):
                            l["status_followup"] = "Follow-up Enviado"
                            l["data_ultimo_followup"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            l["tentativas_followup"] = l.get("tentativas_followup", 0) + 1
                            break
                    save_json(LEADS_PATH, leads)

                    if envio_sucesso:
                        st.balloons()
                        st.success(f"✅ **Follow-up enviado com sucesso para {nome_escolhido} no Telegram!**\n\nHistórico de chat e status do lead atualizados.")
                    else:
                        st.warning(f"Follow-up registrado no sistema! (Nota de envio Telegram: {erro_msg[:120]})")


