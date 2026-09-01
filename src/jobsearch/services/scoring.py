from jobsearch.scrapers.common import (
    contexto_calidad_no_software,
    contexto_software,
    es_pagina_busqueda,
    es_relevante_perfil,
)


def _contiene(texto, termino):
    return termino.lower() in (texto or "").lower()


def evaluar_oferta(oferta, perfil):
    titulo = oferta.get("titulo", "") or ""
    descripcion = oferta.get("descripcion", "") or ""
    modalidad = oferta.get("modalidad", "") or ""
    texto = f"{titulo} {descripcion} {modalidad}".lower()

    if es_pagina_busqueda(titulo):
        return {"puntaje": 0, "area": "Descartada", "razon": "La URL corresponde a una página de búsqueda, no a una vacante individual.", "coincidencias": []}

    for termino in perfil.get("penalizaciones", {}).get("roles_no_objetivo", []):
        if _contiene(titulo, termino):
            return {"puntaje": 5, "area": "Fuera de objetivo", "razon": f"El cargo parece orientado a {termino}, no al perfil técnico objetivo.", "coincidencias": []}

    software = contexto_software(titulo, descripcion)
    no_software = contexto_calidad_no_software(titulo, descripcion)
    if no_software and software < 2 and any(x in titulo.lower() for x in ("qa", "calidad", "quality", "qc")):
        return {"puntaje": 0, "area": "Fuera de objetivo", "razon": "QA/calidad detectado fuera del contexto de software o TI.", "coincidencias": []}

    if not es_relevante_perfil(titulo, descripcion):
        return {"puntaje": 12, "area": "Sin clasificar", "razon": "La oferta no contiene suficiente evidencia de un rol TI compatible con el perfil.", "coincidencias": []}

    candidatos = []
    for area, cfg in perfil.get("areas", {}).items():
        hits_titulo = [k for k in cfg.get("titulo", []) if _contiene(titulo, k)]
        hits_skills = [k for k in cfg.get("skills", []) if _contiene(texto, k)]
        if not hits_titulo and len(hits_skills) < 2:
            continue
        base = 60 if hits_titulo else 36
        base *= float(cfg.get("peso", 1.0))
        puntos_skills = min(28, len(set(hits_skills)) * 4)
        score = base + puntos_skills
        if area == "QA / Testing":
            score += min(8, software * 2)
        candidatos.append((score, area, hits_titulo, hits_skills, cfg))

    if not candidatos:
        return {"puntaje": 18, "area": "Sin clasificar", "razon": "No se detectaron suficientes señales de las áreas configuradas.", "coincidencias": []}

    score, area, hits_titulo, hits_skills, cfg = max(candidatos, key=lambda x: x[0])
    bonus, penal = [], []

    dominios = [d for d in perfil.get("dominios_valorados", []) if d.lower() in texto]
    if dominios:
        score += min(6, len(dominios) * 2); bonus.append("dominio relacionado")

    senioridad = [s for s in perfil.get("penalizaciones", {}).get("senioridad", []) if s.lower() in titulo.lower()]
    if senioridad and cfg.get("nivel") in {"junior", "parcial"}:
        score -= 22; penal.append("senioridad superior al nivel configurado")

    ingles = [s for s in perfil.get("penalizaciones", {}).get("ingles_avanzado", []) if s.lower() in texto]
    if ingles:
        score -= 10; penal.append("inglés avanzado solicitado")

    score = max(0, min(100, round(score)))
    coincidencias = list(dict.fromkeys(hits_titulo + hits_skills))[:8]
    detalle = f"Mejor calce: {area} ({cfg.get('nivel', '')})."
    if coincidencias: detalle += " Coincidencias: " + ", ".join(coincidencias) + "."
    if bonus: detalle += " Bonus por " + ", ".join(bonus) + "."
    if penal: detalle += " Penalización por " + ", ".join(penal) + "."

    return {"puntaje": score, "area": area, "razon": detalle, "coincidencias": coincidencias}
