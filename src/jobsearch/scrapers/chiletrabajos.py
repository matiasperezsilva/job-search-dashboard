"""Adaptador de búsqueda para chiletrabajos."""

from .common import nueva_pagina

NOMBRE = "ChileTrabajos"
BASE_URL = "https://www.chiletrabajos.cl"
TERMINOS_BUSQUEDA = [
    "QA", "tester", "quality assurance",
    "DBA", "administrador de base de datos",
    "soporte cloud",
    "analista funcional",
    "soporte TI",
]
MAX_PAGINAS_POR_TERMINO = 3
PAUSA_MS = 1000


def _buscar_links_por_termino(page, termino):
    print(f"  [{NOMBRE}] Buscando '{termino}'")
    page.goto(BASE_URL, wait_until="load", timeout=30000)
    page.fill('input[placeholder="Trabajo ej: Analista"]', termino)
    page.click("#frm-landingPage1-submit")
    page.wait_for_load_state("load")
    page.wait_for_timeout(PAUSA_MS)

    links = set()
    for num_pagina in range(1, MAX_PAGINAS_POR_TERMINO + 1):
        nuevos = page.locator("h2.title a").evaluate_all("els => els.map(e => e.href)")
        links.update(nuevos)

        siguiente = page.locator('a[data-ci-pagination-page][rel="next"]')
        if num_pagina >= MAX_PAGINAS_POR_TERMINO or siguiente.count() == 0:
            break
        try:
            siguiente.first.click(timeout=3000)
            page.wait_for_load_state("load")
            page.wait_for_timeout(PAUSA_MS)
        except Exception:
            break

    print(f"    {len(links)} ofertas encontradas")
    return links


def _extraer_oferta(page, link):
    page.goto(link, wait_until="load", timeout=30000)
    page.wait_for_timeout(800)

    titulo = page.locator("h1.titulo-detalle").first.inner_text().strip()

    empresa_loc = page.locator('td:has-text("Buscado") + td a')
    empresa = empresa_loc.first.inner_text().strip() if empresa_loc.count() > 0 else ""

    ubicacion_loc = page.locator('td a[href*="/ciudad/"]')
    modalidad = ubicacion_loc.first.inner_text().strip() if ubicacion_loc.count() > 0 else ""

    descripcion_loc = page.locator("div.p-x-3.overflow-hidden")
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
