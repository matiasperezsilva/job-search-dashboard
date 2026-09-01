import importlib
import os
import time
from playwright.sync_api import sync_playwright
from jobsearch.scrapers.common import es_relevante_perfil

FUENTES = {
    "GetOnBoard": "getonbrd",
    "Computrabajo": "computrabajo",
    "ChileTrabajos": "chiletrabajos",
    "Laborum": "laborum",
    "Trabajando.com": "trabajando",
    "BNE": "bne",
    "LinkedIn": "linkedin",
}


def recolectar(fuentes, terminos=None, headless=True, modo="rapida", progreso=None):
    """Recolecta secuencialmente y falla de forma aislada por fuente.

    GetOnBoard y Computrabajo usan HTTP directo; Chromium sólo se inicia si una
    fuente realmente lo necesita. En Render Free esto ahorra RAM y cold-start.
    """
    ofertas, errores, estadisticas = [], [], []
    limite_terminos = 6 if modo == "rapida" else 12
    terminos = list(dict.fromkeys(t.strip() for t in (terminos or []) if t and t.strip()))[:limite_terminos]

    playwright = None
    browser = None
    try:
        for pos, nombre in enumerate(fuentes, 1):
            if nombre == "LinkedIn" and os.getenv("ENABLE_LINKEDIN", "false").lower() != "true":
                errores.append({"fuente": nombre, "error": "Integración opcional desactivada."})
                continue
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
                resultado = [o for o in resultado if es_relevante_perfil(o.get("titulo", ""), o.get("descripcion", ""))]
                ofertas.extend(resultado)
                estadisticas.append({"fuente": nombre, "cantidad": len(resultado), "segundos": round(time.monotonic()-inicio, 1), "ok": True})
            except Exception as exc:
                errores.append({"fuente": nombre, "error": str(exc)})
                estadisticas.append({"fuente": nombre, "cantidad": 0, "segundos": round(time.monotonic()-inicio, 1), "ok": False})
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
