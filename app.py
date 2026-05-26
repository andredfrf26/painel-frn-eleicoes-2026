from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(
    page_title="Painel Processual Eleições 2026",
    layout="wide",
    initial_sidebar_state="collapsed",
)

BASE_DIR = Path(__file__).parent
CSV_PATH = BASE_DIR / "data" / "acompanhamento_processual_2026_05_22_2.csv"
CSS_PATH = BASE_DIR / "assets" / "style.css"
LOGO_PATTERN = "logo-frn-ferraro-novaes*"
GOOGLE_SHEET_URL = ""

PALETTE = ["#b99063", "#147f92", "#2eb39b", "#d6a642", "#0f5c70", "#8fb8c9"]
CHART_BG = "#122334"
PAGE_TEXT = "#d8e6f3"
PLOTLY_CONFIG = {"displayModeBar": False, "responsive": True}


if CSS_PATH.exists():
    st.markdown(
        f"<style>{CSS_PATH.read_text(encoding='utf-8')}</style>",
        unsafe_allow_html=True,
    )


def fix_text(value):
    if pd.isna(value):
        return value

    text = str(value)
    if "Ã" in text or "Â" in text:
        try:
            return text.encode("latin1").decode("utf-8")
        except UnicodeError:
            return text
    return text


def get_secret(name, default=""):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


def google_sheet_to_csv_url(sheet_url):
    if not sheet_url:
        return ""

    parsed = urlparse(sheet_url)
    parts = [part for part in parsed.path.split("/") if part]

    try:
        sheet_id = parts[parts.index("d") + 1]
    except (ValueError, IndexError):
        return sheet_url

    gid = parse_qs(parsed.query).get("gid", ["0"])[0]
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"


def normalize_dataframe(df_loaded):
    df_loaded.columns = [fix_text(col).strip() for col in df_loaded.columns]

    object_cols = df_loaded.select_dtypes(include=["object", "string"]).columns
    for col in object_cols:
        df_loaded[col] = df_loaded[col].map(fix_text)

    return df_loaded


@st.cache_data(show_spinner=False, ttl=300)
def load_data(sheet_url, local_path):
    csv_url = google_sheet_to_csv_url(sheet_url)

    if csv_url:
        try:
            data = pd.read_csv(csv_url, encoding="utf-8-sig")
            return normalize_dataframe(data), "Planilha Google"
        except Exception as exc:
            if not local_path.exists():
                raise RuntimeError(f"Nao foi possivel carregar a planilha Google: {exc}") from exc

            data = pd.read_csv(local_path, encoding="utf-8-sig")
            return normalize_dataframe(data), "CSV local; planilha Google sem acesso publico"

    if not local_path.exists():
        return None, "Arquivo CSV local nao encontrado"

    data = pd.read_csv(local_path, encoding="utf-8-sig")
    return normalize_dataframe(data), "CSV local"


sheet_url_config = get_secret("GOOGLE_SHEET_URL", GOOGLE_SHEET_URL)

if "refresh_message" not in st.session_state:
    st.session_state["refresh_message"] = ""

df, data_source = load_data(sheet_url_config, CSV_PATH)

if df is None:
    st.error(f"Arquivo CSV não encontrado: {CSV_PATH}")
    st.stop()


COL_TIPO = "TIPO DE AÇÃO (CLASSE)"
COL_TEMA = "TEMA"
COL_RELATORIA = "RELATORIA"
COL_PARTE = "PARTE(S) CONTRÁRIA(S)"
COL_PROCESSO = "NÚMERO DO PROCESSO"
COL_OBJETO = "OBJETO"
COL_POLO = "POLO PROCESSUAL"
COL_TRIBUNAL = "TRIBUNAL"
COL_SITUACAO = "SITUAÇÃO"
COL_SITUACAO_PROCESSUAL = "Situação processual"

required_cols = [
    COL_TIPO,
    COL_TEMA,
    COL_RELATORIA,
    COL_PARTE,
    COL_PROCESSO,
    COL_OBJETO,
    COL_POLO,
    COL_TRIBUNAL,
]

missing_cols = [col for col in required_cols if col not in df.columns]
if missing_cols:
    st.error("Colunas obrigatórias não encontradas no CSV: " + ", ".join(missing_cols))
    st.stop()

