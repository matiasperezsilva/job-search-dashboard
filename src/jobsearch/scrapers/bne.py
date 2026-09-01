"""Adaptador de búsqueda para bne."""

from .common import nueva_pagina

NOMBRE = "BNE"
_LAST_DIAGNOSTIC = {}


def get_last_diagnostic():
    return dict(_LAST_DIAGNOSTIC)

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
    page.goto(f"{BASE_URL}/ofertas?mostrar=empleo", wait_until="domcontentloaded", timeout=8000)
    page.wait_for_timeout(250)
    campo = page.locator('input[placeholder*="palabra" i], input[placeholder*="profesi" i]').first
    campo.fill(termino)
    page.locator('button:has-text("BUSCAR"), input[type="submit"]').first.click()
    try:
        page.wait_for_load_state("networkidle", timeout=5000)
    except Exception:
        pass
    page.wait_for_timeout(800)

    links = set()
    for _ in range(MAX_PAGINAS_POR_TERMINO):
        nuevos = page.locator('a[href*="/oferta/"]').evaluate_all(
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
    page.goto(link, wait_until="domcontentloaded", timeout=8000)
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


def buscar_ofertas(browser, terminos=None, modo="rapida", progreso=None):
    global _LAST_DIAGNOSTIC
    _LAST_DIAGNOSTIC = {"links_found": 0, "offers_extracted": 0, "detail_errors": 0, "query_errors": 0, "blocked": False}
    page = nueva_pagina(browser)

    todos_los_links = set()
    limite_terminos = 3 if modo == "rapida" else 6
    for idx, termino in enumerate(list(terminos or TERMINOS_BUSQUEDA)[:limite_terminos], 1):
        if progreso: progreso(f"BNE · búsqueda {idx}/{limite_terminos} · {termino}")
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
    limite_detalles = 4 if modo == "rapida" else 12
    for idx, link in enumerate(sorted(todos_los_links)[:limite_detalles], 1):
        if progreso: progreso(f"BNE · validando {idx}/{min(len(todos_los_links), limite_detalles)}")
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
