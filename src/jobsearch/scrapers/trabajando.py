"""Trabajando.com mediante páginas públicas, sin Chromium."""

import re
import unicodedata

from .common import es_relevante_perfil, titulo_parece_relevante
from .http_common import absolute, date_posted, jobposting_jsonld, location_text, organization_name, soup, text_from_html

USES_BROWSER = False
NOMBRE = "Trabajando.com"
BASE_URL = "https://www.trabajando.cl"
MAX_TERMINOS_RAPIDA = 2
MAX_DETALLES_RAPIDA = 8


def _slug(text: str) -> str:
    value = unicodedata.normalize("NFKD", text.lower())
    value = "".join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")


def _links_busqueda(termino: str):
    doc = soup(f"{BASE_URL}/trabajo-{_slug(termino)}", timeout=8)
    items, seen = [], set()
    for a in doc.find_all("a", href=True):
        href = (a.get("href") or "").strip()
        # Las fichas individuales actuales usan /trabajo/<id>-<slug>.
        if not re.match(r"^/trabajo/\d+-[a-z0-9-]+/?$", href, re.I):
            continue
        link = absolute(BASE_URL, href).split("?")[0]
        if link in seen:
            continue
        seen.add(link)
        items.append((link, a.get_text(" ", strip=True)))
    return items


def _empresa_fallback(doc) -> str:
    # En las fichas suele existir un bloque "Publicada ... por <empresa>".
    text = doc.get_text("\n", strip=True)
    match = re.search(r"Publicada\s+(?:hace\s+[^\n]+\s+)?por\s*\n?([^\n]{2,100})", text, re.I)
    return match.group(1).strip() if match else ""


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
        empresa = _empresa_fallback(doc)
        descripcion = doc.get_text(" ", strip=True)
        modalidad = ""
        publicada = ""
    if not titulo:
        raise ValueError("Trabajando.com no entregó título para la vacante")
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
            progreso(f"Trabajando.com · {idx}/{len(terminos)} · {termino}")
        try:
            for link, hint in _links_busqueda(termino):
                if link not in seen:
                    seen.add(link)
                    items.append((link, hint))
        except Exception as exc:
            if progreso:
                progreso(f"Trabajando.com · consulta omitida: {type(exc).__name__}")

    items.sort(key=lambda item: 0 if titulo_parece_relevante(item[1], terminos) else 1)
    limite = MAX_DETALLES_RAPIDA if modo == "rapida" else 18
    ofertas = []
    for idx, (link, _hint) in enumerate(items[:limite], 1):
        if progreso:
            progreso(f"Trabajando.com · validando {idx}/{min(len(items), limite)}")
        try:
            oferta = _extraer(link)
            if es_relevante_perfil(oferta["titulo"], oferta["descripcion"], terminos):
                ofertas.append(oferta)
        except Exception:
            continue
    return ofertas
