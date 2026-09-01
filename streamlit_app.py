import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))

import streamlit as st
from jobsearch.services.cloud import configurado
from jobsearch.services.auth import iniciar_sesion, registrar, cerrar_sesion, usuario_actual
from jobsearch.ui.theme import aplicar_tema

st.set_page_config(page_title='Job Search Dashboard', page_icon='◈', layout='wide', initial_sidebar_state='expanded')
aplicar_tema()

if not configurado():
    st.error('La aplicación no está configurada. Faltan las variables de Supabase.')
    st.stop()

if not usuario_actual():
    st.markdown('<div class="login-shell">', unsafe_allow_html=True)
    st.markdown('''
    <div class="login-brand">
      <div class="logo">JS</div>
      <h1>Job Search Dashboard</h1>
      <p>Tu centro de búsqueda laboral: analiza tu CV, encuentra oportunidades con mejor calce y gestiona cada postulación en un solo lugar.</p>
    </div>
    ''', unsafe_allow_html=True)
    login, signup = st.tabs(['Iniciar sesión', 'Crear cuenta'])
    with login:
        with st.form('login'):
            email = st.text_input('Correo electrónico', placeholder='tu@email.com')
            password = st.text_input('Contraseña', type='password')
            submit = st.form_submit_button('Entrar a mi dashboard', type='primary', use_container_width=True)
        if submit:
            try:
                iniciar_sesion(email.strip(), password); st.rerun()
            except Exception as exc:
                st.error(f'No fue posible iniciar sesión: {exc}')
    with signup:
        with st.form('signup'):
            email2 = st.text_input('Correo electrónico', key='signup_email', placeholder='tu@email.com')
            password2 = st.text_input('Contraseña (mínimo 6 caracteres)', type='password', key='signup_password')
            submit2 = st.form_submit_button('Crear mi cuenta', type='primary', use_container_width=True)
        if submit2:
            try:
                result = registrar(email2.strip(), password2)
                if result.session:
                    st.success('Cuenta creada.'); st.rerun()
                else:
                    st.success('Cuenta creada. Revisa tu correo para confirmar la dirección antes de iniciar sesión.')
            except Exception as exc:
                st.error(f'No fue posible crear la cuenta: {exc}')
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

user = usuario_actual()
st.sidebar.markdown('### ◈ Job Search')
st.sidebar.caption('Dashboard personal de oportunidades')
st.sidebar.markdown('---')
st.sidebar.caption('SESIÓN ACTIVA')
st.sidebar.write(user.email)
if st.sidebar.button('Cerrar sesión', use_container_width=True):
    cerrar_sesion(); st.rerun()

paginas = {
    'INICIO': [st.Page('src/jobsearch/ui/dashboard.py', title='Dashboard', icon='⌂')],
    'DESCUBRIR': [st.Page('src/jobsearch/ui/search.py', title='Buscar ofertas', icon='⌕'), st.Page('src/jobsearch/ui/jobs.py', title='Oportunidades', icon='◫')],
    'SEGUIMIENTO': [st.Page('src/jobsearch/ui/applications.py', title='Postulaciones', icon='✓')],
    'PERFIL': [st.Page('src/jobsearch/ui/profile.py', title='Mi currículum', icon='◉')],
}
pg = st.navigation(paginas)
st.sidebar.caption('Render · Supabase · Playwright')
pg.run()
