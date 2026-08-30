import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))

import streamlit as st
from jobsearch.services.cloud import configurado
from jobsearch.services.auth import iniciar_sesion, registrar, cerrar_sesion, usuario_actual

st.set_page_config(page_title='Job Search Dashboard', page_icon='🔎', layout='wide')

if not configurado():
    st.error('La aplicación no está configurada. Faltan las variables de Supabase.')
    st.stop()

if not usuario_actual():
    st.title('🔎 Job Search Dashboard')
    st.write('Busca ofertas según tu currículum, prioriza las mejores coincidencias y gestiona tus postulaciones desde la web.')
    login, signup = st.tabs(['Iniciar sesión', 'Crear cuenta'])
    with login:
        with st.form('login'):
            email = st.text_input('Correo electrónico')
            password = st.text_input('Contraseña', type='password')
            submit = st.form_submit_button('Iniciar sesión', type='primary')
        if submit:
            try:
                iniciar_sesion(email.strip(), password)
                st.rerun()
            except Exception as exc:
                st.error(f'No fue posible iniciar sesión: {exc}')
    with signup:
        with st.form('signup'):
            email2 = st.text_input('Correo electrónico', key='signup_email')
            password2 = st.text_input('Contraseña (mínimo 6 caracteres)', type='password', key='signup_password')
            submit2 = st.form_submit_button('Crear cuenta')
        if submit2:
            try:
                result = registrar(email2.strip(), password2)
                if result.session:
                    st.success('Cuenta creada.')
                    st.rerun()
                else:
                    st.success('Cuenta creada. Revisa tu correo para confirmar la dirección antes de iniciar sesión.')
            except Exception as exc:
                st.error(f'No fue posible crear la cuenta: {exc}')
    st.stop()

user = usuario_actual()
st.sidebar.success(user.email)
if st.sidebar.button('Cerrar sesión'):
    cerrar_sesion(); st.rerun()

paginas = {
    'Panel': [st.Page('src/jobsearch/ui/dashboard.py', title='Resumen', icon='📊')],
    'Búsqueda': [st.Page('src/jobsearch/ui/search.py', title='Buscar ofertas', icon='🔎')],
    'Gestión': [st.Page('src/jobsearch/ui/jobs.py', title='Ofertas', icon='💼'), st.Page('src/jobsearch/ui/applications.py', title='Postulaciones', icon='✅')],
    'Configuración': [st.Page('src/jobsearch/ui/profile.py', title='Currículum', icon='📄')],
}
pg = st.navigation(paginas)
st.sidebar.caption('Job Search Dashboard · Cloud')
pg.run()
