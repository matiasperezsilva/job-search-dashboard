"""Adaptador de búsqueda para getonbrd."""

from .common import click_si_existe, normalizar_link, nueva_pagina, texto_o_vacio

NOMBRE = "GetOnBoard"
BASE_URL = "https://www.getonbrd.com"
TERMINOS_BUSQUEDA = [
    "QA", "tester", "quality assurance",
    "DBA", "administrador de base de datos", "database administrator",
    "soporte cloud", "cloud support",
    "analista funcional", "business analyst",
    "soporte TI",
]


def _cargar_todos_los_resultados(page):
    cantidad_anterior = -1
    for _ in range(20):
        cantidad_actual = page.locator("a.results-item").count()
        if cantidad_actual == cantidad_anterior:
            break
        cantidad_anterior = cantidad_actual
        page.mouse.wheel(0, 5000)
        page.wait_for_timeout(800)
    return page.locator("a.results-item").count()


def _buscar_links_por_termino(page, termino):
    print(f"  [{NOMBRE}] Buscando '{termino}'")

    # Vamos siempre a la página base y usamos el buscador real (llenar +
    # Enter), en vez de armar la URL a mano: la URL "directa" a
    # /empleos-{termino} no dispara la misma búsqueda que hace el
    # JavaScript del sitio y devuelve muchos menos resultados.
    page.goto(f"{BASE_URL}/empleos", wait_until="networkidle")
    click_si_existe(page, "#accept_cookies")
    page.fill("#search_term", termino)
    page.press("#search_term", "Enter")
    page.wait_for_load_state("networkidle")
    _cargar_todos_los_resultados(page)

    links = page.locator("a.results-item").evaluate_all("els => els.map(e => e.href)")
    links = [normalizar_link(link) for link in links]
    print(f"    {len(links)} ofertas encontradas")
    return links


def _extraer_oferta(page, link):
    page.goto(link, wait_until="networkidle")
    click_si_existe(page, "#accept_cookies")

    titulo = page.locator('[itemprop="title"]').first.inner_text().strip()
    empresa = texto_o_vacio(page.locator('[itemprop="hiringOrganization"] [itemprop="name"]'))
    modalidad = texto_o_vacio(page.locator('[itemprop="jobLocation"] .location')).replace("\n", " ")
    descripcion = page.locator("#job-body").inner_text().strip()

    return {
        "titulo": titulo,
        "empresa": empresa,
        "descripcion": descripcion,
        "modalidad": modalidad,
        "link": link,
        "fuente": NOMBRE,
    }


def buscar_ofertas(browser, terminos=None):
    """Busca en todos los TERMINOS_BUSQUEDA, deduplica links y extrae cada oferta."""
    page = nueva_pagina(browser)
    todos_los_links = set()
    for termino in (terminos or TERMINOS_BUSQUEDA):
        todos_los_links.update(_buscar_links_por_termino(page, termino))

    ofertas = []
    for link in sorted(todos_los_links):
        try:
            ofertas.append(_extraer_oferta(page, link))
        except Exception as e:
            print(f"    ERROR al procesar {link}: {e}")
    page.close()
    return ofertas
