"""Búsqueda y fichas públicas de la Bolsa Nacional de Empleo."""

import re
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from .common import nueva_pagina, titulo_parece_relevante

USES_BROWSER = True
NOMBRE = "BNE"
BASE_URL = "https://bne.gob.cl"
SEARCH_URL = f"{BASE_URL}/buscar-empleo"
OFFER_SELECTOR = 'a[href*="/ofertas/"], a[href*="/oferta/"], a[href*="/ofertaEmpleoExterno/"]'
_LAST_DIAGNOSTIC = {}


def get_last_diagnostic():
    return dict(_LAST_DIAGNOSTIC)


def _blocked(text: str) -> bool:
    low = (text or "").lower()
    return any(x in low for x in (
        "captcha", "access denied", "verify you are human",
        "verifica que eres humano", "cloudflare",
    ))


def _offer_url(href: str) -> str:
    link = urljoin(BASE_URL, href).split("?", 1)[0].split("#", 1)[0]
    target = urlsplit(link)
    if target.scheme != "https" or target.netloc not in {"bne.gob.cl", "www.bne.gob.cl", "www.bne.cl"}:
        return ""
    return link if re.fullmatch(r"(?:/ofertas/\d+|/(?:oferta|ofertaEmpleoExterno)/[\w-]+)/?", target.path) else ""


def _offer_links(page):
    anchors = page.get_by_role("region", name="Resultados de búsqueda").locator(OFFER_SELECTOR)
    out, seen = [], set()
    for index in range(min(anchors.count(), 30)):
        anchor = anchors.nth(index)
        try:
            link = _offer_url(anchor.get_attribute("href") or "")
            title = anchor.inner_text(timeout=700).strip()
        except Exception:
            continue
        if link and link not in seen:
            seen.add(link)
            out.append((link, title))
    return out


def _buscar_links_por_termino(page, termino):
    response = page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=15000)
    if response and response.status in {403, 429}:
        _LAST_DIAGNOSTIC["blocked"] = True
        return []
    if _blocked(page.locator("body").inner_text(timeout=3000)):
        _LAST_DIAGNOSTIC["blocked"] = True
        return []
    page.locator("#profesion").fill(termino, timeout=6000)
    page.get_by_role("button", name="Buscar", exact=True).click(timeout=6000)
    results = page.get_by_role("region", name="Resultados de búsqueda")
    results.get_by_role("status", name=re.compile("cargando", re.I)).wait_for(state="hidden", timeout=10000)
    if _blocked(results.inner_text(timeout=3000)):
        _LAST_DIAGNOSTIC["blocked"] = True
        return []
    return _offer_links(page)


def _text_after_label(doc, label: str):
    text = doc.get_text("\n", strip=True)
    m = re.search(rf"{re.escape(label)}\s*:?\s*\n?\s*([^\n]{{1,160}})", text, re.I)
    return m.group(1).strip() if m else ""


def _extraer_oferta(page, link):
    response = page.goto(link, wait_until="domcontentloaded", timeout=15000)
    if response and response.status in {403, 429}:
        _LAST_DIAGNOSTIC["blocked"] = True
        raise ValueError("BNE restringió el acceso a la ficha")
    if urlsplit(link).path.startswith("/ofertas/"):
        page.get_by_role("region", name="Descripción de la oferta").wait_for(timeout=7000)
    else:
        page.wait_for_selector("#nombreOferta, h1", timeout=5000)

    html = page.content()
    doc = BeautifulSoup(html, "html.parser")

    title_el = doc.select_one("#nombreOferta > span") or doc.select_one("#nombreOferta") or doc.find("h1")
    titulo = title_el.get_text(" ", strip=True) if title_el else ""
    if not titulo:
        raise ValueError("BNE no entregó título para la vacante")

    empresa = _text_after_label(doc, "Empresa")
    descripcion = ""
    # Ficha interna: bloque DESCRIPCIÓN.
    heading = doc.find(lambda tag: tag.name in {"h2","h3","h4"} and "DESCRIP" in tag.get_text(" ", strip=True).upper())
    if heading:
        container = heading.find_parent(["article","section","div"])
        if container:
            descripcion = container.get_text(" ", strip=True)
    if not descripcion:
        # Las ofertas externas usan una estructura distinta; conservar cuerpo útil.
        descripcion = doc.get_text(" ", strip=True)

    modalidad_bits = []
    for label in ("Tipo de contrato", "Jornada", "Nivel de Cargo ofrecido", "Ubicación"):
        value = _text_after_label(doc, label)
        if value:
            modalidad_bits.append(value)

    # BNE publica rango de vigencia. La primera fecha es una buena aproximación de publicación.
    body_text = doc.get_text(" ", strip=True)
    date_match = re.search(r"\b(\d{2})/(\d{2})/(\d{4})\b", body_text)
    published = ""
    if date_match:
        published = f"{date_match.group(3)}-{date_match.group(2)}-{date_match.group(1)}"

    return {
        "titulo": titulo,
        "empresa": empresa,
        "descripcion": descripcion,
        "modalidad": " · ".join(dict.fromkeys(modalidad_bits)),
        "link": link,
        "fuente": NOMBRE,
        "published_at": published,
    }


