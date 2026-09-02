"""BNE: búsqueda pública con Playwright y fallback al listado.

La BNE mantiene /ofertas?mostrar=empleo y fichas /oferta/<id>. El formulario
ha cambiado de estructura varias veces, por eso no dependemos de un único selector:
detectamos el campo visible, probamos Enter/botón y aceptamos ofertas internas y externas.
"""

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .common import nueva_pagina, titulo_parece_relevante

USES_BROWSER = True
NOMBRE = "BNE"
BASE_URL = "https://www.bne.cl"
SEARCH_URL = f"{BASE_URL}/ofertas?mostrar=empleo"
_LAST_DIAGNOSTIC = {}


def get_last_diagnostic():
    return dict(_LAST_DIAGNOSTIC)


def _blocked(text: str) -> bool:
    low = (text or "").lower()
    return any(x in low for x in (
        "captcha", "access denied", "verify you are human",
        "verifica que eres humano", "cloudflare",
    ))


def _offer_links(page):
    anchors = page.locator('a[href*="/oferta/"], a[href*="/ofertaEmpleoExterno/"]')
    out, seen = [], set()
    for i in range(min(anchors.count(), 500)):
        a = anchors.nth(i)
        try:
            href = a.get_attribute("href") or ""
            text = a.inner_text(timeout=700).strip()
        except Exception:
            continue
        link = urljoin(BASE_URL, href).split("?")[0].split("#")[0]
        if not re.search(r"/(?:oferta|ofertaEmpleoExterno)/[^/?#]+", link):
            continue
        if link in seen:
            continue
        seen.add(link)
        out.append((link, text))
    return out

def _visible_search_input(page):
    selectors = [
        'input[placeholder*="profesi" i]',
        'input[placeholder*="empresa" i]',
        'input[placeholder*="palabra" i]',
        'input[type="search"]',
        'input[type="text"]',
    ]
    for selector in selectors:
        loc = page.locator(selector)
        for i in range(min(loc.count(), 20)):
            candidate = loc.nth(i)
            try:
                if candidate.is_visible():
                    placeholder = (candidate.get_attribute("placeholder") or "").lower()
                    # Evitar inputs de filtros región/ocupación si hay uno más específico.
                    if any(x in placeholder for x in ("región", "region", "ocupación", "ocupacion")):
                        continue
                    return candidate
            except Exception:
                continue
    return None


def _buscar_links_por_termino(page, termino):
    page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=15000)
    page.wait_for_timeout(500)
    body = page.locator("body").inner_text(timeout=3000) if page.locator("body").count() else ""
    if _blocked(body):
        _LAST_DIAGNOSTIC["blocked"] = True
        return []

    campo = _visible_search_input(page)
    if campo is None:
        raise RuntimeError("BNE cambió el campo principal de búsqueda")

    campo.fill(termino)
    submitted = False
    try:
        campo.press("Enter", timeout=2000)
        submitted = True
    except Exception:
        pass

    try:
        page.wait_for_selector('a[href*="/oferta/"], a[href*="/ofertaEmpleoExterno/"]', timeout=4500)
    except Exception:
        if submitted:
            # Enter puede no enviar el formulario. Intentamos el botón visible.
            pass

    links = _offer_links(page)
    if not links:
        buttons = page.locator('button:has-text("BUSCAR"), button:has-text("Buscar"), input[type="submit"]')
        for i in range(min(buttons.count(), 10)):
            try:
                if buttons.nth(i).is_visible():
                    buttons.nth(i).click(timeout=2500)
                    break
            except Exception:
                continue
        try:
            page.wait_for_selector('a[href*="/oferta/"], a[href*="/ofertaEmpleoExterno/"]', timeout=6000)
        except Exception:
            pass
        links = _offer_links(page)

    return links


def _text_after_label(doc, label: str):
    text = doc.get_text("\n", strip=True)
    m = re.search(rf"{re.escape(label)}\s*:?\s*\n?\s*([^\n]{{1,160}})", text, re.I)
    return m.group(1).strip() if m else ""


def _extraer_oferta(page, link):
    page.goto(link, wait_until="domcontentloaded", timeout=15000)
    try:
        page.wait_for_selector("#nombreOferta, h1", timeout=5000)
    except Exception:
        pass

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
            page.wait_for_timeout(700)
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

    page.close()
    return offers
