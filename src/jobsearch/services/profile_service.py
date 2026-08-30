from jobsearch.config import perfil_demo
from jobsearch.services.repository import obtener_perfil


def cargar_perfil():
    row = obtener_perfil()
    return (row.get('profile_data') if row else None) or perfil_demo()


def cv_activo():
    return obtener_perfil() is not None


def texto_cv():
    row = obtener_perfil()
    return (row or {}).get('cv_text', '')
