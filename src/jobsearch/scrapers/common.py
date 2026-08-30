"""Utilidades compartidas por los adaptadores de portales de empleo."""

import re
from urllib.parse import urlsplit, urlunsplit

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

_TITULOS_TECNICOS = re.compile(
    r"\b(qa|tester|testing|sdet|quality assurance|analista de pruebas|"
    r"dba|administrador(?:a)? de bases? de datos|database administrator|"
    r"cloud support|soporte cloud|cloud operations|operador cloud|"
    r"analista funcional|business analyst|analista de negocio|"
    r"soporte (?:ti|t[ií]cnico)|mesa de ayuda|service desk|help ?desk)\b",
    re.IGNORECASE,
)

_TITULOS_NO_OBJETIVO = re.compile(
    r"\b(ejecutiv[oa] comercial|ventas?|sales|account manager|marketing|"
    r"reclutador|recruiter|recursos humanos|contador|contable|prevencionista|"
    r"calidad (?:industrial|alimentos?|construcci[oó]n|minera))\b",
    re.IGNORECASE,
)

_SENALES_DESCRIPCION = [
    "casos de prueba", "pruebas funcionales", "pruebas de regresión",
    "test automation", "selenium", "playwright", "cypress", "postman",
    "administrador de base de datos", "oracle dba", "sql server dba",
    "cloud support", "operaciones cloud", "levantamiento de requerimientos",
    "criterios de aceptación", "soporte n1", "soporte n2", "service desk",
]


def nueva_pagina(browser):
    page = browser.new_page(user_agent=USER_AGENT, locale="es-CL")
    page.set_default_timeout(12000)
    return page


def normalizar_link(url):
    partes = urlsplit(url)
    return urlunsplit((partes.scheme, partes.netloc, partes.path, "", ""))


def click_si_existe(page, selector, timeout=3000):
    boton = page.locator(selector)
    if boton.count() > 0:
        try:
            boton.first.click(timeout=timeout)
        except Exception:
            pass


def texto_o_vacio(locator):
    return locator.first.inner_text().strip() if locator.count() > 0 else ""


def es_relevante_perfil(titulo, descripcion=""):
    """Filtro conservador previo al scoring para reducir falsos positivos."""
    titulo = (titulo or "").strip()
    if _TITULOS_NO_OBJETIVO.search(titulo):
        return False
    if _TITULOS_TECNICOS.search(titulo):
        return True
    texto = (descripcion or "").lower()
    coincidencias = sum(1 for s in _SENALES_DESCRIPCION if s in texto)
    return coincidencias >= 2
