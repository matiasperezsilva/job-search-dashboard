import streamlit as st
from jobsearch.services.repository import resumen
from jobsearch.ui.theme import hero, metricas

hero('Tu búsqueda laboral, en un solo lugar', 'Prioriza oportunidades según tu CV, genera cartas personalizadas y mantén el seguimiento de cada postulación.', 'RESUMEN GENERAL')
r = resumen()
metricas([
    ('Ofertas guardadas', r['total'], 'Oportunidades en tu base'),
    ('Calce alto', r['top'], 'Puntaje igual o superior a 70'),
    ('Postuladas', r['postuladas'], 'Procesos iniciados'),
    ('Entrevistas', r['entrevistas'], 'Procesos activos'),
])
st.write('')
left, right = st.columns([1.6, 1])
with left:
    st.markdown('<div class="section-title">Distribución por fuente</div><div class="section-subtitle">Dónde estás encontrando más oportunidades.</div>', unsafe_allow_html=True)
    if r['fuentes']:
        st.bar_chart({x['fuente']: x['cantidad'] for x in r['fuentes']}, height=300)
    else:
        st.info('Todavía no hay ofertas. Sube tu CV y ejecuta tu primera búsqueda.')
with right:
    st.markdown('''<div class="panel-card"><div class="section-title">Próximo paso recomendado</div>
    <div class="section-subtitle">Mantén el proceso simple y medible.</div>
    <p><strong>1.</strong> Revisa que tu CV esté actualizado.</p>
    <p><strong>2.</strong> Ejecuta una búsqueda rápida en 1–3 portales.</p>
    <p><strong>3.</strong> Prioriza ofertas con calce ≥ 70.</p>
    <p><strong>4.</strong> Genera una carta y registra tu postulación.</p></div>''', unsafe_allow_html=True)
