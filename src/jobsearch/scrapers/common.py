"""Utilidades compartidas por los adaptadores de portales de empleo."""

import re
from urllib.parse import urlsplit, urlunsplit

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)

_TITULOS_TECNICOS = re.compile(
    r"\b(qa|tester|testing|sdet|quality assurance|analista de pruebas|"
    r"dba|administrador(?:a)? de bases? de datos|database administrator|"
    r"cloud support|soporte cloud|cloud operations|operador cloud|cloud engineer|devops|"
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


def nueva_pagina(browser, *, timeout_ms=8000):
    page = browser.new_page(user_agent=USER_AGENT, locale="es-CL")
    page.set_default_timeout(timeout_ms)
    page.set_default_navigation_timeout(12000)

    # En Render Free imágenes, fuentes y multimedia sólo consumen CPU/RAM y no
    # aportan nada al scraping. Bloquearlas acelera mucho la navegación.
    def _route(route):
        if route.request.resource_type in {"image", "media", "font"}:
            route.abort()
        else:
            route.continue_()

    page.route("**/*", _route)
    return page


def ir_rapido(page, url, timeout=12000):
    return page.goto(url, wait_until="domcontentloaded", timeout=timeout)


def normalizar_link(url):
    partes = urlsplit(url)
    return urlunsplit((partes.scheme, partes.netloc, partes.path, "", ""))


def click_si_existe(page, selector, timeout=1500):
    boton = page.locator(selector)
    if boton.count() > 0:
        try:
            boton.first.click(timeout=timeout)
        except Exception:
            pass


def texto_o_vacio(locator):
    try:
        return locator.first.inner_text(timeout=2500).strip() if locator.count() > 0 else ""
    except Exception:
        return ""


def titulo_parece_relevante(titulo, terminos=None):
    titulo = (titulo or "").strip()
    if not titulo or _TITULOS_NO_OBJETIVO.search(titulo):
        return False
    if _TITULOS_TECNICOS.search(titulo):
        return True
    t = titulo.lower()
    return any(term.lower() in t for term in (terminos or []) if len(term.strip()) >= 2)


def es_relevante_perfil(titulo, descripcion=""):
    titulo = (titulo or "").strip()
    if _TITULOS_NO_OBJETIVO.search(titulo):
        return False
    if _TITULOS_TECNICOS.search(titulo):
        return True
    texto = (descripcion or "").lower()
    coincidencias = sum(1 for s in _SENALES_DESCRIPCION if s in texto)
    return coincidencias >= 2