SITUACAO_FIELD = COL_SITUACAO_PROCESSUAL if COL_SITUACAO_PROCESSUAL in df.columns else COL_SITUACAO


def unique_options(frame, column, all_label):
    values = (
        frame[column]
        .dropna()
        .astype(str)
        .map(str.strip)
    )
    values = sorted([item for item in values.unique().tolist() if item and item.lower() != "nan"])
    return [all_label] + values


def contains(series, text):
    return series.astype(str).str.contains(text, case=False, na=False, regex=False)


def reduce_text(value, limit=38):
    text = "Não informado" if pd.isna(value) or str(value).strip() == "" else str(value).strip()
    return text if len(text) <= limit else text[:limit].rstrip() + "..."


def reset_filters():
    defaults = {
        "busca": "",
        "numero": "",
        "objeto": "",
        "tipo": "Todos",
        "tema": "Todos",
        "relatoria": "Todas",
        "situacao": "Todas",
        "parte": "Todas",
    }
    for key, value in defaults.items():
        st.session_state[key] = value


def ensure_session_choice(key, options, default):
    if st.session_state.get(key, default) not in options:
        st.session_state[key] = default


def select_polo(polo):
    st.session_state["selected_polo"] = polo
    st.query_params["polo"] = polo


def kpi_card(title, value, description):
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-title">{title}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-desc">{description}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def chart_layout(fig, title, height=340, showlegend=False):
    fig.update_layout(
        template="plotly_dark",
        title=title,
        height=height,
        paper_bgcolor=CHART_BG,
        plot_bgcolor=CHART_BG,
        font=dict(color=PAGE_TEXT, size=12),
        title_font=dict(color="#ffffff", size=17),
        margin=dict(l=16, r=24, t=52, b=30),
        xaxis=dict(
            title="",
            gridcolor="rgba(255,255,255,0.07)",
            zeroline=False,
            tickfont=dict(color=PAGE_TEXT, size=12),
        ),
        yaxis=dict(
            title="",
            gridcolor="rgba(255,255,255,0.03)",
            automargin=True,
            tickfont=dict(color=PAGE_TEXT, size=12),
        ),
        bargap=0.28,
        showlegend=showlegend,
    )
    fig.update_traces(marker_line_width=0)
    return fig


