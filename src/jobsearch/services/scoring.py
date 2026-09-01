from jobsearch.scrapers.common import (
    contexto_calidad_no_software,
    contexto_software,
    es_relevante_perfil,
    oferta_es_valida,
)


def _contiene(texto, termino):
    return termino.lower() in (texto or "").lower()


def evaluar_oferta(oferta, perfil):
    titulo = oferta.get("titulo", "") or ""
    descripcion = oferta.get("descripcion", "") or ""
    modalidad = oferta.get("modalidad", "") or ""
    fuente = oferta.get("fuente", "") or ""
    texto = f"{titulo} {descripcion} {modalidad}".lower()

    # Regla dura: antes de puntuar, demostrar que ES una vacante individual.
    if not oferta_es_valida(oferta):
        return {"puntaje": 0, "area": "Descartada", "razon": "Página de resultados/SEO o URL que no corresponde a una vacante individual.", "coincidencias": []}

    for termino in perfil.get("penalizaciones", {}).get("roles_no_objetivo", []):
        if _contiene(titulo, termino):
            return {"puntaje": 0, "area": "Fuera de objetivo", "razon": f"El cargo está orientado a {termino}, no al perfil técnico objetivo.", "coincidencias": []}

    software = contexto_software(titulo, descripcion)
    no_software = contexto_calidad_no_software(titulo, descripcion)
    titulo_lower = titulo.lower()

    # En portales generalistas, QA ambiguo exige evidencia TI real.
    qa_ambiguo = any(x in titulo_lower for x in ("qa", "quality", "calidad", "qc", "tester", "testing"))
    if qa_ambiguo and fuente.lower() != "getonboard":
        if no_software >= 1 and software < 2:
            return {"puntaje": 0, "area": "Fuera de objetivo", "razon": "QA/calidad fuera de contexto de software o TI.", "coincidencias": []}
        if software < 1 and not any(x in titulo_lower for x in ("qa automation", "qa automatizador", "qa funcional", "tester software", "sdet")):
            return {"puntaje": 8, "area": "Sin evidencia TI", "razon": "El título menciona QA/calidad, pero la publicación no entrega evidencia suficiente de testing de software.", "coincidencias": []}

    if not es_relevante_perfil(titulo, descripcion):
        # GetOnBoard es un portal TI; permitir títulos técnicos explícitos aunque el HTML resumido tenga poca descripción.
        if not (fuente.lower() == "getonboard" and any(x in titulo_lower for x in ("qa", "tester", "cloud", "devops", "dba", "sre"))):
            return {"puntaje": 10, "area": "Sin clasificar", "razon": "No contiene suficiente evidencia de un rol TI compatible con el perfil.", "coincidencias": []}

    candidatos = []
    for area, cfg in perfil.get("areas", {}).items():
        hits_titulo = [k for k in cfg.get("titulo", []) if _contiene(titulo, k)]
        hits_skills = [k for k in cfg.get("skills", []) if _contiene(texto, k)]
        if not hits_titulo and len(hits_skills) < 2:
            continue
        base = 58 if hits_titulo else 34
        base *= float(cfg.get("peso", 1.0))
        puntos_skills = min(28, len(set(hits_skills)) * 4)
        score = base + puntos_skills
        if area == "QA / Testing":
            score += min(10, software * 2)
        candidatos.append((score, area, hits_titulo, hits_skills, cfg))

    if not candidatos:
        return {"puntaje": 15, "area": "Sin clasificar", "razon": "No se detectaron suficientes señales de las áreas configuradas.", "coincidencias": []}

    score, area, hits_titulo, hits_skills, cfg = max(candidatos, key=lambda x: x[0])
    bonus, penal = [], []

    dominios = [d for d in perfil.get("dominios_valorados", []) if d.lower() in texto]
    if dominios:
        score += min(6, len(dominios) * 2); bonus.append("dominio relacionado")

    senioridad = [s for s in perfil.get("penalizaciones", {}).get("senioridad", []) if s.lower() in titulo_lower]
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
