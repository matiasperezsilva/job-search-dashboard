"""Utilidades compartidas por los adaptadores de portales de empleo."""

import re
import unicodedata
from urllib.parse import urlsplit, urlunsplit

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)

_TITULOS_TECNICOS = re.compile(
    r"\b(qa(?:\s+(?:engineer|analyst|automation|manual|funcional|software))?|tester|testing|sdet|quality assurance|analista(?:\s+de)?\s+(?:qa|pruebas)|"
    r"dba|administrador(?:a)? de bases? de datos|database administrator|"
    r"cloud support|soporte cloud|cloud operations|operador cloud|cloud engineer|devops|sre|"
    r"analista funcional|business analyst|analista de negocio|"
    r"soporte (?:ti|t[ií]cnico)|mesa de ayuda|service desk|help ?desk)\b",
    re.IGNORECASE,
)

_TITULOS_NO_OBJETIVO = re.compile(
    r"\b(ejecutiv[oa] comercial|ventas?|sales|account manager|marketing|"
    r"reclutador|recruiter|recursos humanos|contador|contable|prevencionista)\b",
    re.IGNORECASE,
)

# Señales que permiten distinguir QA de software de QA/QC industrial, alimentos,
# minería, construcción, laboratorio, etc.
_SOFTWARE_SIGNALS = [
    "software", "aplicación", "aplicaciones", "sistema", "sistemas", "frontend", "backend",
    "web", "mobile", "api", "rest", "postman", "selenium", "cypress", "playwright",
    "jmeter", "jira", "azure devops", "bug", "bugs", "defecto", "defectos", "regresión",
    "regression", "casos de prueba", "test cases", "testing funcional", "pruebas funcionales",
    "automatización", "automation", "uat", "criterios de aceptación", "scrum", "agile",
    "sql", "base de datos", "microservicios", "ciclo de desarrollo", "sdlc", "devops",
]

_NON_SOFTWARE_QUALITY = [
    "minería", "mineria", "construcción", "construccion", "obra", "obras", "planta",
    "producción", "produccion", "manufactura", "alimentos", "alimentaria", "laboratorio",
    "químico", "quimico", "química", "quimica", "farmacéutico", "farmaceutico",
    "farmacéutica", "farmaceutica", "soldadura", "inspección", "inspeccion", "iso 9001",
    "haccp", "bpm", "calidad de vida", "control de calidad", "aseguramiento de calidad",
    "qa/qc", "qc", "metrología", "metrologia", "materiales", "faena", "minero", "minera",
]

_SEO_OR_SEARCH_PAGE = re.compile(
    r"^(ofertas? de trabajo de|trabajos? de|empleos? de|de qa\b|qa en\b)", re.IGNORECASE
)


def _norm(texto: str) -> str:
    text = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in text if not unicodedata.combining(c)).lower().strip()


def nueva_pagina(browser, *, timeout_ms=8000):
    page = browser.new_page(user_agent=USER_AGENT, locale="es-CL")
    page.set_default_timeout(timeout_ms)
    page.set_default_navigation_timeout(12000)

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


def es_pagina_busqueda(titulo: str) -> bool:
    return bool(_SEO_OR_SEARCH_PAGE.search((titulo or "").strip()))


def contexto_software(titulo: str, descripcion: str = "") -> int:
    texto = _norm(f"{titulo} {descripcion}")
    return sum(1 for s in _SOFTWARE_SIGNALS if _norm(s) in texto)


def contexto_calidad_no_software(titulo: str, descripcion: str = "") -> int:
    texto = _norm(f"{titulo} {descripcion}")
    return sum(1 for s in _NON_SOFTWARE_QUALITY if _norm(s) in texto)


def titulo_parece_relevante(titulo, terminos=None):
    titulo = (titulo or "").strip()
    if not titulo or es_pagina_busqueda(titulo) or _TITULOS_NO_OBJETIVO.search(titulo):
        return False
    if _TITULOS_TECNICOS.search(titulo):
        return True
    t = _norm(titulo)
    # Nunca usar skills genéricas (sql, linux, java...) como sustituto de un rol.
    return any(
        _norm(term) in t
        for term in (terminos or [])
        if len(term.strip()) >= 4 and any(k in _norm(term) for k in ("qa", "tester", "cloud", "dba", "soporte", "analista"))
    )


def es_relevante_perfil(titulo, descripcion=""):
    titulo = (titulo or "").strip()
    if not titulo or es_pagina_busqueda(titulo) or _TITULOS_NO_OBJETIVO.search(titulo):
        return False

    software = contexto_software(titulo, descripcion)
    no_software = contexto_calidad_no_software(titulo, descripcion)
    tnorm = _norm(titulo)

    # QA ambiguo necesita contexto tecnológico real. Un QA/QC industrial con ISO,
    # minería, planta, alimentos, etc. se descarta incluso si incluye "QA".
    qa_ambiguo = bool(re.search(r"\b(qa|quality|calidad|tester|testing)\b", tnorm))
    if qa_ambiguo:
        if no_software >= 1 and software < 2:
            return False
        return software >= 1 or bool(re.search(r"\b(qa (engineer|analyst|automation|manual|funcional|software)|sdet|tester de software)\b", tnorm))

    if _TITULOS_TECNICOS.search(titulo):
        return True
    return software >= 2
