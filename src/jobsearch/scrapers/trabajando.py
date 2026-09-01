"""Adaptador de búsqueda para trabajando."""

from .common import nueva_pagina

NOMBRE = "Trabajando.com"
BASE_URL = "https://www.trabajando.cl"
TERMINOS_BUSQUEDA = [
    "QA", "tester", "analista de pruebas",
    "DBA", "administrador de base de datos",
    "soporte cloud",
    "analista funcional",
    "soporte TI",
]
MAX_PAGINAS_POR_TERMINO = 1
PAUSA_MS = 200


def _aceptar_cookies(page):
    boton = page.locator('button:has-text("Acepto")')
    if boton.count() > 0:
        try:
            boton.first.click(timeout=3000)
        except Exception:
            pass


def _buscar_links_por_termino(page, termino):
    print(f"  [{NOMBRE}] Buscando '{termino}'")
    page.goto(BASE_URL, wait_until="domcontentloaded", timeout=12000)
    _aceptar_cookies(page)

    # El input visible es el 2do de los que matchean el placeholder: el resto
    # son duplicados de tamaño cero que Playwright rechaza como "no visibles".
    campo = page.locator('input[placeholder*="trabajo buscas"]').nth(1)
    campo.click(timeout=5000)
    campo.type(termino)
    page.keyboard.press("Enter")
    page.wait_for_load_state("domcontentloaded", timeout=6000)
    page.wait_for_timeout(PAUSA_MS)

    links = set()
    for _ in range(MAX_PAGINAS_POR_TERMINO):
        nuevos = page.locator('a[href*="/trabajo-empleo/"][href*="/trabajo/"]').evaluate_all(
            "els => els.map(e => e.href)"
        )
        if not nuevos:
            break
        antes = len(links)
        links.update(nuevos)
        if len(links) == antes:
            break

        siguiente = page.get_by_text("Siguiente")
        if siguiente.count() == 0:
            break
        try:
            siguiente.first.click(timeout=3000)
            page.wait_for_load_state("domcontentloaded", timeout=6000)
            page.wait_for_timeout(PAUSA_MS)
        except Exception:
            break

    print(f"    {len(links)} ofertas encontradas")
    return links


def _extraer_oferta(page, link):
    page.goto(link, wait_until="domcontentloaded", timeout=12000)
    page.wait_for_timeout(250)

    titulo = page.locator("h3").first.inner_text().strip()

    empresa_loc = page.locator("a.tag-manager-lead-fichaempresa")
    empresa = empresa_loc.first.inner_text().strip() if empresa_loc.count() > 0 else ""

    perfil = page.locator('h4:has-text("Perfil deseado")')
    contenedor = perfil.first.locator('xpath=ancestor::div[contains(@class,"col")][1]') if perfil.count() > 0 else None

    modalidad = ""
    descripcion = ""
    if contenedor is not None:
        tags = contenedor.locator("ul.badges li").all_inner_texts()
        modalidad = " - ".join(t.strip() for t in tags if t.strip())
        parrafos = contenedor.locator("p").all_inner_texts()
        descripcion = "\n".join(p.strip() for p in parrafos if p.strip())

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
