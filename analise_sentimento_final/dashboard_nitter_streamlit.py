import streamlit as st
import pandas as pd
from pathlib import Path

LOG_SAIDA = Path("coletas_diarias.csv")

st.set_page_config(page_title="Coleta Nitter – Tarifaço", page_icon="📊", layout="centered")

st.title("📊 Coleta de Tweets – Tarifaço")
st.caption("Atualização automática diária às 6h")

if LOG_SAIDA.exists():
    log = pd.read_csv(LOG_SAIDA)
    st.metric("Coletas de Hoje", int(log.tail(1)['coletas'].values[0]))
    st.line_chart(log.set_index("data")["coletas"])
else:
    st.warning("Ainda não há registros de coleta.")
