import os
import json
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
from supabase import create_client, Client

st.set_page_config(page_title="SalesPulse Analytics", page_icon="📈", layout="wide")

load_dotenv()

supabase: Client = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

produtos = requests.get("https://dummyjson.com/products?limit=0")
vendas = requests.get("https://dummyjson.com/carts")

produtos_filtro = [
    {"id_produto": item.get("id"), "titulo": item.get("title"), "categoria": item.get("category")}
    for item in produtos.json().get("products", [])
]

dados_vendas = vendas.json().get("carts", [])
vendas_filtro = [
    {"id_carrinho": carrinho.get("id"), "id_produto": venda.get("id"), "quantidade": venda.get("quantity"), "preco_total_item": venda.get("discountedTotal")}
    for carrinho in dados_vendas
    for venda in carrinho.get("products", [])
]

@st.cache_data(ttl=3600, show_spinner="Buscando métricas no banco de dados...")
def carregar_dados(intervalo):
    try:
        response = supabase.rpc("carregar_dados_dashboard", {"intervalo_grafico": intervalo}).execute()
        return response.data
    except Exception as e:
        st.error(f"Erro ao conectar com o banco de dados: {e}")
        return {}

opcoes_periodo = {
    "Last 7 Days": "7 days",
    "Last 15 Days": "15 days",
    "Last Month": "1 month",
    "Último Quarter": "3 months",
    "Last 6 Months": "6 months",
    "Last Year": "1 year"
}

st.title("SalesPulse Analytics")
st.subheader("Revenue monitoring platform with insights by time, category, and performance.")

container_kpis = st.container()

filtro_selecionado = st.selectbox(
    "Time frame:",
    options=list(opcoes_periodo.keys()),
    index=0, width=200
)

parametro_banco = opcoes_periodo[filtro_selecionado]
dados_dashboard = carregar_dados(parametro_banco)

kpis = dados_dashboard.get("kpis", {})
dados_grafico = dados_dashboard.get("grafico_faturamento", [])

config_kpis = [
    {"titulo": "Total Revenue", "valor": f"R$ {kpis.get('faturamento_total', 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")},
    {"titulo": "Sales Volume", "valor": str(kpis.get('vendas_semana', 0))},
    {"titulo": "Revenue (7 days)", "valor": f"R$ {kpis.get('faturamento_semana', 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")},
    {"titulo": "Best Category", "valor": kpis.get('melhor_categoria_semana', 'N/A').title()}
]

with container_kpis:
    colunas = st.columns(len(config_kpis), border=True)
    for i, config in enumerate(config_kpis):
         colunas[i].metric(label=config["titulo"], value=config["valor"])


def aplicar_estilo_corporativo(figura):
    figura.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=40, b=20),
        showlegend=False
    )
    figura.update_xaxes(showgrid=False, zeroline=False)
    figura.update_yaxes(showgrid=False, zeroline=False)
    return figura

with st.container():
    col_esq, col_dir = st.columns([6, 4], gap="large") 

    with col_esq:
        st.markdown("### Revenue Growth")        
        if dados_grafico:
            df_grafico = pd.DataFrame(dados_grafico)
            fig_linha = px.line(
                df_grafico, x="data", y="valor", markers=True,
                labels={"data": "Data", "valor": "Receita (R$)"}
            )
            fig_linha.update_traces(line_color="#8b5cf6", line_width=4, marker=dict(size=8, color="#1e40af"))
            fig_linha = aplicar_estilo_corporativo(fig_linha)
            st.plotly_chart(fig_linha, use_container_width=True)
        else:
            st.info("Nenhum dado de faturamento encontrado no período.")

        st.markdown("---")

        st.markdown("### Revenue by Category")
        df_receita_cat = pd.DataFrame(dados_dashboard.get("receita_por_categoria", []))
        if not df_receita_cat.empty:
            fig_area = px.area(
                df_receita_cat, x="categoria", y="receita",
                labels={"categoria": "Categoria", "receita": "Receita (R$)"}
            )
            fig_area.update_traces(line_color="#a78bfa", fillcolor="rgba(167, 139, 250, 0.5)")
            fig_area = aplicar_estilo_corporativo(fig_area)
            st.plotly_chart(fig_area, use_container_width=True)

    with col_dir:
        with st.container():
            col_esq, col_dir = st.columns(2)
            with col_esq:
                st.markdown("### Volume by Category")
                df_vendas_cat = pd.DataFrame(dados_dashboard.get("vendas_por_categoria", []))
                if not df_vendas_cat.empty:
                    fig_barras_cat = px.bar(
                        df_vendas_cat, x="total_itens_vendidos", y="categoria", orientation='h',
                        labels={"total_itens_vendidos": "Itens Vendidos", "categoria": "Categoria"}
                    )
                    fig_barras_cat.update_traces(marker_color="#8b5cf6")
                    fig_barras_cat = aplicar_estilo_corporativo(fig_barras_cat)
                    fig_barras_cat.update_layout(yaxis={'categoryorder':'total ascending'}) 
                    st.plotly_chart(fig_barras_cat, use_container_width=True)

            with col_dir:
                st.markdown("### Top 3 Products")
                df_top_3 = pd.DataFrame(dados_dashboard.get("top_3_produtos", []))
                if not df_top_3.empty:
                    fig_barras_prod = px.bar(
                        df_top_3, x="produto", y="receita_gerada",
                        labels={"produto": "Produto", "receita_gerada": "Receita (R$)"}
                    )
                    fig_barras_prod.update_traces(marker_color="#8b5cf6")
                    fig_barras_prod = aplicar_estilo_corporativo(fig_barras_prod)
                    st.plotly_chart(fig_barras_prod, use_container_width=True)


                st.markdown("### Category Share")
                df_performance = pd.DataFrame(dados_dashboard.get("tabela_performance", []))
                
                if not df_performance.empty:
                    fig_pizza = px.pie(
                        df_performance, 
                        values="receita_total", 
                        names="categoria",
                        hole=0.4 
                    )
                    fig_pizza.update_traces(textposition='inside', textinfo='percent+label', showlegend=False) 
                    fig_pizza = aplicar_estilo_corporativo(fig_pizza)
                    fig_pizza.update_layout(margin=dict(l=0, r=0, t=10, b=0)) 
                    st.plotly_chart(fig_pizza, use_container_width=True)