def buscar_ofertas(browser, terminos=None, modo="rapida", progreso=None):
    global _LAST_DIAGNOSTIC
    _LAST_DIAGNOSTIC = {
        "links_found": 0, "offers_extracted": 0, "detail_errors": 0,
        "query_errors": 0, "blocked": False, "transport": "playwright",
    }
    page = nueva_pagina(browser)
    terms = list(dict.fromkeys(t for t in (terminos or []) if t))[:3 if modo == "rapida" else 6]
    cards = []

    for idx, term in enumerate(terms, 1):
        if progreso:
            progreso(f"BNE · {idx}/{len(terms)} · {term}")
        try:
            cards.extend(_buscar_links_por_termino(page, term))
        except Exception:
            _LAST_DIAGNOSTIC["query_errors"] += 1
        if _LAST_DIAGNOSTIC["blocked"]:
            page.close()
            return []

    # Deduplica por URL conservando el texto más descriptivo del listado.
    by_link = {}
    for link, hint in cards:
        if link not in by_link or len(hint or "") > len(by_link[link] or ""):
            by_link[link] = hint or ""
    cards = list(by_link.items())

    # Si el formulario cambió pero el listado público sí carga, rescatar enlaces visibles.
    if not cards and not _LAST_DIAGNOSTIC["blocked"]:
        try:
            page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=15000)
            results = page.get_by_role("region", name="Resultados de búsqueda")
            results.get_by_role("status", name=re.compile("cargando", re.I)).wait_for(state="hidden", timeout=10000)
            cards = _offer_links(page)
            if cards:
                _LAST_DIAGNOSTIC["transport"] = "public-list-fallback"
        except Exception:
            _LAST_DIAGNOSTIC["query_errors"] += 1

    _LAST_DIAGNOSTIC["links_found"] = len(cards)

    # La ejecución anterior encontró 20 links pero gastó el presupuesto en 8 fichas
    # irrelevantes. Ahora priorizamos el texto visible del listado antes de abrir fichas.
    cards.sort(key=lambda item: 0 if titulo_parece_relevante(item[1], terms) else 1)
    relevant_cards = [c for c in cards if titulo_parece_relevante(c[1], terms)]
    fallback_cards = [c for c in cards if c not in relevant_cards]

    # En rápida: hasta 10 títulos relevantes; si hay pocos, completa con 4 fallback.
    selected = relevant_cards[:10 if modo == "rapida" else 20]
    if len(selected) < 4:
        selected += fallback_cards[:4-len(selected)]
    elif modo != "rapida":
        selected += fallback_cards[:max(0, 24-len(selected))]

    offers = []
    for idx, (link, hint) in enumerate(selected, 1):
        if progreso:
            progreso(f"BNE · leyendo {idx}/{len(selected)} · {hint[:45] or 'vacante'}")
        try:
            offers.append(_extraer_oferta(page, link))
            _LAST_DIAGNOSTIC["offers_extracted"] += 1
        except Exception:
            _LAST_DIAGNOSTIC["detail_errors"] += 1
            if _LAST_DIAGNOSTIC["blocked"]:
                break

    page.close()
    return offers
