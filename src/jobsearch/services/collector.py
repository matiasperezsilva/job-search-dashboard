import importlib
import os
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


def recolectar(fuentes, terminos=None, headless=True):
    """Recolecta ofertas usando términos derivados del CV activo.

    Cada fuente se ejecuta de manera independiente. LinkedIn es opcional y se
    mantiene desactivado por defecto porque puede requerir autenticación y puede
    imponer controles anti-automatización.
    """
    ofertas = []
    errores = []
    terminos = [t.strip() for t in (terminos or []) if t and t.strip()]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        try:
            for nombre in fuentes:
                if nombre == "LinkedIn" and os.getenv("ENABLE_LINKEDIN", "false").lower() != "true":
                    errores.append({
                        "fuente": nombre,
                        "error": "Fuente opcional desactivada. La app funciona sin iniciar sesión en LinkedIn.",
                    })
                    continue
                modulo = importlib.import_module(f"jobsearch.scrapers.{FUENTES[nombre]}")
                try:
                    ofertas.extend(modulo.buscar_ofertas(browser, terminos=terminos or None))
                except Exception as exc:
                    errores.append({"fuente": nombre, "error": str(exc)})
        finally:
            browser.close()

    vistos = set()
    salida = []
    for oferta in ofertas:
        key = (
            oferta.get("titulo", "").strip().lower(),
            oferta.get("empresa", "").strip().lower(),
            oferta.get("fuente", ""),
        )
        if key in vistos:
            continue
        vistos.add(key)
        salida.append(oferta)
    return salida, errores
