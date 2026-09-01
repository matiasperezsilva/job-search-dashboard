import streamlit as st
from jobsearch.services.repository import listar_ofertas
from jobsearch.ui.theme import hero

hero('Seguimiento de postulaciones', 'Visualiza rápidamente en qué etapa está cada proceso y mantén tus notas centralizadas.', 'PIPELINE PERSONAL')
estado = st.segmented_control('Estado', ['Postulada', 'Entrevista', 'Oferta recibida', 'Rechazada', 'Guardada'], default='Postulada')
rows = listar_ofertas(0, estado=estado)
st.caption(f'{len(rows)} registros en **{estado}**')
if not rows:
    st.info('No hay registros en este estado.')
for row in rows:
    score = row.get('puntaje',0)
    badge = 'badge-green' if score >= 70 else 'badge-blue' if score >= 50 else 'badge-gray'
    st.markdown(f'''<div class="panel-card"><div style="display:flex;justify-content:space-between;gap:16px;align-items:flex-start">
    <div><div class="section-title">{row['titulo']}</div><div class="section-subtitle">{row['empresa']} · {row.get('fuente','')}</div></div>
    <span class="badge {badge}">{score} pts</span></div>
    <div style="color:#68758a;font-size:.9rem">{row.get('notas') or row.get('razon') or 'Sin notas registradas.'}</div></div>''', unsafe_allow_html=True)
    if row.get('link'):
        st.link_button('Abrir publicación', row['link'])
