"""GetOnBoard usando HTML público + JSON-LD.

No requiere Chromium: las páginas de categoría y detalle son públicas y contienen
suficiente información server-side. Esto reduce mucho el tiempo y memoria en Render.
"""

import re
from .common import es_relevante_perfil
from .http_common import absolute, jobposting_jsonld, location_text, organization_name, soup, text_from_html

USES_BROWSER = False

NOMBRE = "GetOnBoard"
BASE_URL = "https://www.getonbrd.com"
CATEGORIAS_RAPIDAS = ["/jobs/sysadmin-devops-qa", "/jobs/data-science-analytics"]
CATEGORIAS_EXTRA = ["/jobs/innovation-agile", "/jobs/customer-support"]
MAX_DETALLES_RAPIDA = 18


def _links_categoria(path):
    doc = soup(BASE_URL + path, timeout=10)
    prefix = path.rstrip("/") + "/"
    links = []
    seen = set()
    for a in doc.find_all("a", href=True):
        href = a.get("href", "")
        if href.startswith(prefix) and href != path and href not in seen:
            # Un job real tiene un slug después de la categoría.
            tail = href[len(prefix):].strip("/")
            if tail and "/" not in tail:
                seen.add(href)
                links.append(absolute(BASE_URL, href))
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
        descripcion = doc.get_text(" ", strip=True)
        empresa = ""
        modalidad = ""
    if not titulo:
        raise ValueError("GetOnBoard no entregó título para la vacante")
    return {"titulo": titulo, "empresa": empresa, "descripcion": descripcion, "modalidad": modalidad, "link": link, "fuente": NOMBRE}


def buscar_ofertas(browser=None, terminos=None, modo="rapida", progreso=None):
    categorias = CATEGORIAS_RAPIDAS if modo == "rapida" else CATEGORIAS_RAPIDAS + CATEGORIAS_EXTRA
    links, seen = [], set()
    for i, cat in enumerate(categorias, 1):
        if progreso: progreso(f"GetOnBoard · categoría {i}/{len(categorias)}")
        try:
            for link in _links_categoria(cat):
                if link not in seen:
                    seen.add(link); links.append(link)
        except Exception as exc:
            if progreso: progreso(f"GetOnBoard · categoría omitida: {type(exc).__name__}")

    limit = MAX_DETALLES_RAPIDA if modo == "rapida" else 35
    ofertas = []
    for i, link in enumerate(links[:limit], 1):
        if progreso: progreso(f"GetOnBoard · analizando {i}/{min(len(links), limit)}")
        try:
            oferta = _extraer(link)
            if es_relevante_perfil(oferta["titulo"], oferta["descripcion"]):
                ofertas.append(oferta)
        except Exception:
            continue
    return ofertas
