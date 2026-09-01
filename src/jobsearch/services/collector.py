import importlib
import time
from playwright.sync_api import sync_playwright
from jobsearch.scrapers.common import es_relevante_perfil, oferta_es_valida

FUENTES = {
    "GetOnBoard": "getonbrd",
    "Computrabajo": "computrabajo",
    "ChileTrabajos": "chiletrabajos",
    "Laborum": "laborum",
    "Trabajando.com": "trabajando",
    "BNE": "bne",
    "LinkedIn": "linkedin",
}


def recolectar(fuentes, terminos=None, headless=True, modo="rapida", progreso=None, on_source_result=None):
    """Recolecta secuencialmente y falla de forma aislada por fuente.

    GetOnBoard y Computrabajo usan HTTP directo; Chromium sólo se inicia si una
    fuente realmente lo necesita. En Render Free esto ahorra RAM y cold-start.
    """
    ofertas, errores, estadisticas = [], [], []
    limite_terminos = 4 if modo == "rapida" else 10
    terminos = list(dict.fromkeys(t.strip() for t in (terminos or []) if t and t.strip()))[:limite_terminos]

    playwright = None
    browser = None
    try:
        for pos, nombre in enumerate(fuentes, 1):
            if progreso:
                progreso({"tipo": "fuente", "fuente": nombre, "indice": pos, "total": len(fuentes), "mensaje": f"Consultando {nombre}…"})

            modulo = importlib.import_module(f"jobsearch.scrapers.{FUENTES[nombre]}")
            uses_browser = getattr(modulo, "USES_BROWSER", True)
            if uses_browser and browser is None:
                playwright = sync_playwright().start()
                browser = playwright.chromium.launch(headless=headless, args=["--disable-dev-shm-usage", "--no-sandbox"])

            inicio = time.monotonic()
            try:
                def sub(msg):
                    if progreso:
                        progreso({"tipo": "detalle", "fuente": nombre, "mensaje": msg})
                target_browser = browser if uses_browser else None
                try:
                    resultado = modulo.buscar_ofertas(target_browser, terminos=terminos or None, modo=modo, progreso=sub)
                except TypeError:
                    resultado = modulo.buscar_ofertas(target_browser, terminos=terminos or None)

                # Segunda barrera común: una fuente nunca puede guardar una página
                # SEO o un QA industrial aunque su adaptador se equivoque.
                resultado = [o for o in resultado if oferta_es_valida(o) and es_relevante_perfil(o.get("titulo", ""), o.get("descripcion", ""))]
                ofertas.extend(resultado)
                if on_source_result:
                    on_source_result(nombre, resultado)
                stat={"fuente": nombre, "cantidad": len(resultado), "segundos": round(time.monotonic()-inicio, 1), "ok": True, "estado": "ok" if resultado else "empty"}; estadisticas.append(stat)
                if progreso: progreso({"tipo":"resultado_fuente","fuente":nombre,"mensaje":f"{nombre}: {len(resultado)} vacantes relevantes","estadistica":stat})
            except Exception as exc:
                errores.append({"fuente": nombre, "error": str(exc)})
                stat={"fuente": nombre, "cantidad": 0, "segundos": round(time.monotonic()-inicio, 1), "ok": False, "estado": "error"}; estadisticas.append(stat)
                if progreso: progreso({"tipo":"resultado_fuente","fuente":nombre,"mensaje":f"{nombre}: no se pudo completar","estadistica":stat})
    finally:
        if browser is not None:
            browser.close()
        if playwright is not None:
            playwright.stop()

    vistos, salida = set(), []
    for oferta in ofertas:
        key = (oferta.get("titulo", "").strip().lower(), oferta.get("empresa", "").strip().lower(), oferta.get("fuente", ""))
        if key in vistos:
            continue
        vistos.add(key); salida.append(oferta)
    return salida, errores, estadisticas
