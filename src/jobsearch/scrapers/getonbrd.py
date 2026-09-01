"""GetOnBoard mediante páginas públicas, sin Chromium."""

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .common import es_relevante_perfil, titulo_parece_relevante
from .http_common import (
    absolute,
    date_posted,
    get_html,
    jobposting_jsonld,
    location_text,
    organization_name,
    soup,
    text_from_html,
)

USES_BROWSER = False
NOMBRE = "GetOnBoard"
BASE_URL = "https://www.getonbrd.com"
CATEGORIAS_RAPIDAS = ["/jobs/sysadmin-devops-qa", "/jobs/data-science-analytics"]
CATEGORIAS_EXTRA = ["/jobs/innovation-agile", "/jobs/customer-support"]


def _titulo_hint(texto: str) -> str:
    texto = re.sub(r"\s+", " ", (texto or "")).strip()
    # Las cards suelen concatenar título + tipo de contrato + empresa + ubicación.
    return re.split(
        r"\s+(?:Full time|Part time|Freelance|Internship|No experience required)\b",
        texto,
        maxsplit=1,
        flags=re.I,
    )[0].strip()


def _links_categoria(path: str):
    html = get_html(BASE_URL + path, timeout=8)
    doc = BeautifulSoup(html, "html.parser")
    categoria = path.rstrip("/").split("/")[-1]
    items, seen = [], set()

    for a in doc.find_all("a", href=True):
        href = a.get("href", "").strip()
        url = absolute(BASE_URL, href).split("?")[0]
        parsed = urlparse(url)
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) < 3 or parts[0] not in {"jobs", "empleos"} or parts[1] != categoria:
            continue
        if url in seen:
            continue
        seen.add(url)
        items.append((url, _titulo_hint(a.get_text(" ", strip=True))))

    # Fallback ante cambios de marcado: extraer hrefs del HTML crudo.
    patron = re.compile(
        r'href=["\']([^"\']*/(?:jobs|empleos)/' + re.escape(categoria) + r'/[^"\'?#]+)',
        re.I,
    )
    for href in patron.findall(html):
        url = absolute(BASE_URL, href).split("?")[0]
        if url not in seen:
            seen.add(url)
            items.append((url, ""))
    return items


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
        descripcion = doc.get_text(" ", strip=True)
        empresa = ""
        modalidad = ""
        publicada = ""
    if not titulo:
        raise ValueError("GetOnBoard no entregó título para la vacante")
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
    categorias = CATEGORIAS_RAPIDAS if modo == "rapida" else CATEGORIAS_RAPIDAS + CATEGORIAS_EXTRA
    items, seen = [], set()

    for i, cat in enumerate(categorias, 1):
        if progreso:
            progreso(f"GetOnBoard · categoría {i}/{len(categorias)}")
        try:
            for link, hint in _links_categoria(cat):
                if link not in seen:
                    seen.add(link)
                    items.append((link, hint))
        except Exception as exc:
            if progreso:
                progreso(f"GetOnBoard · categoría omitida: {type(exc).__name__}")

    def prioridad(item):
        hint = item[1]
        if titulo_parece_relevante(hint, terminos):
            return 0
        if any(k in hint.lower() for k in ("qa", "tester", "sdet", "cloud", "devops", "dba", "sre", "soporte")):
            return 1
        return 2

    items.sort(key=prioridad)
    limit = 14 if modo == "rapida" else 36
    ofertas = []

    for i, (link, hint) in enumerate(items[:limit], 1):
        if progreso:
            progreso(f"GetOnBoard · analizando {i}/{min(len(items), limit)}")
        try:
            oferta = _extraer(link)
            if es_relevante_perfil(oferta["titulo"], oferta["descripcion"], terminos) or titulo_parece_relevante(
                oferta["titulo"], terminos
            ):
                ofertas.append(oferta)
        except Exception:
            # Si el detalle puntual falla pero la card trae un cargo técnico explícito,
            # conservar el enlace. El scoring de GetOnBoard puede trabajar con el título.
            if hint and titulo_parece_relevante(hint, terminos):
                ofertas.append(
                    {
                        "titulo": hint,
                        "empresa": "",
                        "descripcion": "",
                        "modalidad": "",
                        "link": link,
                        "fuente": NOMBRE,
                        "published_at": "",
                    }
                )

    return ofertas
