"""Trabajando.com: navegación pública con Playwright.

El listado público /trabajo-<termino> y las fichas /trabajo/<id>-<slug> existen
sin autenticación. Se usa navegador porque desde hosts cloud la respuesta HTTP
directa puede agotar timeout aunque la página pública cargue normalmente.
"""

import re
import unicodedata
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from .common import nueva_pagina, titulo_parece_relevante
from .http_common import date_posted, jobposting_jsonld, location_text, organization_name, text_from_html

USES_BROWSER = True
NOMBRE = "Trabajando.com"
BASE_URL = "https://www.trabajando.cl"
MAX_TERMINOS_RAPIDA = 4
MAX_DETALLES_RAPIDA = 12
_LAST_DIAGNOSTIC = {}


def get_last_diagnostic():
    return dict(_LAST_DIAGNOSTIC)


def _slug(text: str) -> str:
    value = unicodedata.normalize("NFKD", (text or "").lower())
    value = "".join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")


def _blocked(body: str) -> bool:
    low = (body or "").lower()
    return any(x in low for x in (
        "captcha", "access denied", "verify you are human",
        "verifica que eres humano", "cloudflare", "temporarily blocked",
    ))


def _links_busqueda(page, termino: str):
    # La ruta estable actual es /trabajo-empleo/chile. La búsqueda por keyword
    # se ejecuta desde el formulario del frontend; /trabajo-<slug> dejó de ser
    # confiable para obtener listados desde Render.
    page.goto(f"{BASE_URL}/trabajo-empleo/chile", wait_until="domcontentloaded", timeout=15000)
    page.wait_for_timeout(400)

    search = page.locator(
        'input[placeholder*="Qué trabajo buscas" i], '
        'input[placeholder*="trabajo buscas" i], '
        'input[type="search"]'
    ).first
    if search.count() == 0:
        raise RuntimeError("Trabajando.com cambió el campo principal de búsqueda")

    search.fill(termino)
    submitted = False
    try:
        search.press("Enter", timeout=2000)
        submitted = True
    except Exception:
        pass

    try:
        page.wait_for_selector('a[href*="/trabajo/"]', timeout=6000)
    except Exception:
        # Algunas versiones del frontend no envían con Enter.
        buttons = page.locator('button:has-text("Buscar empleo"), button:has-text("Buscar")')
        for i in range(min(buttons.count(), 8)):
            try:
                if buttons.nth(i).is_visible():
                    buttons.nth(i).click(timeout=2500)
                    submitted = True
                    break
            except Exception:
                continue
        try:
            page.wait_for_selector('a[href*="/trabajo/"]', timeout=6500)
        except Exception:
            pass

    body = page.locator("body").inner_text(timeout=3000) if page.locator("body").count() else ""
    if _blocked(body):
        _LAST_DIAGNOSTIC["blocked"] = True

    links, seen = [], set()
    anchors = page.locator('a[href*="/trabajo/"]')
    for idx in range(min(anchors.count(), 300)):
        a = anchors.nth(idx)
        href = (a.get_attribute("href") or "").strip()
        link = urljoin(BASE_URL, href).split("?")[0].split("#")[0]
        path = urlsplit(link).path
        if not re.match(r"^/trabajo/\d+(?:-[^/?#]+)?/?$", path, re.I):
            continue
        if link in seen:
            continue
        seen.add(link)
        try:
            hint = a.inner_text(timeout=800).strip()
        except Exception:
            hint = ""
        links.append((link, hint))

    # Si el formulario carga resultados vía navegación SPA, a veces los anchors
    # aparecen después de un breve tick aunque wait_for_selector haya expirado.
    if not links and submitted:
        page.wait_for_timeout(1800)
        anchors = page.locator('a[href*="/trabajo/"]')
        for idx in range(min(anchors.count(), 300)):
            a = anchors.nth(idx)
            href = (a.get_attribute("href") or "").strip()
            link = urljoin(BASE_URL, href).split("?")[0].split("#")[0]
            path = urlsplit(link).path
            if re.match(r"^/trabajo/\d+(?:-[^/?#]+)?/?$", path, re.I) and link not in seen:
                seen.add(link)
                try:
                    hint = a.inner_text(timeout=800).strip()
                except Exception:
                    hint = ""
                links.append((link, hint))
    return links

def _empresa_fallback(doc) -> str:
    text = doc.get_text("\n", strip=True)
    m = re.search(r"Publicada\s+(?:hace\s+[^\n]+\s+)?por\s*\n?([^\n]{2,100})", text, re.I)
    return m.group(1).strip() if m else ""


def _extraer(page, link: str):
    page.goto(link, wait_until="domcontentloaded", timeout=15000)
    try:
        page.wait_for_selector("h1", timeout=5000)
    except Exception:
        pass
    html = page.content()
    doc = BeautifulSoup(html, "html.parser")
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


def buscar_ofertas(browser, terminos=None, modo="rapida", progreso=None):
    global _LAST_DIAGNOSTIC
    _LAST_DIAGNOSTIC = {
        "links_found": 0, "offers_extracted": 0, "detail_errors": 0,
        "query_errors": 0, "blocked": False, "transport": "playwright",
    }
    page = nueva_pagina(browser)
    limite_terminos = MAX_TERMINOS_RAPIDA if modo == "rapida" else 6
    terms = list(dict.fromkeys(t for t in (terminos or []) if t))[:limite_terminos]
    items, seen = [], set()

    for idx, termino in enumerate(terms, 1):
        if progreso:
            progreso(f"Trabajando.com · {idx}/{len(terms)} · {termino}")
        try:
            for link, hint in _links_busqueda(page, termino):
                if link not in seen:
                    seen.add(link)
                    items.append((link, hint))
        except Exception as exc:
            _LAST_DIAGNOSTIC["query_errors"] += 1
            if progreso:
                progreso(f"Trabajando.com · consulta omitida: {type(exc).__name__}")

    _LAST_DIAGNOSTIC["links_found"] = len(items)
    items.sort(key=lambda x: 0 if titulo_parece_relevante(x[1], terms) else 1)

    ofertas = []
    limite = MAX_DETALLES_RAPIDA if modo == "rapida" else 20
    for idx, (link, _hint) in enumerate(items[:limite], 1):
        if progreso:
            progreso(f"Trabajando.com · leyendo {idx}/{min(len(items), limite)}")
        try:
            ofertas.append(_extraer(page, link))
            _LAST_DIAGNOSTIC["offers_extracted"] += 1
        except Exception:
            _LAST_DIAGNOSTIC["detail_errors"] += 1

    page.close()
    return ofertas
