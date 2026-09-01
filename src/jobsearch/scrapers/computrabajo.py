"""Computrabajo optimizado para páginas públicas.

Solo conserva enlaces de vacantes INDIVIDUALES. Las páginas `/trabajo-de-*` son
resultados de búsqueda y nunca se guardan como ofertas.
"""

import re
import unicodedata
from urllib.parse import quote

from .common import es_relevante_perfil
from .http_common import absolute, jobposting_jsonld, location_text, organization_name, soup, text_from_html

USES_BROWSER = False

NOMBRE = "Computrabajo"
BASE_URL = "https://cl.computrabajo.com"
DETAIL_PREFIX = "/ofertas-de-trabajo/oferta-de-trabajo-de-"
MAX_TERMINOS_RAPIDA = 3
MAX_DETALLES_RAPIDA = 14


def _slug(text):
    x = unicodedata.normalize("NFKD", text.lower())
    x = "".join(c for c in x if not unicodedata.combining(c))
    x = re.sub(r"[^a-z0-9]+", "-", x).strip("-")
    return x


def _links_busqueda(termino):
    url = f"{BASE_URL}/trabajo-de-{_slug(termino)}"
    doc = soup(url, timeout=10)
    links, seen = [], set()
    for a in doc.find_all("a", href=True):
        href = a.get("href", "")
        # Clave: NO aceptar /trabajo-de-* ni páginas regionales/listados.
        if not href.startswith(DETAIL_PREFIX):
            continue
        link = absolute(BASE_URL, href)
        if link not in seen:
            seen.add(link); links.append(link)
    return links


def _extraer(link):
    doc = soup(link, timeout=10)
    job = jobposting_jsonld(doc)
    if job:
        titulo = str(job.get("title") or "").strip()
        empresa = organization_name(job.get("hiringOrganization"))
        descripcion = text_from_html(job.get("description") or "")
        modalidad = location_text(job.get("jobLocation"))
    else:
        h1 = doc.find("h1")
        titulo = h1.get_text(" ", strip=True) if h1 else ""
        # En Computrabajo el texto de la página completa es mejor fallback que
        # selectores CSS frágiles; el filtro posterior exige contexto TI.
        descripcion = doc.get_text(" ", strip=True)
        empresa = ""
        modalidad = ""
    if not titulo:
        raise ValueError("No se identificó título de vacante")
    return {"titulo": titulo, "empresa": empresa, "descripcion": descripcion, "modalidad": modalidad, "link": link, "fuente": NOMBRE}


def buscar_ofertas(browser=None, terminos=None, modo="rapida", progreso=None):
    terminos = list(dict.fromkeys(terminos or []))[:MAX_TERMINOS_RAPIDA if modo == "rapida" else 6]
    links, seen = [], set()
    for idx, termino in enumerate(terminos, 1):
        if progreso: progreso(f"Computrabajo · {idx}/{len(terminos)} · {termino}")
        try:
            for link in _links_busqueda(termino):
                if link not in seen:
                    seen.add(link); links.append(link)
        except Exception as exc:
            if progreso: progreso(f"Computrabajo · consulta omitida: {type(exc).__name__}")
        if modo == "rapida" and len(links) >= MAX_DETALLES_RAPIDA:
            break

    limit = MAX_DETALLES_RAPIDA if modo == "rapida" else 28
    ofertas = []
    for idx, link in enumerate(links[:limit], 1):
        if progreso: progreso(f"Computrabajo · validando {idx}/{min(len(links), limit)}")
        try:
            oferta = _extraer(link)
            if es_relevante_perfil(oferta["titulo"], oferta["descripcion"]):
                ofertas.append(oferta)
        except Exception:
            continue
    return ofertas
