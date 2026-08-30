import streamlit as st
from jobsearch.services.repository import resumen

st.title("📊 Resumen")
r = resumen()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Ofertas guardadas", r["total"])
c2.metric("Calce ≥ 70", r["top"])
c3.metric("Postuladas", r["postuladas"])
c4.metric("Entrevistas", r["entrevistas"])

st.subheader("Ofertas por fuente")
if r["fuentes"]:
    st.bar_chart({x["fuente"]: x["cantidad"] for x in r["fuentes"]})
else:
    st.info("Todavía no hay ofertas. Puedes cargar el dataset de ejemplo o ejecutar una búsqueda.")
