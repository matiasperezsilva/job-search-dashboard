"""Adaptador de búsqueda para laborum."""

from .common import nueva_pagina

NOMBRE = "Laborum"
_LAST_DIAGNOSTIC = {}


def get_last_diagnostic():
    return dict(_LAST_DIAGNOSTIC)

BASE_URL = "https://www.laborum.cl"
# El término se inserta directo en la URL (/empleos-busqueda-{termino}.html),
# así que los términos de varias palabras van con guion, no espacio.
TERMINOS_BUSQUEDA = [
    "qa", "tester", "quality-assurance",
    "dba", "administrador-de-base-de-datos",
    "soporte-cloud",
    "analista-funcional",
    "soporte-ti",
]
MAX_PAGINAS_POR_TERMINO = 1
PAUSA_MS = 200


def _buscar_links_por_termino(page, termino):
    print(f"  [{NOMBRE}] Buscando '{termino}'")
    links = set()
    for num_pagina in range(1, MAX_PAGINAS_POR_TERMINO + 1):
        sufijo = "" if num_pagina == 1 else f"?page={num_pagina}"
        slug = termino.strip().lower().replace(" ", "-")
        url = f"{BASE_URL}/empleos-busqueda-{slug}.html{sufijo}"
        page.goto(url, wait_until="domcontentloaded", timeout=8000)
        page.wait_for_timeout(700)

        nuevos = page.locator('a[href*="/empleos/"]').evaluate_all("els => els.map(e => e.href)")
        if not nuevos:
            break
        antes = len(links)
        links.update(nuevos)
        if len(links) == antes:
            break

    print(f"    {len(links)} ofertas encontradas")
    return links


def _extraer_oferta(page, link):
    page.goto(link, wait_until="domcontentloaded", timeout=8000)
    page.wait_for_timeout(250)

    titulo = page.locator("h1[aria-label]").first.inner_text().strip()

    empresa_loc = page.locator('[aria-label*="Ir a la empresa" i]')
    empresa_aria = empresa_loc.first.get_attribute("aria-label") if empresa_loc.count() > 0 else ""
    empresa = empresa_aria.replace("Ir a la empresa", "").strip() if empresa_aria else ""

    modalidad_loc = page.locator('[aria-label="Modalidad"]').locator("xpath=..")

    desc_heading = page.get_by_text("Descripción del puesto")
    descripcion = desc_heading.first.locator("xpath=../..").inner_text().strip() if desc_heading.count() > 0 else ""

    return {
        "titulo": titulo,
        "empresa": empresa,
        "descripcion": descripcion,
        "modalidad": modalidad_loc.first.inner_text().strip() if modalidad_loc.count() > 0 else "",
        "link": link,
        "fuente": NOMBRE,
    }


def buscar_ofertas(browser, terminos=None, modo="rapida", progreso=None):
    global _LAST_DIAGNOSTIC
    _LAST_DIAGNOSTIC = {"links_found": 0, "offers_extracted": 0, "detail_errors": 0, "query_errors": 0, "blocked": False}
    page = nueva_pagina(browser)

    todos_los_links = set()
    limite_terminos = 4 if modo == "rapida" else 6
    for idx, termino in enumerate(list(terminos or TERMINOS_BUSQUEDA)[:limite_terminos], 1):
        if progreso: progreso(f"Laborum · búsqueda {idx}/{limite_terminos} · {termino}")
        try:
            todos_los_links.update(_buscar_links_por_termino(page, termino))
            body = page.locator("body").inner_text().lower() if page.locator("body").count() else ""
            if any(x in body for x in ("captcha", "access denied", "verifica que eres humano", "verify you are human", "cloudflare")):
                _LAST_DIAGNOSTIC["blocked"] = True
        except Exception as e:
            _LAST_DIAGNOSTIC["query_errors"] += 1
            print(f"    ERROR buscando '{termino}': {e}")
        page.wait_for_timeout(PAUSA_MS)

    _LAST_DIAGNOSTIC["links_found"] = len(todos_los_links)
    ofertas = []
    limite_detalles = 5 if modo == "rapida" else 12
    for idx, link in enumerate(sorted(todos_los_links)[:limite_detalles], 1):
        if progreso: progreso(f"Laborum · validando {idx}/{min(len(todos_los_links), limite_detalles)}")
        try:
            oferta = _extraer_oferta(page, link)
        except Exception as e:
            _LAST_DIAGNOSTIC["detail_errors"] += 1
            print(f"    ERROR al procesar {link}: {e}")
            continue
        ofertas.append(oferta)
        _LAST_DIAGNOSTIC["offers_extracted"] += 1
        page.wait_for_timeout(PAUSA_MS)

    page.close()
    return ofertas
