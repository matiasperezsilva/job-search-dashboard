"""Adaptador de búsqueda para linkedin."""

from urllib.parse import quote_plus
from .common import nueva_pagina

NOMBRE = "LinkedIn"
BASE_URL = "https://www.linkedin.com/jobs/search"
TERMINOS_BUSQUEDA = [
    "QA", "tester", "quality assurance",
    "DBA", "administrador de base de datos", "database administrator",
    "soporte cloud", "cloud support",
    "analista funcional", "business analyst",
    "soporte TI",
]
MAX_OFERTAS_POR_TERMINO = 20
PAUSA_MS = 3000


def _cerrar_modal_login(page):
    boton = page.locator('button[aria-label="Dismiss"], button.modal__dismiss')
    if boton.count() > 0:
        try:
            boton.first.click(timeout=2000)
        except Exception:
            pass


def _buscar_links_por_termino(page, termino):
    print(f"  [{NOMBRE}] Buscando '{termino}'")
    url = f"{BASE_URL}?keywords={quote_plus(termino)}&location=Chile"
    page.goto(url, wait_until="load", timeout=30000)
    page.wait_for_timeout(PAUSA_MS)

    if "linkedin.com/authwall" in page.url or "checkpoint" in page.url:
        print("    Bloqueado (authwall/checkpoint), se omite este término")
        return set()

    links = page.locator('a.base-card__full-link, a[href*="/jobs/view/"]').evaluate_all(
        "els => [...new Set(els.map(e => e.href.split('?')[0]))]"
    )
    links = links[:MAX_OFERTAS_POR_TERMINO]
    print(f"    {len(links)} ofertas a procesar (de las encontradas en la página)")
    return set(links)


def _extraer_oferta(page, link):
    page.goto(link, wait_until="load", timeout=30000)
    page.wait_for_timeout(PAUSA_MS)
    _cerrar_modal_login(page)

    if "linkedin.com/authwall" in page.url or "checkpoint" in page.url:
        raise RuntimeError("bloqueado por authwall/checkpoint")

    titulo = page.locator(".top-card-layout__title").first.inner_text().strip()

    empresa_loc = page.locator(".topcard__org-name-link")
    empresa = empresa_loc.first.inner_text().strip() if empresa_loc.count() > 0 else ""

    modalidad_loc = page.locator(".topcard__flavor--bullet")
    modalidad = modalidad_loc.first.inner_text().strip() if modalidad_loc.count() > 0 else ""

    desc_loc = page.locator(".description__text")
    descripcion = desc_loc.first.inner_text().strip() if desc_loc.count() > 0 else ""

    return {
        "titulo": titulo,
        "empresa": empresa,
        "descripcion": descripcion,
        "modalidad": modalidad,
        "link": link,
        "fuente": NOMBRE,
    }


def buscar_ofertas(browser, terminos=None):
    page = nueva_pagina(browser)

    todos_los_links = set()
    for termino in (terminos or TERMINOS_BUSQUEDA):
        try:
            todos_los_links.update(_buscar_links_por_termino(page, termino))
        except Exception as e:
            print(f"    ERROR buscando '{termino}': {e}")
        page.wait_for_timeout(PAUSA_MS)

    ofertas = []
    for link in sorted(todos_los_links):
        try:
            oferta = _extraer_oferta(page, link)
        except Exception as e:
            print(f"    ERROR al procesar {link}: {e}")
            continue
        ofertas.append(oferta)
        page.wait_for_timeout(PAUSA_MS)

    page.close()
    return ofertas
