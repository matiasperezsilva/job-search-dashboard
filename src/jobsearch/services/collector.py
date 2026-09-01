import importlib
import os
import time
from playwright.sync_api import sync_playwright

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
    """Recolecta por fuente, con límites agresivos en modo rápido.

    `progreso` recibe eventos dict para que la UI pueda informar qué está
    ocurriendo sin parecer bloqueada.
    """
    ofertas, errores, estadisticas = [], [], []
    limite_terminos = 6 if modo == "rapida" else 12
    terminos = list(dict.fromkeys(t.strip() for t in (terminos or []) if t and t.strip()))[:limite_terminos]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, args=["--disable-dev-shm-usage", "--no-sandbox"])
        try:
            for pos, nombre in enumerate(fuentes, 1):
                if nombre == "LinkedIn" and os.getenv("ENABLE_LINKEDIN", "false").lower() != "true":
                    errores.append({"fuente": nombre, "error": "Integración opcional desactivada."})
                    continue
                if progreso:
                    progreso({"tipo": "fuente", "fuente": nombre, "indice": pos, "total": len(fuentes), "mensaje": f"Consultando {nombre}…"})
                modulo = importlib.import_module(f"jobsearch.scrapers.{FUENTES[nombre]}")
                inicio = time.monotonic()
                try:
                    def sub(msg):
                        if progreso:
                            progreso({"tipo": "detalle", "fuente": nombre, "mensaje": msg})
                    try:
                        resultado = modulo.buscar_ofertas(browser, terminos=terminos or None, modo=modo, progreso=sub)
                    except TypeError:
                        # Compatibilidad con adaptadores que todavía no usan la nueva firma.
                        resultado = modulo.buscar_ofertas(browser, terminos=terminos or None)
                    ofertas.extend(resultado)
                    estadisticas.append({"fuente": nombre, "cantidad": len(resultado), "segundos": round(time.monotonic()-inicio, 1), "ok": True})
                except Exception as exc:
                    errores.append({"fuente": nombre, "error": str(exc)})
                    estadisticas.append({"fuente": nombre, "cantidad": 0, "segundos": round(time.monotonic()-inicio, 1), "ok": False})
        finally:
            browser.close()

    vistos, salida = set(), []
    for oferta in ofertas:
        key = (oferta.get("titulo", "").strip().lower(), oferta.get("empresa", "").strip().lower(), oferta.get("fuente", ""))
        if key in vistos:
            continue
        vistos.add(key); salida.append(oferta)
    return salida, errores, estadisticas
