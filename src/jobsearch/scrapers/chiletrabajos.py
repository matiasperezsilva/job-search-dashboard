"""ChileTrabajos mediante páginas públicas, sin Chromium."""

import re
from urllib.parse import quote_plus

from .common import es_relevante_perfil, titulo_parece_relevante
from .http_common import absolute, date_posted, jobposting_jsonld, location_text, organization_name, soup, text_from_html

USES_BROWSER = False
NOMBRE = "ChileTrabajos"
BASE_URL = "https://www.chiletrabajos.cl"
MAX_TERMINOS_RAPIDA = 2
MAX_DETALLES_RAPIDA = 8


def _links_busqueda(termino: str):
    query = quote_plus(termino.strip())
    url = f"{BASE_URL}/encuentra-un-empleo/?2={query}&filterSearch=Buscar"
    doc = soup(url, timeout=8)
    links, seen = [], set()
    for a in doc.find_all("a", href=True):
        href = (a.get("href") or "").strip()
        if not re.match(r"^/trabajo/(?:[\w-]+-)?\d+/?$", href):
            continue
        link = absolute(BASE_URL, href).split("?")[0]
        if link not in seen:
            seen.add(link)
            links.append((link, a.get_text(" ", strip=True)))
    return links


def _texto_celda(doc, etiqueta: str) -> str:
    for cell in doc.find_all(["td", "th"]):
        if cell.get_text(" ", strip=True).lower() == etiqueta.lower():
            nxt = cell.find_next_sibling("td")
            if nxt:
                return nxt.get_text(" ", strip=True)
    return ""


def _extraer(link: str):
    doc = soup(link, timeout=8)
    job = jobposting_jsonld(doc)
    if job:
        titulo = str(job.get("title") or "").strip()
        empresa = organization_name(job.get("hiringOrganization"))
        descripcion = text_from_html(job.get("description") or "")
        modalidad = location_text(job.get("jobLocation"))
        publicada = date_posted(job)
    else:
        h1 = doc.find("h1")
        titulo = h1.get_text(" ", strip=True) if h1 else ""
        empresa = _texto_celda(doc, "Buscado")
        modalidad = _texto_celda(doc, "Ubicación")
        # El texto completo es un fallback estable; el filtro posterior exige contexto TI.
        descripcion = doc.get_text(" ", strip=True)
        publicada = ""
    if not titulo:
        raise ValueError("ChileTrabajos no entregó título para la vacante")
    return {
        "titulo": titulo,
        "empresa": empresa,
        "descripcion": descripcion,
        "modalidad": modalidad,
        "link": link,
        "fuente": NOMBRE,
        "published_at": publicada,
    }


def buscar_ofertas(browser=None, terminos=None, modo="rapida", progreso=None):
    limite_terminos = MAX_TERMINOS_RAPIDA if modo == "rapida" else 5
    terminos = list(dict.fromkeys(terminos or []))[:limite_terminos]
    items, seen = [], set()

    for idx, termino in enumerate(terminos, 1):
        if progreso:
            progreso(f"ChileTrabajos · {idx}/{len(terminos)} · {termino}")
        try:
            for link, hint in _links_busqueda(termino):
                if link not in seen:
                    seen.add(link)
                    items.append((link, hint))
        except Exception as exc:
            if progreso:
                progreso(f"ChileTrabajos · consulta omitida: {type(exc).__name__}")

    # Títulos que ya parecen del perfil se leen primero.
    items.sort(key=lambda item: 0 if titulo_parece_relevante(item[1], terminos) else 1)
    limite = MAX_DETALLES_RAPIDA if modo == "rapida" else 18
    ofertas = []

    for idx, (link, _hint) in enumerate(items[:limite], 1):
        if progreso:
            progreso(f"ChileTrabajos · validando {idx}/{min(len(items), limite)}")
        try:
            oferta = _extraer(link)
            if es_relevante_perfil(oferta["titulo"], oferta["descripcion"], terminos):
                ofertas.append(oferta)
        except Exception:
            continue
    return ofertas
