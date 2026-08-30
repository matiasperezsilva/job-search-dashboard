"""Adaptador de búsqueda para computrabajo."""

from .common import click_si_existe, normalizar_link, nueva_pagina

NOMBRE = "Computrabajo"
BASE_URL = "https://cl.computrabajo.com"
TERMINOS_BUSQUEDA = [
    "QA", "tester", "analista de pruebas",
    "DBA", "administrador de base de datos",
    "soporte cloud",
    "analista funcional",
    "soporte TI",
]
MAX_PAGINAS_POR_TERMINO = 3
PAUSA_MS = 2000


def _buscar_links_por_termino(page, termino):
    print(f"  [{NOMBRE}] Buscando '{termino}'")
    page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(PAUSA_MS)
    click_si_existe(page, "#didomi-notice-agree-button")

    page.fill("#prof-cat-search-input", termino)
    page.wait_for_timeout(500)
    page.press("#prof-cat-search-input", "Enter")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(PAUSA_MS)

    if "403 Forbidden" in page.title():
        print(f"    Bloqueado (403) buscando '{termino}', se omite este término")
        return []

    links = set()
    for num_pagina in range(1, MAX_PAGINAS_POR_TERMINO + 1):
        nuevos = page.locator("article.box_offer a.js-o-link").evaluate_all(
            "els => els.map(e => e.href)"
        )
        links.update(normalizar_link(link) for link in nuevos)

        siguiente = page.locator('span[title="Siguiente"]')
        if num_pagina >= MAX_PAGINAS_POR_TERMINO or siguiente.count() == 0:
            break
        try:
            siguiente.first.click(timeout=3000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(PAUSA_MS)
        except Exception:
            break

    print(f"    {len(links)} ofertas encontradas")
    return links


def _extraer_oferta(page, link):
    page.goto(link, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(1500)

    titulo = page.locator("h1.box_detail").first.inner_text().strip()
    empresa_y_lugar = page.locator("h1.box_detail + p.fs16")
    empresa_y_lugar = empresa_y_lugar.first.inner_text().strip() if empresa_y_lugar.count() > 0 else ""
    partes = [p.strip() for p in empresa_y_lugar.split(" - ")]
    empresa = partes[0] if partes else ""
    modalidad = " - ".join(partes[1:]) if len(partes) > 1 else ""

    descripcion_loc = page.locator('div[div-link="oferta"]')
    descripcion = descripcion_loc.first.inner_text().strip() if descripcion_loc.count() > 0 else ""

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
