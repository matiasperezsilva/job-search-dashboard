import json
import streamlit as st
from jobsearch.services.cv_profile import extraer_texto_cv, construir_perfil_desde_texto
from jobsearch.services.repository import guardar_perfil, obtener_perfil, eliminar_perfil
from jobsearch.config import perfil_demo

st.title('📄 Currículum y perfil de búsqueda')
st.write('Sube tu currículum y la aplicación construirá el perfil usado para buscar y puntuar ofertas. El PDF/DOCX original se procesa en memoria y no se conserva; se guarda de forma privada el texto extraído para generar cartas personalizadas.')

archivo = st.file_uploader('Currículum', type=['pdf','docx','txt'], accept_multiple_files=False)
if archivo is not None:
    try:
        texto = extraer_texto_cv(archivo.name, archivo.getvalue())
        perfil = construir_perfil_desde_texto(texto)
        st.success(f'Currículum procesado: {len(texto):,} caracteres extraídos.')
        resumen = perfil['resumen']; c1,c2=st.columns(2)
        c1.subheader('Áreas detectadas'); c1.write(resumen['areas_detectadas'] or 'No se detectaron áreas específicas')
        c2.subheader('Tecnologías / skills'); c2.write(resumen['skills_detectadas'] or 'No se detectaron tecnologías conocidas')
        terminos_txt = st.text_area('Términos de búsqueda propuestos', ', '.join(resumen['terminos_busqueda']), height=100)
        if st.button('Usar este CV como perfil activo', type='primary'):
            perfil['resumen']['terminos_busqueda'] = list(dict.fromkeys(t.strip() for t in terminos_txt.split(',') if t.strip()))[:25]
            guardar_perfil(perfil, texto, archivo.name)
            st.success('Perfil guardado de forma privada en la nube.'); st.rerun()
    except Exception as exc:
        st.error(f'No se pudo procesar el currículum: {exc}')

st.divider(); st.subheader('Perfil activo')
registro = obtener_perfil()
if registro:
    perfil = registro.get('profile_data') or {}
    st.success(f"CV activo: {registro.get('cv_name') or 'currículum procesado'}")
else:
    perfil = perfil_demo(); st.info('Todavía no hay un CV activo. Se muestra el perfil de demostración.')
resumen = perfil.get('resumen', {})
st.write('**Áreas:**', ', '.join(resumen.get('areas_detectadas', [])) or '—')
st.write('**Skills:**', ', '.join(resumen.get('skills_detectadas', [])) or '—')
st.write('**Búsquedas:**', ', '.join(resumen.get('terminos_busqueda', [])) or '—')
with st.expander('Ver perfil técnico generado'):
    st.code(json.dumps(perfil, ensure_ascii=False, indent=2), language='json')
if registro and st.button('Eliminar mi CV y perfil almacenado'):
    eliminar_perfil(); st.success('Perfil eliminado.'); st.rerun()
