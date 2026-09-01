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
                    resultado_bruto = modulo.buscar_ofertas(target_browser, terminos=terminos or None, modo=modo, progreso=sub)
                except TypeError:
                    resultado_bruto = modulo.buscar_ofertas(target_browser, terminos=terminos or None)

                if resultado_bruto is None:
                    resultado_bruto = []
                raw_count = len(resultado_bruto)

                # Diagnóstico opcional enriquecido por adaptador.
                source_diag = {}
                get_diag = getattr(modulo, "get_last_diagnostic", None)
                if callable(get_diag):
                    try:
                        source_diag = dict(get_diag() or {})
                    except Exception:
                        source_diag = {}

                validas = [o for o in resultado_bruto if oferta_es_valida(o)]
                resultado = [
                    o for o in validas
                    if es_relevante_perfil(o.get("titulo", ""), o.get("descripcion", ""), terminos)
                ]
                ofertas.extend(resultado)
                if on_source_result:
                    on_source_result(nombre, resultado)

                enlaces = int(source_diag.get("links_found", raw_count) or 0)
                extraidas = int(source_diag.get("offers_extracted", raw_count) or 0)
                detalle_fallos = int(source_diag.get("detail_errors", 0) or 0)
                query_errors = int(source_diag.get("query_errors", 0) or 0)
                blocked = bool(source_diag.get("blocked", False))
                invalidas = max(0, raw_count - len(validas))
                filtradas = max(0, len(validas) - len(resultado))

                if resultado:
                    estado = "ok"
                    diagnostico = f"{len(resultado)} coincidencias relevantes"
                elif blocked:
                    estado = "blocked"
                    diagnostico = "El portal respondió con bloqueo/CAPTCHA o verificación anti-bot"
                elif enlaces == 0 and query_errors > 0:
                    estado = "query_error"
                    diagnostico = "Las consultas al portal fallaron antes de obtener enlaces"
                elif enlaces == 0:
                    estado = "no_links"
                    diagnostico = "El adaptador no encontró enlaces de vacantes en los resultados"
                elif extraidas == 0:
                    estado = "extract_error"
                    diagnostico = f"Se encontraron {enlaces} enlaces, pero ninguna ficha pudo extraerse"
                elif filtradas > 0 or invalidas > 0:
                    estado = "filtered"
                    diagnostico = f"Se extrajeron {extraidas} fichas, pero ninguna pasó la validación/matching"
                else:
                    estado = "empty"
                    diagnostico = "El portal respondió sin coincidencias relevantes"

                stat = {
                    "fuente": nombre,
                    "cantidad": len(resultado),
                    "segundos": round(time.monotonic()-inicio, 1),
                    "ok": estado in {"ok", "empty", "filtered"},
                    "estado": estado,
                    "diagnostico": diagnostico,
                    "raw_count": raw_count,
                    "links_found": enlaces,
                    "offers_extracted": extraidas,
                    "invalid_count": invalidas,
                    "filtered_count": filtradas,
                    "detail_errors": detalle_fallos,
                    "query_errors": query_errors,
                    "blocked": blocked,
                    "transport": source_diag.get("transport", "browser" if uses_browser else "http"),
                }
                estadisticas.append(stat)
                if progreso:
                    progreso({
                        "tipo":"resultado_fuente",
                        "fuente":nombre,
                        "mensaje":f"{nombre}: {diagnostico}",
                        "estadistica":stat
                    })
            except Exception as exc:
                error_text = str(exc) or type(exc).__name__
                errores.append({"fuente": nombre, "error": error_text})
                stat={
                    "fuente": nombre, "cantidad": 0,
                    "segundos": round(time.monotonic()-inicio, 1),
                    "ok": False, "estado": "error",
                    "diagnostico": f"Error del adaptador: {error_text[:160]}",
                    "raw_count": 0, "links_found": 0, "offers_extracted": 0,
                    "invalid_count": 0, "filtered_count": 0,
                    "detail_errors": 0, "query_errors": 1, "blocked": False,
                }
                estadisticas.append(stat)
                if progreso:
                    progreso({"tipo":"resultado_fuente","fuente":nombre,"mensaje":f"{nombre}: error del adaptador","estadistica":stat})
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
