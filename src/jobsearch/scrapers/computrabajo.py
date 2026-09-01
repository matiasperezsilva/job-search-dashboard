"""Adaptador optimizado para Computrabajo.

Computrabajo puede aplicar protección anti-bot. En ese caso fallamos rápido y
seguimos con otras fuentes en vez de bloquear toda la búsqueda.
"""

from .common import click_si_existe, ir_rapido, normalizar_link, nueva_pagina, texto_o_vacio

NOMBRE = "Computrabajo"
BASE_URL = "https://cl.computrabajo.com"
MAX_TERMINOS_RAPIDA = 4
MAX_PAGINAS_RAPIDA = 1
MAX_RESULTADOS_RAPIDA = 12


def _buscar_links_por_termino(page, termino, max_paginas=1):
    ir_rapido(page, BASE_URL, timeout=10000)
    click_si_existe(page, "#didomi-notice-agree-button")

    posibles = ["#prof-cat-search-input", 'input[name="q"]', 'input[type="search"]']
    buscador = None
    for selector in posibles:
        loc = page.locator(selector)
        if loc.count() > 0:
            buscador = loc.first
            break
    if buscador is None:
        raise RuntimeError("Computrabajo cambió su buscador o bloqueó la página")

    buscador.fill(termino, timeout=2500)
    buscador.press("Enter", timeout=2500)
    try:
        page.wait_for_load_state("domcontentloaded", timeout=7000)
    except Exception:
        pass

    contenido = (page.title() + " " + page.locator("body").inner_text(timeout=3000)).lower()
    if "403 forbidden" in contenido or "access denied" in contenido or "captcha" in contenido:
        raise RuntimeError("Computrabajo bloqueó la consulta automática en este servidor")

    links = set()
    for num in range(max_paginas):
        for selector in ["article.box_offer a.js-o-link", 'a[href*="/ofertas-de-trabajo/"]', 'a[href*="/trabajo-de-"]']:
            loc = page.locator(selector)
            if loc.count() > 0:
                try:
                    nuevos = loc.evaluate_all("els => els.map(e => e.href)")
                    links.update(normalizar_link(x) for x in nuevos if x)
                except Exception:
                    pass
        if num + 1 >= max_paginas:
            break
        siguiente = page.locator('span[title="Siguiente"], a[aria-label="Siguiente"]')
        if siguiente.count() == 0:
            break
        try:
            siguiente.first.click(timeout=2000)
            page.wait_for_load_state("domcontentloaded", timeout=6000)
        except Exception:
            break
    return list(links)


def _extraer_oferta(page, link):
    ir_rapido(page, link, timeout=9000)
    titulo = texto_o_vacio(page.locator("h1.box_detail")) or texto_o_vacio(page.locator("h1"))
    empresa_y_lugar = texto_o_vacio(page.locator("h1.box_detail + p.fs16"))
    partes = [p.strip() for p in empresa_y_lugar.split(" - ")]
    empresa = partes[0] if partes else ""
    modalidad = " - ".join(partes[1:]) if len(partes) > 1 else ""
    descripcion = texto_o_vacio(page.locator('div[div-link="oferta"]'))
    if not descripcion:
        descripcion = texto_o_vacio(page.locator("main"))
    if not titulo:
        raise ValueError("No se pudo identificar el título")
    return {"titulo": titulo, "empresa": empresa, "descripcion": descripcion, "modalidad": modalidad, "link": link, "fuente": NOMBRE}


def buscar_ofertas(browser, terminos=None, modo="rapida", progreso=None):
    page = nueva_pagina(browser)
    terminos = list(dict.fromkeys(terminos or []))
    terminos = terminos[:MAX_TERMINOS_RAPIDA if modo == "rapida" else 8]
    max_paginas = MAX_PAGINAS_RAPIDA if modo == "rapida" else 2
    max_resultados = MAX_RESULTADOS_RAPIDA if modo == "rapida" else 24
    links = []
    vistos = set()
    try:
        for idx, termino in enumerate(terminos, 1):
            if progreso:
                progreso(f"Computrabajo · término {idx}/{len(terminos)}: {termino}")
            try:
                encontrados = _buscar_links_por_termino(page, termino, max_paginas)
            except RuntimeError:
                raise
            except Exception:
                continue
            for link in encontrados:
                if link not in vistos:
                    vistos.add(link); links.append(link)
                if len(links) >= max_resultados:
                    break
            if len(links) >= max_resultados:
                break

        ofertas = []
        for idx, link in enumerate(links[:max_resultados], 1):
            if progreso:
                progreso(f"Computrabajo · leyendo {idx}/{min(len(links), max_resultados)}")
            try:
                ofertas.append(_extraer_oferta(page, link))
            except Exception:
                continue
        return ofertas
    finally:
        page.close()
