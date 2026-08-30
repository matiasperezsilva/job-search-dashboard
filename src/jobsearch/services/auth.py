import streamlit as st
from jobsearch.services.cloud import cliente


def usuario_actual():
    return st.session_state.get('auth_user')


def access_token():
    session = st.session_state.get('auth_session')
    return getattr(session, 'access_token', None) if session else None


def client_autenticado():
    token = access_token()
    if not token:
        raise RuntimeError('No hay una sesión iniciada.')
    return cliente(token)


def iniciar_sesion(email, password):
    result = cliente().auth.sign_in_with_password({'email': email, 'password': password})
    if not result.user or not result.session:
        raise RuntimeError('No fue posible iniciar sesión.')
    st.session_state.auth_user = result.user
    st.session_state.auth_session = result.session
    return result.user


def registrar(email, password):
    result = cliente().auth.sign_up({'email': email, 'password': password})
    if result.user and result.session:
        st.session_state.auth_user = result.user
        st.session_state.auth_session = result.session
    return result


def cerrar_sesion():
    try:
        client_autenticado().auth.sign_out()
    except Exception:
        pass
    for key in ('auth_user', 'auth_session'):
        st.session_state.pop(key, None)
