"""Adaptador rápido para Get on Board.

En producción priorizamos las páginas públicas por categoría en vez del buscador
JS. Esto reduce navegación, evita esperas por `networkidle` y funciona mejor en
instancias pequeñas como Render Free.
"""

from .common import ir_rapido, normalizar_link, nueva_pagina, texto_o_vacio, titulo_parece_relevante

NOMBRE = "GetOnBoard"
BASE_URL = "https://www.getonbrd.com"
CATEGORIAS = [
    "/jobs/sysadmin-devops-qa",
    "/jobs/data-science-analytics",
    "/jobs/innovation-agile",
    "/jobs/customer-support",
]
MAX_CANDIDATOS = 24
MAX_DETALLES = 16


def _links_categoria(page, path, terminos):
    ir_rapido(page, BASE_URL + path)
    enlaces = page.locator('a[href*="/jobs/"]')
    datos = enlaces.evaluate_all(
        "els => els.map(e => ({href:e.href, text:(e.innerText||'').trim()}))"
    )
    salida = []
    for item in datos:
        href = normalizar_link(item.get("href", ""))
        texto = (item.get("text") or "").split("\n", 1)[0].strip()
        if not href or href.rstrip("/").endswith(path.strip("/")):
            continue
        if href.count("/jobs/") != 1:
            continue
        # Preferimos títulos afines; si el texto no viene bien formado lo dejamos
        # como candidato para no perder resultados.
        if not texto or titulo_parece_relevante(texto, terminos):
            salida.append(href)
        if len(salida) >= MAX_CANDIDATOS:
            break
    return salida


def _extraer_oferta(page, link):
    ir_rapido(page, link)
    titulo = texto_o_vacio(page.locator('[itemprop="title"]')) or texto_o_vacio(page.locator("h1"))
    empresa = texto_o_vacio(page.locator('[itemprop="hiringOrganization"] [itemprop="name"]'))
    if not empresa:
        empresa = texto_o_vacio(page.locator('[itemprop="hiringOrganization"]'))
    modalidad = texto_o_vacio(page.locator('[itemprop="jobLocation"]')).replace("\n", " ")
    descripcion = texto_o_vacio(page.locator("#job-body"))
    if not descripcion:
        descripcion = texto_o_vacio(page.locator('[itemprop="description"]'))
    if not titulo:
        raise ValueError("No se pudo identificar el título de la oferta")
    return {
        "titulo": titulo,
        "empresa": empresa,
        "descripcion": descripcion,
        "modalidad": modalidad,
        "link": link,
        "fuente": NOMBRE,
    }


def buscar_ofertas(browser, terminos=None, modo="rapida", progreso=None):
    page = nueva_pagina(browser)
    terminos = (terminos or [])[:6 if modo == "rapida" else 12]
    links = []
    vistos = set()
    categorias = CATEGORIAS[:2] if modo == "rapida" else CATEGORIAS
    try:
        for i, cat in enumerate(categorias, 1):
            if progreso:
                progreso(f"GetOnBoard · categoría {i}/{len(categorias)}")
            try:
                for link in _links_categoria(page, cat, terminos):
                    if link not in vistos:
                        vistos.add(link); links.append(link)
                    if len(links) >= MAX_CANDIDATOS:
                        break
            except Exception:
                continue
            if len(links) >= MAX_CANDIDATOS:
                break

        ofertas = []
        limite = min(len(links), MAX_DETALLES if modo == "rapida" else MAX_CANDIDATOS)
        for idx, link in enumerate(links[:limite], 1):
            if progreso:
                progreso(f"GetOnBoard · leyendo {idx}/{limite}")
            try:
                oferta = _extraer_oferta(page, link)
                if titulo_parece_relevante(oferta["titulo"], terminos):
                    ofertas.append(oferta)
            except Exception:
                continue
        return ofertas
    finally:
        page.close()