def horizontal_bar(frame, column, label, title, color, limit=10, height=340):
    chart_data = (
        frame[column]
        .fillna("Não informado")
        .astype(str)
        .map(lambda value: value.strip() or "Não informado")
        .value_counts()
        .head(limit)
        .reset_index()
    )
    chart_data.columns = [f"{label} Original", "Quantidade"]
    chart_data[label] = chart_data[f"{label} Original"].map(reduce_text)

    fig = px.bar(
        chart_data,
        x="Quantidade",
        y=label,
        orientation="h",
        custom_data=[f"{label} Original"],
        text="Quantidade",
        color_discrete_sequence=[color],
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    fig.update_traces(
        textposition="outside",
        cliponaxis=False,
        textfont=dict(color="#ffffff", size=13),
        hovertemplate="%{customdata[0]}<br>Quantidade: %{x}<extra></extra>",
    )
    return chart_layout(fig, title, height=height)


query_polo = str(st.query_params.get("polo", st.session_state.get("selected_polo", "ATIVO"))).upper()
selected_polo = query_polo if query_polo in ["ATIVO", "PASSIVO"] else "ATIVO"
st.session_state["selected_polo"] = selected_polo

df_tse = df[contains(df[COL_TRIBUNAL], "TSE")].copy()
df_base = df_tse[contains(df_tse[COL_POLO], selected_polo)].copy()

fora_filtro = len(df) - len(df_base)
ativo_total = contains(df_tse[COL_POLO], "ATIVO").sum()
passivo_total = contains(df_tse[COL_POLO], "PASSIVO").sum()
polo_label = "Ativo" if selected_polo == "ATIVO" else "Passivo"

header_left, header_right = st.columns([4.6, 1.2])

with header_left:
    st.markdown("<h1>Painel Processual Eleições 2026</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p class='subtitle'>Federação Brasil da Esperança - Monitoramento processual no TSE</p>",
        unsafe_allow_html=True,
    )

with header_right:
    logo_files = sorted((BASE_DIR / "assets").glob(LOGO_PATTERN))
    if logo_files:
        st.image(str(logo_files[0]), width="stretch")

polo_ativo, polo_passivo, atualizar_col, _ = st.columns([0.9, 0.9, 0.9, 4.3])
with polo_ativo:
    st.button(
        f"Polo Ativo    {ativo_total}",
        width="stretch",
        key="polo_ativo_btn",
        on_click=select_polo,
        args=("ATIVO",),
        type="primary" if selected_polo == "ATIVO" else "secondary",
    )
with polo_passivo:
    st.button(
        f"Polo Passivo    {passivo_total}",
        width="stretch",
        key="polo_passivo_btn",
        on_click=select_polo,
        args=("PASSIVO",),
        type="primary" if selected_polo == "PASSIVO" else "secondary",
    )
with atualizar_col:
    if st.button("Atualizar", width="stretch", key="btn_atualizar_dados"):
        st.cache_data.clear()
        st.session_state["refresh_message"] = "Dados atualizados."
        st.rerun()
if st.session_state["refresh_message"]:
    st.toast(st.session_state["refresh_message"])
    st.session_state["refresh_message"] = ""

tipo_options = unique_options(df_base, COL_TIPO, "Todos")
tema_options = unique_options(df_base, COL_TEMA, "Todos")
relatoria_options = unique_options(df_base, COL_RELATORIA, "Todas")
situacao_options = unique_options(df_base, SITUACAO_FIELD, "Todas")
parte_options = unique_options(df_base, COL_PARTE, "Todas")

ensure_session_choice("tipo", tipo_options, "Todos")
ensure_session_choice("tema", tema_options, "Todos")
ensure_session_choice("relatoria", relatoria_options, "Todas")
ensure_session_choice("situacao", situacao_options, "Todas")
ensure_session_choice("parte", parte_options, "Todas")

busca = st.session_state.get("busca", "")
numero = st.session_state.get("numero", "")
tipo = st.session_state.get("tipo", "Todos")
tema = st.session_state.get("tema", "Todos")
relatoria = st.session_state.get("relatoria", "Todas")
objeto = st.session_state.get("objeto", "")
situacao = st.session_state.get("situacao", "Todas")
parte = st.session_state.get("parte", "Todas")

df_filtrado = df_base.copy()

if busca:
    search = busca.strip().lower()
    df_filtrado = df_filtrado[
        df_filtrado.astype(str).apply(
            lambda row: row.str.lower().str.contains(search, na=False, regex=False).any(),
            axis=1,
        )
    ]

if numero:
    df_filtrado = df_filtrado[contains(df_filtrado[COL_PROCESSO], numero.strip())]

if tipo != "Todos":
    df_filtrado = df_filtrado[df_filtrado[COL_TIPO].astype(str) == tipo]

if tema != "Todos":
    df_filtrado = df_filtrado[df_filtrado[COL_TEMA].astype(str) == tema]

if relatoria != "Todas":
    df_filtrado = df_filtrado[df_filtrado[COL_RELATORIA].astype(str) == relatoria]

if objeto:
    df_filtrado = df_filtrado[contains(df_filtrado[COL_OBJETO], objeto.strip())]

if situacao != "Todas":
    df_filtrado = df_filtrado[df_filtrado[SITUACAO_FIELD].astype(str) == situacao]

if parte != "Todas":
    df_filtrado = df_filtrado[df_filtrado[COL_PARTE].astype(str) == parte]

percent_base = 0 if len(df_base) == 0 else (len(df_filtrado) / len(df_base)) * 100

k1, k2, k3, k4, k5, k6 = st.columns(6)
with k1:
    kpi_card(
        f"Registros TSE / {polo_label} exibidos",
        len(df_filtrado),
        f"{percent_base:.1f}% da base TSE / {polo_label}",
    )
with k2:
    kpi_card("Tipos da ação", df_filtrado[COL_TIPO].nunique(), "classes distintas")
with k3:
    kpi_card("Temas", df_filtrado[COL_TEMA].nunique(), "temas distintos")
with k4:
    kpi_card("Situação processual", df_filtrado[SITUACAO_FIELD].nunique(), "situações distintas")
with k5:
    kpi_card("Partes contrárias", df_filtrado[COL_PARTE].nunique(), "menções distintas")
with k6:
    kpi_card("Filtro fixo", len(df_base), f"{fora_filtro} registro(s) fora de TSE / {polo_label}")

st.markdown("<div class='section-gap'></div>", unsafe_allow_html=True)

with st.container(border=True):
    f1, f2, f3, f4, f5 = st.columns([2.2, 1.1, 1.1, 1.1, 1.1])

    f1.text_input(
        "Busca livre",
        placeholder="Processo, tema, objeto, situação, relatoria ou parte contrária",
        key="busca",
    )
    f2.text_input("Número do processo", placeholder="0600...", key="numero")
    f3.selectbox("Tipo da Ação", tipo_options, key="tipo")
    f4.selectbox("Tema", tema_options, key="tema")
    f5.selectbox("Relatoria", relatoria_options, key="relatoria")

    f6, f7, f8, f9, f10 = st.columns([2.2, 1.1, 1.1, 1.1, 1.1])

    f6.text_input("Objeto contém", placeholder="Instagram, impulsionamento, IA...", key="objeto")
    f7.selectbox("Situação processual", situacao_options, key="situacao")
    f8.selectbox("Parte Contrária", parte_options, key="parte")

    with f9:
        st.button(
            "Limpar filtros",
            width="stretch",
            on_click=reset_filters,
            key="btn_limpar_campos",
        )

    with f10:
        st.download_button(
            "Exportar CSV",
            df_filtrado.to_csv(index=False).encode("utf-8-sig"),
            "processos_filtrados.csv",
            "text/csv",
            width="stretch",
            key="btn_exportar_csv",
        )

st.markdown("<div class='section-gap'></div>", unsafe_allow_html=True)

g1, g2 = st.columns(2)

with g1:
    tipo_data = (
        df_filtrado[COL_TIPO]
        .fillna("Não informado")
        .astype(str)
        .map(lambda value: value.strip() or "Não informado")
        .value_counts()
        .reset_index()
    )
    tipo_data.columns = ["Tipo", "Quantidade"]

    fig1 = px.pie(
        tipo_data,
        names="Tipo",
        values="Quantidade",
        hole=0.62,
        color_discrete_sequence=PALETTE,
    )
    fig1.update_layout(
        template="plotly_dark",
        title="Distribuição por Tipo de Ação",
        height=340,
        paper_bgcolor=CHART_BG,
        plot_bgcolor=CHART_BG,
        font=dict(color=PAGE_TEXT, size=12),
        title_font=dict(color="#ffffff", size=17),
        legend=dict(
            orientation="h",
            y=-0.16,
            x=0,
            font=dict(size=12, color=PAGE_TEXT),
        ),
        margin=dict(l=12, r=12, t=52, b=48),
    )
    fig1.update_traces(
        textfont=dict(color="#ffffff", size=13),
        marker=dict(line=dict(color=CHART_BG, width=1)),
    )
    st.plotly_chart(fig1, width="stretch", config=PLOTLY_CONFIG)

with g2:
    st.plotly_chart(
        horizontal_bar(df_filtrado, COL_TEMA, "Tema", "Top 10 Temas", "#147f92"),
        width="stretch",
        config=PLOTLY_CONFIG,
    )

g3, g4 = st.columns(2)

with g3:
    st.plotly_chart(
        horizontal_bar(df_filtrado, COL_RELATORIA, "Relatoria", "Distribuição por Relatoria", "#b99063"),
        width="stretch",
        config=PLOTLY_CONFIG,
    )

with g4:
    st.plotly_chart(
        horizontal_bar(df_filtrado, COL_PARTE, "Parte Contrária", "Top 10 Partes Contrárias", "#2eb39b"),
        width="stretch",
        config=PLOTLY_CONFIG,
    )

st.plotly_chart(
    horizontal_bar(
        df_filtrado,
        SITUACAO_FIELD,
        "Situação",
        "Distribuição por Situação Processual",
        "#d6a642",
        height=340,
    ),
    width="stretch",
    config=PLOTLY_CONFIG,
)

st.subheader("Detalhamento dos Processos")

table_columns = [
    COL_PROCESSO,
    COL_TIPO,
    COL_TEMA,
    COL_OBJETO,
    COL_RELATORIA,
    COL_PARTE,
    COL_POLO,
    COL_TRIBUNAL,
]

if SITUACAO_FIELD in df_filtrado.columns:
    table_columns.append(SITUACAO_FIELD)

st.dataframe(
    df_filtrado[table_columns],
    width="stretch",
    height=500,
    hide_index=True,
)
