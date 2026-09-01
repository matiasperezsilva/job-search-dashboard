import json
import streamlit as st
from jobsearch.services.cv_profile import extraer_texto_cv, construir_perfil_desde_texto
from jobsearch.services.repository import guardar_perfil, obtener_perfil, eliminar_perfil
from jobsearch.config import perfil_demo
from jobsearch.ui.theme import hero

hero('Tu currículum define la búsqueda', 'Sube tu CV y la aplicación detectará áreas, tecnologías y términos relevantes para encontrar oportunidades con mejor calce.', 'PERFIL PROFESIONAL')

left, right = st.columns([1.15,.85])
with left:
    st.markdown('<div class="section-title">Actualizar currículum</div><div class="section-subtitle">PDF, DOCX o TXT. El archivo original se procesa en memoria y no se conserva.</div>', unsafe_allow_html=True)
    archivo = st.file_uploader('Arrastra tu currículum aquí', type=['pdf','docx','txt'], accept_multiple_files=False, label_visibility='collapsed')
    if archivo is not None:
        try:
            texto = extraer_texto_cv(archivo.name, archivo.getvalue())
            perfil_nuevo = construir_perfil_desde_texto(texto)
            resumen_nuevo = perfil_nuevo['resumen']
            st.success(f'CV procesado correctamente · {len(texto):,} caracteres')
            st.markdown('**Áreas detectadas**')
            st.markdown(''.join(f'<span class="badge badge-blue">{x}</span>' for x in resumen_nuevo['areas_detectadas']) or '—', unsafe_allow_html=True)
            st.markdown('**Tecnologías / skills**')
            st.markdown(''.join(f'<span class="badge">{x}</span>' for x in resumen_nuevo['skills_detectadas']) or '—', unsafe_allow_html=True)
            terminos_txt = st.text_area('Términos de búsqueda propuestos', ', '.join(resumen_nuevo['terminos_busqueda']), height=110)
            if st.button('Activar este currículum', type='primary', use_container_width=True):
                perfil_nuevo['resumen']['terminos_busqueda'] = list(dict.fromkeys(t.strip() for t in terminos_txt.split(',') if t.strip()))[:25]
                guardar_perfil(perfil_nuevo, texto, archivo.name)
                st.success('Perfil actualizado en la nube.'); st.rerun()
        except Exception as exc:
            st.error(f'No se pudo procesar el currículum: {exc}')

with right:
    registro = obtener_perfil()
    perfil = (registro.get('profile_data') or {}) if registro else perfil_demo()
    resumen = perfil.get('resumen', {})
    titulo = registro.get('cv_name') if registro else 'Perfil de demostración'
    st.markdown(f'''<div class="panel-card"><div class="section-title">Perfil activo</div><div class="section-subtitle">{titulo}</div>
    <p><strong>{len(resumen.get('areas_detectadas',[]))}</strong> áreas detectadas</p>
    <p><strong>{len(resumen.get('skills_detectadas',[]))}</strong> tecnologías / skills</p>
    <p><strong>{len(resumen.get('terminos_busqueda',[]))}</strong> términos de búsqueda</p></div>''', unsafe_allow_html=True)
    if resumen.get('areas_detectadas'):
        st.markdown(''.join(f'<span class="badge badge-blue">{x}</span>' for x in resumen['areas_detectadas']), unsafe_allow_html=True)
    if resumen.get('skills_detectadas'):
        st.markdown(''.join(f'<span class="badge">{x}</span>' for x in resumen['skills_detectadas'][:12]), unsafe_allow_html=True)

st.write('')
with st.expander('Ver perfil técnico generado'):
    st.code(json.dumps(perfil, ensure_ascii=False, indent=2), language='json')
if registro and st.button('Eliminar CV y perfil almacenado'):
    eliminar_perfil(); st.success('Perfil eliminado.'); st.rerun()
