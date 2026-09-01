import json
import time
import streamlit as st
from jobsearch.services.collector import recolectar, FUENTES
from jobsearch.services.repository import guardar_ofertas
from jobsearch.services.scoring import evaluar_oferta
from jobsearch.config import ROOT
from jobsearch.services.profile_service import cargar_perfil, cv_activo
from jobsearch.ui.theme import hero

hero('Buscar oportunidades', 'Usamos los roles detectados en tu CV para consultar fuentes laborales y descartamos resultados que no pertenezcan al contexto TI.', 'DESCUBRIR')
perfil = cargar_perfil(); resumen = perfil.get('resumen', {}); terminos_cv = resumen.get('terminos_busqueda', [])

if not cv_activo():
    st.warning('Activa primero un currículum para personalizar las búsquedas y el scoring.')
else:
    skills = resumen.get('skills_detectadas', [])[:10]
    if skills:
        st.markdown('<div class="surface-card"><div class="section-title">Perfil activo</div><div class="section-subtitle">Estas skills ayudan a puntuar las vacantes; las búsquedas usan cargos específicos para evitar ruido.</div>' + ''.join(f'<span class="badge purple">{x}</span>' for x in skills) + '</div>', unsafe_allow_html=True)

left, right = st.columns([1.05, .95], gap='large')
with left:
    with st.container(border=True):
        st.markdown('#### Configuración de búsqueda')
        st.caption('El modo rápido prioriza velocidad y estabilidad en Render Free.')
        modo_label = st.radio('Modo', ['Rápida', 'Exhaustiva'], horizontal=True)
        modo = 'rapida' if modo_label == 'Rápida' else 'exhaustiva'
        max_terms = 6 if modo == 'rapida' else 12
        terminos_txt = st.text_area('Cargos / búsquedas prioritarias', ', '.join(terminos_cv[:max_terms]), height=115,
                                    help='Usa cargos como “qa software” o “cloud support”; evita skills aisladas como SQL o Java.')
        terminos = list(dict.fromkeys(t.strip() for t in terminos_txt.split(',') if t.strip()))[:max_terms]

with right:
    with st.container(border=True):
        st.markdown('#### Fuentes')
        st.caption('Empieza por 1–2 fuentes. GetOnBoard y Computrabajo ya no necesitan Chromium.')
        fuentes = st.multiselect('Portales', list(FUENTES), default=['GetOnBoard'])
        st.info('GetOnBoard usa sus categorías públicas. Computrabajo solo acepta enlaces de vacantes individuales y descarta páginas de resultados.')

run_col, demo_col, _ = st.columns([1.15, .8, 1.8])
start = run_col.button('Buscar oportunidades', type='primary', use_container_width=True, disabled=not fuentes or not terminos or not cv_activo())
if demo_col.button('Cargar demo', use_container_width=True):
    path = ROOT / 'data' / 'ejemplo_ofertas.json'
    ofertas = json.loads(path.read_text(encoding='utf-8'))
    nuevas = guardar_ofertas(ofertas, perfil, evaluar_oferta)
    st.success(f'Demo cargada: {nuevas} oportunidades nuevas.')

if start:
    inicio = time.monotonic()
    progress = st.progress(0, text='Preparando búsqueda…')
    activity = st.empty()
    current = {'idx': 0, 'total': max(len(fuentes),1)}

    def on_progress(event):
        if event.get('tipo') == 'fuente':
            current['idx'] = event.get('indice', current['idx']); current['total'] = event.get('total', current['total'])
        pct = min(int(((max(current['idx']-1,0)) / current['total']) * 100), 94)
        msg = event.get('mensaje', 'Buscando…')
        progress.progress(pct, text=msg)
        activity.caption(f'{msg} · {int(time.monotonic()-inicio)} s')

    ofertas, errores, estadisticas = recolectar(fuentes, terminos=terminos, modo=modo, progreso=on_progress)
    nuevas = guardar_ofertas(ofertas, perfil, evaluar_oferta)
    total_s = round(time.monotonic()-inicio, 1)
    progress.progress(100, text='Búsqueda finalizada')
    activity.empty()

    st.markdown(f'''<div class="search-summary">
      <div class="search-stat"><b>{len(ofertas)}</b><span>vacantes relevantes</span></div>
      <div class="search-stat"><b>{nuevas}</b><span>nuevas guardadas</span></div>
      <div class="search-stat"><b>{total_s}s</b><span>tiempo total</span></div></div>''', unsafe_allow_html=True)

    for stat in estadisticas:
        if stat['ok']:
            st.success(f"{stat['fuente']}: {stat['cantidad']} vacantes relevantes en {stat['segundos']} s")
        else:
            st.warning(f"{stat['fuente']}: no se pudo completar la consulta.")
    for error in errores:
        st.warning(f"{error['fuente']}: {error['error']}")

st.markdown('---')
st.markdown('#### Criterio de relevancia')
st.caption('Un “QA” ambiguo solo se acepta si la vacante contiene señales de software/TI (testing, APIs, frontend/backend, Postman, Selenium, Jira, regresión, UAT, etc.). QA/QC de minería, construcción, alimentos, planta o ISO se descarta.')
