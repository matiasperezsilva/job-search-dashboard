"""Adaptador de búsqueda para bne."""

from .common import nueva_pagina

NOMBRE = "BNE"
BASE_URL = "https://www.bne.cl"
TERMINOS_BUSQUEDA = [
    "QA", "tester", "analista de pruebas", "quality assurance",
    "DBA", "administrador de base de datos",
    "soporte cloud",
    "analista funcional",
    "soporte TI", "mesa de ayuda",
]
MAX_PAGINAS_POR_TERMINO = 1
PAUSA_MS = 200


def _buscar_links_por_termino(page, termino):
    print(f"  [{NOMBRE}] Buscando '{termino}'")
    page.goto(f"{BASE_URL}/ofertas?mostrar=empleo", wait_until="domcontentloaded", timeout=12000)
    page.wait_for_timeout(250)
    page.fill('input[placeholder*="palabra clave"]', termino)
    page.click('button:has-text("BUSCAR")')
    page.wait_for_timeout(300)

    links = set()
    for _ in range(MAX_PAGINAS_POR_TERMINO):
        nuevos = page.locator('a[href^="/oferta/"]').evaluate_all(
            "els => els.map(e => e.href)"
        )
        if not nuevos:
            break
        antes = len(links)
        links.update(nuevos)
        if len(links) == antes:
            break

        siguiente = page.locator('a[aria-label="Siguiente"], a:has-text("›")')
        if siguiente.count() == 0:
            break
        try:
            siguiente.first.click(timeout=3000)
            page.wait_for_timeout(250)
        except Exception:
            break

    print(f"    {len(links)} ofertas encontradas")
    return links


def _extraer_oferta(page, link):
    page.goto(link, wait_until="domcontentloaded", timeout=12000)
    page.wait_for_timeout(200)

    titulo = page.locator("#nombreOferta > span").first.inner_text().strip()

    categoria_loc = page.locator("#nombreOferta small")
    categoria = categoria_loc.first.inner_text().strip() if categoria_loc.count() > 0 else ""

    empresa_bloque = page.get_by_text("Empresa:")
    empresa = ""
    if empresa_bloque.count() > 0:
        texto = empresa_bloque.first.locator("xpath=../..").inner_text()
        empresa = texto.replace("Empresa:", "").strip()

    desc_heading = page.locator('h3:has-text("DESCRIPCIÓN")')
    descripcion = ""
    if desc_heading.count() > 0:
        panel = desc_heading.first.locator("xpath=ancestor::article[1]")
        parrafos = panel.locator("p").all_inner_texts()
        descripcion = "\n".join(p.strip() for p in parrafos if p.strip())

    return {
        "titulo": titulo,
        "empresa": empresa,
        "descripcion": descripcion,
        "modalidad": categoria,
        "link": link,
        "fuente": NOMBRE,
    }


def buscar_ofertas(browser, terminos=None):
    page = nueva_pagina(browser)

    todos_los_links = set()
    for termino in list(terminos or TERMINOS_BUSQUEDA)[:6]:
        try:
            todos_los_links.update(_buscar_links_por_termino(page, termino))
        except Exception as e:
            print(f"    ERROR buscando '{termino}': {e}")
        page.wait_for_timeout(PAUSA_MS)

    ofertas = []
    for link in sorted(todos_los_links)[:15]:
        try:
            oferta = _extraer_oferta(page, link)
        except Exception as e:
            print(f"    ERROR al procesar {link}: {e}")
            continue
        ofertas.append(oferta)
        page.wait_for_timeout(PAUSA_MS)

    page.close()
    return ofertas
