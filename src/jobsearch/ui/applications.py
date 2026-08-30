import streamlit as st
from jobsearch.services.repository import listar_ofertas

st.title("✅ Postulaciones")
estado = st.selectbox("Estado", ["Postulada", "Entrevista", "Oferta recibida", "Rechazada", "Guardada"])
rows = listar_ofertas(0, estado=estado)

if not rows:
    st.info("No hay registros en este estado.")

for row in rows:
    with st.expander(f"{row['titulo']} — {row['empresa']} · {row['puntaje']} pts"):
        st.write(row["razon"])
        if row["notas"]:
            st.write(row["notas"])
        if row["link"]:
            st.link_button("Abrir publicación", row["link"])
