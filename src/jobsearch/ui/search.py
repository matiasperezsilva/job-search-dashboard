import json
import time
import streamlit as st
from jobsearch.services.collector import recolectar, FUENTES
from jobsearch.services.repository import guardar_ofertas
from jobsearch.services.scoring import evaluar_oferta
from jobsearch.config import ROOT
from jobsearch.services.profile_service import cargar_perfil, cv_activo
from jobsearch.ui.theme import hero

hero('Encuentra oportunidades con mejor calce', 'La búsqueda usa señales extraídas de tu CV y luego puntúa cada vacante para ayudarte a priorizar.', 'BÚSQUEDA INTELIGENTE')
perfil = cargar_perfil(); resumen = perfil.get('resumen', {}); terminos_cv = resumen.get('terminos_busqueda', [])

if not cv_activo():
    st.warning('No hay un CV activo. Puedes probar con datos de demostración, pero la búsqueda personalizada requiere subir tu currículum.')
else:
    skills = resumen.get('skills_detectadas', [])[:8]
    if skills:
        st.markdown(''.join(f'<span class="badge">{x}</span>' for x in skills), unsafe_allow_html=True)

st.write('')
col_cfg, col_src = st.columns([1, 1.25])
with col_cfg:
    st.markdown('<div class="section-title">Configuración</div><div class="section-subtitle">En Render Free recomendamos búsquedas cortas y secuenciales.</div>', unsafe_allow_html=True)
    modo_label = st.radio('Tipo de búsqueda', ['Rápida · recomendada', 'Exhaustiva · más lenta'], horizontal=False)
    modo = 'rapida' if modo_label.startswith('Rápida') else 'exhaustiva'
    max_terms = 6 if modo == 'rapida' else 12
    terminos_txt = st.text_area('Términos prioritarios', ', '.join(terminos_cv[:max_terms]), height=120, help=f'Se usarán como máximo {max_terms} términos en este modo.')
    terminos = list(dict.fromkeys(t.strip() for t in terminos_txt.split(',') if t.strip()))[:max_terms]
with col_src:
    st.markdown('<div class="section-title">Fuentes</div><div class="section-subtitle">Para la primera prueba selecciona 1 o 2 portales.</div>', unsafe_allow_html=True)
    recomendadas = ['GetOnBoard', 'ChileTrabajos', 'BNE']
    fuentes = st.multiselect('Portales a consultar', list(FUENTES), default=['GetOnBoard'])
    st.caption('GetOnBoard usa ahora sus categorías técnicas públicas para reducir fallos y tiempo de ejecución. Computrabajo puede bloquear servidores automatizados.')

run_col, demo_col, _ = st.columns([1, 1, 1.6])
if run_col.button('Buscar oportunidades', type='primary', use_container_width=True, disabled=not fuentes or not terminos):
    inicio = time.monotonic()
    progress = st.progress(0, text='Preparando búsqueda…')
    activity = st.empty()
    current = {'idx': 0, 'total': max(len(fuentes),1)}

    def on_progress(event):
        if event.get('tipo') == 'fuente':
            current['idx'] = event.get('indice', current['idx']); current['total'] = event.get('total', current['total'])
        pct = min(int(((max(current['idx']-1,0)) / current['total']) * 100), 95)
        progress.progress(pct, text=event.get('mensaje', 'Buscando…'))
        elapsed = int(time.monotonic() - inicio)
        activity.caption(f"{event.get('mensaje','Procesando')} · {elapsed}s transcurridos")

    with st.status('Búsqueda en curso', expanded=True) as status:
        st.write(f"**Modo:** {'Rápido' if modo == 'rapida' else 'Exhaustivo'} · **Fuentes:** {', '.join(fuentes)}")
        ofertas, errores, estadisticas = recolectar(fuentes, terminos=terminos, modo=modo, progreso=on_progress)
        nuevas = guardar_ofertas(ofertas, perfil, evaluar_oferta)
        progress.progress(100, text='Búsqueda finalizada')
        elapsed = round(time.monotonic()-inicio, 1)
        st.success(f'{len(ofertas)} ofertas procesadas · {nuevas} nuevas · {elapsed}s')
        for stat in estadisticas:
            icon = '✅' if stat['ok'] else '⚠️'
            st.write(f"{icon} **{stat['fuente']}** — {stat['cantidad']} resultados · {stat['segundos']}s")
        for error in errores:
            st.warning(f"{error['fuente']}: {error['error']}")
        status.update(label='Búsqueda finalizada', state='complete')

if demo_col.button('Ver demo', use_container_width=True):
    path = ROOT / 'data' / 'ejemplo_ofertas.json'
    ofertas = json.loads(path.read_text(encoding='utf-8'))
    nuevas = guardar_ofertas(ofertas, perfil, evaluar_oferta)
    st.success(f'Datos de demostración cargados ({nuevas} nuevos).')

st.markdown('---')
st.markdown('<div class="section-title">Cómo obtener mejores resultados</div>', unsafe_allow_html=True)
st.caption('Empieza con GetOnBoard, ChileTrabajos o BNE. Añade Computrabajo solo como fuente secundaria si responde bien desde Render. La app seguirá funcionando aunque una fuente falle.')
