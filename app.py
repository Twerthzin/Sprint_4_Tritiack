"""
Dashboard Streamlit do projeto de monitoramento inteligente GoodWe.

Execute com:
    streamlit run app.py
"""

from __future__ import annotations

import streamlit as st
import plotly.express as px

from src.analyzer import calcular_metricas, enriquecer_dataframe
from src.goodwe_reader import carregar_dados
from src.recommender import gerar_recomendacoes, resumo_recomendacoes


st.set_page_config(
    page_title="Monitoramento Inteligente GoodWe",
    page_icon="☀️",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Carregamento de dados (cache para não recarregar a cada interação)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60)
def carregar_tudo():
    df, origem = carregar_dados()
    df = enriquecer_dataframe(df)
    metricas = calcular_metricas(df)
    recomendacoes = gerar_recomendacoes(df)
    resumo = resumo_recomendacoes(recomendacoes)
    return df, origem, metricas, recomendacoes, resumo


df, origem, metricas, recomendacoes, resumo = carregar_tudo()


# ---------------------------------------------------------------------------
# Cabeçalho
# ---------------------------------------------------------------------------

st.title("☀️ Monitoramento Inteligente GoodWe")
st.caption(
    f"Origem dos dados: **{origem}** · "
    f"{len(df)} leituras · "
    f"Projeto acadêmico FIAP — PRINT 4"
)


# ---------------------------------------------------------------------------
# Métricas principais
# ---------------------------------------------------------------------------

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Energia gerada",
    f"{metricas.energia_gerada_kwh:.2f} kWh",
    help="Total gerado no período analisado.",
)
col2.metric(
    "CO₂ evitado",
    f"{metricas.co2_evitado_kg:.2f} kg",
    help="Baseado no fator médio do SIN (0,0385 kg CO₂/kWh).",
)
col3.metric(
    "Autoconsumo",
    f"{metricas.eficiencia_autoconsumo_pct:.1f}%",
    help="Percentual da geração aproveitado localmente.",
)
col4.metric(
    "Economia estimada",
    f"R$ {metricas.economia_estimada_rs:.2f}",
    help="Autoconsumo + injeção na rede × tarifa média.",
)


# ---------------------------------------------------------------------------
# Gráfico 1: geração × consumo
# ---------------------------------------------------------------------------

st.subheader("Geração × Consumo ao longo do dia")

fig_linha = px.line(
    df,
    x="timestamp",
    y=["potencia_gerada_kw", "potencia_consumo_kw"],
    labels={
        "timestamp": "Horário",
        "value": "Potência (kW)",
        "variable": "Série",
    },
    color_discrete_sequence=["#F2A900", "#1F77B4"],
)
fig_linha.update_layout(
    legend_title_text="",
    hovermode="x unified",
    height=380,
)
st.plotly_chart(fig_linha, use_container_width=True)


# ---------------------------------------------------------------------------
# Gráfico 2: composição do balanço energético
# ---------------------------------------------------------------------------

st.subheader("Balanço energético instantâneo")

fig_area = px.area(
    df,
    x="timestamp",
    y=["autoconsumo_kw", "excedente_kw", "deficit_kw"],
    labels={
        "timestamp": "Horário",
        "value": "Potência (kW)",
        "variable": "Componente",
    },
    color_discrete_sequence=["#2CA02C", "#F2A900", "#D62728"],
)
fig_area.update_layout(
    legend_title_text="",
    hovermode="x unified",
    height=380,
)
st.plotly_chart(fig_area, use_container_width=True)


# ---------------------------------------------------------------------------
# Recomendações
# ---------------------------------------------------------------------------

st.subheader("Recomendações do motor de decisão")

if recomendacoes:
    st.caption(
        f"{resumo['total']} recomendações geradas · "
        f"Prioridades: {resumo['por_prioridade']} · "
        f"Categorias: {resumo['por_categoria']}"
    )

    tabela = [
        {
            "Horário": r.timestamp.strftime("%H:%M"),
            "Prioridade": r.prioridade.upper(),
            "Categoria": r.categoria,
            "Ação": r.acao,
            "Justificativa": r.justificativa,
        }
        for r in recomendacoes
    ]
    st.dataframe(tabela, use_container_width=True, hide_index=True)
else:
    st.info("Nenhuma recomendação gerada para o período analisado.")


# ---------------------------------------------------------------------------
# Rodapé
# ---------------------------------------------------------------------------

st.divider()
st.caption(
    "Stack: Python · Streamlit · pandas · Plotly · biblioteca `goodwe` (integração local) · "
    "alinhado ao ecossistema GoodWe (SEMS+)"
)