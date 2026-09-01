import csv
import io
import os
import html
import streamlit as st
from jobsearch.ui.theme import hero, job_card
from jobsearch.services.profile_service import cargar_perfil, texto_cv
from jobsearch.services.letters import ConfigAPI, coincidencias_cv_oferta, config_api_desde_entorno, generar_borrador_local, generar_carta_inteligente
from jobsearch.services.repository import guardar_carta, guardar_estado, listar_ofertas, obtener_carta, reevaluar_ofertas

hero('Oportunidades', 'Explora vacantes priorizadas por compatibilidad con tu currículum y gestiona cada proceso sin perder contexto.', 'OPORTUNIDADES')

tool_a, tool_b = st.columns([1,4])
if tool_a.button('Reevaluar base', use_container_width=True, help='Recalcula el calce de todas las ofertas guardadas con las reglas actuales.'):
    perfil_actual = cargar_perfil()
    with st.spinner('Reevaluando ofertas guardadas…'):
        result = reevaluar_ofertas(perfil_actual, __import__('jobsearch.services.scoring', fromlist=['evaluar_oferta']).evaluar_oferta)
    st.success(f"{result['actualizadas']} ofertas reevaluadas · {result['descartadas']} quedaron fuera del objetivo.")
    st.rerun()

f1, f2, f3 = st.columns([1,1,1.2])
min_score = f1.select_slider('Calce mínimo', options=[0,30,40,50,60,70,80,90], value=50)
fuente = f2.selectbox('Fuente', ['Todas','GetOnBoard','Computrabajo','ChileTrabajos','BNE','Laborum','Trabajando.com'])
search_text = f3.text_input('Buscar por cargo o empresa', placeholder='Ej. QA, Cloud, empresa…')
rows = listar_ofertas(min_score, None if fuente == 'Todas' else fuente)
if search_text:
    q = search_text.lower().strip()
    rows = [r for r in rows if q in (r.get('titulo','')+' '+r.get('empresa','')).lower()]

st.caption(f'{len(rows)} oportunidades con los filtros actuales')

if rows:
    # CSV compacto
    display = [{k:r.get(k,'') for k in ['puntaje','area','titulo','empresa','fuente','modalidad','estado','link']} for r in rows]
    out=io.StringIO(); writer=csv.DictWriter(out,fieldnames=display[0].keys()); writer.writeheader(); writer.writerows(display)
    _, dl = st.columns([5,1])
    dl.download_button('Exportar CSV', out.getvalue(), 'ofertas.csv', 'text/csv', use_container_width=True)

    st.markdown('### Resultados')
    # Mostrar tarjetas, no dataframe oscuro/scroll horizontal.
    for r in rows[:30]:
        st.markdown(job_card(r), unsafe_allow_html=True)

    st.markdown('---')
    st.markdown('### Gestionar oportunidad')
    opciones = {f"{r['puntaje']} · {r['titulo']} — {r.get('empresa') or 'Empresa no informada'}": r for r in rows}
    elegido = opciones[st.selectbox('Selecciona una vacante', list(opciones), label_visibility='collapsed')]

    with st.container(border=True):
        st.markdown(job_card(elegido), unsafe_allow_html=True)
        if elegido.get('razon'):
            st.caption(elegido['razon'])
        if elegido.get('link'):
            st.link_button('Abrir publicación original ↗', elegido['link'])

    tab_estado, tab_carta = st.tabs(['Seguimiento', 'Carta de presentación'])
    with tab_estado:
        c1,c2=st.columns([.8,1.2])
        estados=['Guardada','Postulada','Entrevista','Rechazada','Oferta recibida']
        actual=elegido.get('estado','Guardada'); idx=estados.index(actual) if actual in estados else 0
        estado=c1.selectbox('Estado',estados,index=idx)
        notas=c2.text_area('Notas',value=elegido.get('notas',''),height=100,key=f"notas_{elegido['id']}")
        if st.button('Guardar seguimiento',type='primary',key=f"estado_{elegido['id']}"):
            guardar_estado(elegido['id'],estado,notas); st.success('Seguimiento actualizado.')

    with tab_carta:
        perfil=cargar_perfil(); coincidencias=coincidencias_cv_oferta(perfil,elegido)
        if coincidencias:
            st.markdown(''.join(f'<span class="badge purple">{html.escape(x)}</span>' for x in coincidencias),unsafe_allow_html=True)
        descripcion=elegido.get('descripcion','') or ''
        with st.expander('Descripción usada para personalizar la carta'):
            st.write(descripcion or 'No hay descripción guardada para esta vacante.')

        modo=st.segmented_control('Generación',['Local','Inteligente (API)'],default='Local',key=f"modo_{elegido['id']}")
        config_entorno=config_api_desde_entorno(); config_api=None
        if modo == 'Inteligente (API)':
            with st.expander('Configurar API',expanded=config_entorno is None):
                base=st.text_input('URL base',value=config_entorno.base_url if config_entorno else os.getenv('LETTER_API_BASE_URL',''),key=f"base_{elegido['id']}")
                model=st.text_input('Modelo',value=config_entorno.model if config_entorno else os.getenv('LETTER_API_MODEL',''),key=f"model_{elegido['id']}")
                key=st.text_input('API key',value=config_entorno.api_key if config_entorno else '',type='password',key=f"key_{elegido['id']}")
                if base and model and key: config_api=ConfigAPI(base_url=base,api_key=key,model=model)

        carta_guardada=obtener_carta(elegido['id']); state_key=f"carta_{elegido['id']}"
        if state_key not in st.session_state: st.session_state[state_key]=carta_guardada['contenido'] if carta_guardada else ''
        if st.button('Generar carta',type='primary',key=f"gen_{elegido['id']}_{modo}"):
            try:
                if modo=='Local': st.session_state[state_key]=generar_borrador_local(elegido,perfil)
                else:
                    if not config_api: raise ValueError('Completa la configuración de API.')
                    cv=texto_cv()
                    if not cv: raise ValueError('Activa primero un currículum.')
                    with st.spinner('Generando carta…'): st.session_state[state_key]=generar_carta_inteligente(elegido,perfil,cv,config_api)
                st.success('Carta generada. Revísala antes de usarla.')
            except Exception as exc: st.error(f'No se pudo generar: {exc}')

        carta=st.text_area('Borrador editable',key=state_key,height=330)
        b1,b2=st.columns(2)
        if b1.button('Guardar borrador',use_container_width=True,disabled=not carta.strip(),key=f"save_{elegido['id']}"):
            guardar_carta(elegido['id'],carta,'inteligente' if modo!='Local' else 'local'); st.success('Borrador guardado.')
        safe=''.join(c if c.isalnum() or c in '_- ' else '' for c in f"{elegido.get('empresa','empresa')}_{elegido.get('titulo','cargo')}").strip().replace(' ','_')
        b2.download_button('Descargar carta',carta,file_name=f'carta_{safe or "presentacion"}.txt',mime='text/plain',use_container_width=True,disabled=not carta.strip())
else:
    st.info('No hay oportunidades que cumplan los filtros. Ejecuta una nueva búsqueda o baja temporalmente el calce mínimo.')
