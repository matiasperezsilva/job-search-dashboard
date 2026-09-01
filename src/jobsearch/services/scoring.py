from jobsearch.scrapers.common import oferta_es_valida, contexto_calidad_no_software
from jobsearch.services.cv_profile import _requisito_experiencia
import re


def _contains(text, term):
    return (term or "").lower() in (text or "").lower()



_MODALITY_TERMS = {
    "remoto": ("remoto", "remote", "teletrabajo", "home office", "work from home"),
    "híbrido": ("híbrido", "hibrido", "híbrida", "hibrida", "hybrid", "semipresencial"),
    "presencial": ("presencial", "on site", "onsite", "en oficina"),
}

_CHILE_LOCATIONS = (
    "santiago", "providencia", "las condes", "vitacura", "ñuñoa", "nunoa",
    "huechuraba", "maipú", "maipu", "pudahuel", "quilicura", "san bernardo",
    "la florida", "lo barnechea", "valparaíso", "valparaiso", "viña del mar",
    "concepción", "concepcion", "temuco", "antofagasta", "calama", "rancagua",
    "talca", "chillán", "chillan", "puerto montt", "la serena", "coquimbo",
)


def _detectar_modalidad(texto):
    low = (texto or "").lower()
    found = []
    for mode, terms in _MODALITY_TERMS.items():
        if any(term in low for term in terms):
            found.append(mode)
    return found


def _detectar_ubicaciones(texto):
    low = (texto or "").lower()
    return [loc for loc in _CHILE_LOCATIONS if loc in low]


def _money_to_int(raw):
    raw = (raw or "").lower().strip()
    multiplier = 1
    if re.search(r"\b(?:m|mill[oó]n|millones)\b", raw):
        multiplier = 1_000_000
    cleaned = re.sub(r"[^\d,\.]", "", raw)
    if not cleaned:
        return None
    # 1.500.000 / 1,500,000
    if cleaned.count(".") >= 2 or cleaned.count(",") >= 2:
        digits = re.sub(r"[^\d]", "", cleaned)
        value = int(digits) if digits else None
    elif multiplier == 1_000_000 and re.fullmatch(r"\d+[,.]\d+", cleaned):
        value = int(float(cleaned.replace(",", ".")) * multiplier)
        multiplier = 1
    else:
        digits = re.sub(r"[^\d]", "", cleaned)
        value = int(digits) if digits else None
    if value is None:
        return None
    value *= multiplier
    return value if 100_000 <= value <= 100_000_000 else None


def _extraer_renta_clp(texto):
    """Extrae una renta mensual solo cuando aparece cerca de señales salariales."""
    low = (texto or "").lower()
    patterns = [
        r"(?:renta|sueldo|salario|remuneraci[oó]n|líquido|liquido|bruto)[:\s]*(?:clp|\$)?\s*([\d\.,]+\s*(?:m|mill[oó]n(?:es)?)?)",
        r"(?:clp|\$)\s*([\d\.,]+)\s*(?:mensual(?:es)?|al mes)",
    ]
    vals = []
    for pat in patterns:
        for m in re.finditer(pat, low):
            val = _money_to_int(m.group(1))
            if val:
                vals.append(val)
    if not vals:
        return None
    return {"min": min(vals), "max": max(vals)}


def _evaluar_preferencias(oferta, perfil):
    prefs = perfil.get("preferencias") or {}
    modalidades_pref = [str(x).lower() for x in prefs.get("modalidades") or []]
    ubicaciones_pref = [str(x).lower() for x in prefs.get("ubicaciones") or []]
    renta_min = prefs.get("renta_minima")
    texto = " ".join(str(oferta.get(k, "") or "") for k in ("titulo", "descripcion", "modalidad"))

    components = []
    total = 0

    offered_modes = _detectar_modalidad(texto)
    modality_delta = 0
    if modalidades_pref and offered_modes:
        if any(m in modalidades_pref for m in offered_modes):
            modality_delta = 5
            modality_detail = f"Modalidad publicada: {', '.join(offered_modes)}; coincide con tus preferencias."
        else:
            modality_delta = -8
            modality_detail = f"Modalidad publicada: {', '.join(offered_modes)}; no está entre tus preferencias."
    elif modalidades_pref:
        modality_detail = "La oferta no declara una modalidad con suficiente claridad; no afecta el puntaje."
    else:
        modality_detail = "No configuraste una preferencia de modalidad."
    total += modality_delta
    components.append(_component(
        "Modalidad", modality_delta, modality_detail, None,
        "positive" if modality_delta > 0 else "negative" if modality_delta < 0 else "neutral"
    ))

    location_delta = 0
    detected_locations = _detectar_ubicaciones(texto)
    if ubicaciones_pref:
        if "remoto" in offered_modes:
            location_detail = "La oferta es remota; la ubicación no genera penalización."
        elif any(pref in texto.lower() for pref in ubicaciones_pref):
            location_delta = 4
            location_detail = "La ubicación publicada coincide con una de tus preferencias."
        elif detected_locations:
            location_delta = -6
            location_detail = f"Ubicación detectada: {', '.join(detected_locations[:3])}; no coincide con tus ubicaciones preferidas."
        else:
            location_detail = "La oferta no publica una ubicación suficientemente clara; no afecta el puntaje."
    else:
        location_detail = "No configuraste ubicaciones preferidas."
    total += location_delta
    components.append(_component(
        "Ubicación", location_delta, location_detail, None,
        "positive" if location_delta > 0 else "negative" if location_delta < 0 else "neutral"
    ))

    salary_delta = 0
    salary = _extraer_renta_clp(texto)
    if renta_min:
        try:
            target = int(renta_min)
            if salary:
                if salary["max"] < target:
                    salary_delta = -15
                    salary_detail = f"La renta publicada llega hasta ${salary['max']:,} CLP y tu mínimo es ${target:,} CLP.".replace(",", ".")
                elif salary["min"] >= target:
                    salary_delta = 6
                    salary_detail = f"La renta publicada cumple o supera tu mínimo de ${target:,} CLP.".replace(",", ".")
                else:
                    salary_delta = 2
                    salary_detail = f"El rango publicado incluye tu mínimo de ${target:,} CLP.".replace(",", ".")
            else:
                salary_detail = "La oferta no publica una renta mensual comparable; no afecta el puntaje."
        except (TypeError, ValueError):
            salary_detail = "La preferencia de renta no pudo interpretarse."
    else:
        salary_detail = "No configuraste una renta mínima."
    total += salary_delta
    components.append(_component(
        "Renta", salary_delta, salary_detail, None,
        "positive" if salary_delta > 0 else "negative" if salary_delta < 0 else "neutral"
    ))

    return total, components

def _component(label, value=0, detail="", max_value=None, kind="positive"):
    out = {
        "label": label,
        "value": int(round(value)),
        "detail": detail,
        "kind": kind,
    }
    if max_value is not None:
        out["max"] = int(max_value)
    return out


def _empty_breakdown(verdict, detail):
    return {
        "version": 1,
        "verdict": verdict,
        "components": [
            _component("Cargo / rol", 0, detail, 70, "neutral"),
            _component("Competencias", 0, "Sin evaluación por descarte previo.", 25, "neutral"),
            _component("Afinidad del área", 0, "Sin evaluación por descarte previo.", None, "neutral"),
            _component("Experiencia", 0, "Sin evaluación por descarte previo.", None, "neutral"),
            _component("Seniority", 0, "Sin evaluación por descarte previo.", None, "neutral"),
            _component("Requisitos adicionales", 0, "Sin evaluación por descarte previo.", None, "neutral"),
            _component("Modalidad", 0, "Sin evaluación por descarte previo.", None, "neutral"),
            _component("Ubicación", 0, "Sin evaluación por descarte previo.", None, "neutral"),
            _component("Renta", 0, "Sin evaluación por descarte previo.", None, "neutral"),
        ],
        "pre_clamp_score": 0,
        "final_score": 0,
    }


def evaluar_oferta(oferta, perfil):
    titulo = oferta.get("titulo", "") or ""
    descripcion = oferta.get("descripcion", "") or ""
    modalidad = oferta.get("modalidad", "") or ""
    texto = f"{titulo} {descripcion} {modalidad}".lower()

    if not oferta_es_valida(oferta):
        razon = "Página de resultados/SEO o URL que no corresponde a una vacante individual."
        return {
            "puntaje": 0, "area": "Descartada", "razon": razon, "coincidencias": [],
            "match_breakdown": _empty_breakdown("Vacante inválida", razon),
        }

    # Compatibilidad con perfiles antiguos: sus exclusiones explícitas siguen vigentes.
    for term in perfil.get("penalizaciones", {}).get("roles_no_objetivo", []):
        if _contains(titulo, term):
            razon = f"El cargo coincide con una exclusión configurada: {term}."
            return {
                "puntaje": 0, "area": "Fuera de perfil", "razon": razon, "coincidencias": [],
                "match_breakdown": _empty_breakdown("Fuera de perfil", razon),
            }

    # Desambiguación contextual basada en el perfil.
    industrial = contexto_calidad_no_software(titulo, descripcion)
    profile_areas = set((perfil.get("areas") or {}).keys())
    if industrial >= 1 and "Minería / Calidad industrial" not in profile_areas and any(
        x in titulo.lower() for x in ("qa", "qc", "calidad", "quality")
    ):
        razon = "La vacante corresponde a calidad industrial y ese ámbito no forma parte del perfil activo."
        return {
            "puntaje": 0, "area": "Fuera de perfil", "razon": razon, "coincidencias": [],
            "match_breakdown": _empty_breakdown("Área no compatible", razon),
        }

    candidatos = []
    for area, cfg in (perfil.get("areas") or {}).items():
        roles = cfg.get("titulo", [])
        skills = cfg.get("skills", [])
        hits_role = [x for x in roles if _contains(titulo, x)]
        hits_skill = [x for x in skills if _contains(texto, x)]

        # Un skill aislado nunca convierte un cargo ajeno en buen match.
        if not hits_role and len(set(hits_skill)) < 3:
            continue

        role_base = 52 if hits_role else 24
        role_bonus = min(18, len(set(hits_role)) * 8)
        role_score = role_base + role_bonus
        skill_score = min(25, len(set(hits_skill)) * 5)
        pre_weight = role_score + skill_score
        weight = float(cfg.get("peso", 1.0))
        weighted = pre_weight * weight
        area_delta = weighted - pre_weight

        candidatos.append({
            "score": weighted,
            "area": area,
            "hits_role": hits_role,
            "hits_skill": hits_skill,
            "cfg": cfg,
            "role_score": role_score,
            "skill_score": skill_score,
            "area_delta": area_delta,
            "weight": weight,
        })

    if not candidatos:
        razon = "La vacante no coincide suficientemente con los roles o competencias del perfil activo."
        breakdown = _empty_breakdown("Bajo calce", razon)
        breakdown["pre_clamp_score"] = 8
        breakdown["final_score"] = 8
        breakdown["components"][0] = _component(
            "Cargo / rol", 8, "No se detectó un cargo objetivo ni suficientes competencias relacionadas.", 70, "neutral"
        )
        return {
            "puntaje": 8, "area": "Bajo calce", "razon": razon, "coincidencias": [],
            "match_breakdown": breakdown,
        }

    best = max(candidatos, key=lambda x: x["score"])
    score = best["score"]
    area = best["area"]
    hits_role = best["hits_role"]
    hits_skill = best["hits_skill"]
    cfg = best["cfg"]
    penal = []

    components = [
        _component(
            "Cargo / rol",
            best["role_score"],
            ("Coincide con: " + ", ".join(dict.fromkeys(hits_role)))
            if hits_role else "No hay coincidencia directa de cargo; se exige mayor evidencia por competencias.",
            70,
        ),
        _component(
            "Competencias",
            best["skill_score"],
            ("Coinciden: " + ", ".join(list(dict.fromkeys(hits_skill))[:8]))
            if hits_skill else "No se detectaron competencias coincidentes.",
            25,
        ),
        _component(
            "Afinidad del área",
            best["area_delta"],
            f"Área seleccionada: {area} · factor {best['weight']:.2f}x.",
            None,
            "positive" if best["area_delta"] >= 0 else "negative",
        ),
    ]

    seniority_delta = 0
    seniority_detail = "Sin penalización de seniority."
    seniority = [
        x for x in perfil.get("penalizaciones", {}).get("senioridad", [])
        if x.lower() in titulo.lower()
    ]
    nivel = cfg.get("nivel", "")
    if seniority and nivel in {"junior", "no especificado"}:
        seniority_delta = -18
        score += seniority_delta
        penal.append("senioridad superior al perfil")
        seniority_detail = f"El cargo contiene {', '.join(seniority)} y el perfil está en nivel {nivel or 'no especificado'}."
    components.append(_component(
        "Seniority", seniority_delta, seniority_detail, None,
        "negative" if seniority_delta < 0 else "neutral",
    ))

    requirements_delta = 0
    req_details = []
    ingles = [
        x for x in perfil.get("penalizaciones", {}).get("ingles_avanzado", [])
        if x.lower() in texto
    ]
    if ingles:
        requirements_delta -= 8
        penal.append("inglés avanzado solicitado")
        req_details.append("Solicita inglés avanzado.")
    else:
        req_details.append("Sin penalizaciones adicionales detectadas.")
    score += requirements_delta

    experience_delta = 0
    experience_detail = "La oferta no declara un mínimo de años comparable."
    req_years = _requisito_experiencia(f"{titulo} {descripcion}")
    candidate_years = (perfil.get("resumen") or {}).get("anos_experiencia")
    if req_years and candidate_years is not None:
        try:
            candidate_years = float(candidate_years)
            gap = float(req_years) - candidate_years
            if gap >= 3:
                experience_delta = -24
                penal.append(f"solicita {req_years} años y el perfil acredita aprox. {candidate_years:g}")
            elif gap >= 1:
                experience_delta = -12
                penal.append(f"solicita {req_years} años y el perfil acredita aprox. {candidate_years:g}")
            elif gap <= 0:
                experience_delta = 4
            experience_detail = (
                f"La oferta solicita {req_years} años; el perfil acredita aprox. {candidate_years:g}."
            )
            score += experience_delta
        except (TypeError, ValueError):
            experience_detail = "No fue posible comparar los años con suficiente seguridad."
    elif req_years and candidate_years is None:
        experience_detail = (
            f"La oferta solicita {req_years} años, pero el CV no permite estimar años con suficiente seguridad."
        )

    components.append(_component(
        "Experiencia", experience_delta, experience_detail, None,
        "positive" if experience_delta > 0 else "negative" if experience_delta < 0 else "neutral",
    ))
    components.append(_component(
        "Requisitos adicionales", requirements_delta, " ".join(req_details), None,
        "negative" if requirements_delta < 0 else "neutral",
    ))

    preferences_delta, preference_components = _evaluar_preferencias(oferta, perfil)
    score += preferences_delta
    components.extend(preference_components)

    pre_clamp = round(score)
    final_score = max(0, min(100, pre_clamp))
    coincidencias = list(dict.fromkeys(hits_role + hits_skill))[:10]
    razon = f"Mejor calce: {area}. Coincidencias: {', '.join(coincidencias) or 'señales del perfil'}."
    if penal:
        razon += " Penalización por " + ", ".join(penal) + "."

    verdict = (
        "Calce alto" if final_score >= 70
        else "Calce medio" if final_score >= 50
        else "Calce bajo"
    )
    breakdown = {
        "version": 1,
        "verdict": verdict,
        "components": components,
        "pre_clamp_score": pre_clamp,
        "final_score": final_score,
        "area": area,
        "matched_roles": list(dict.fromkeys(hits_role))[:6],
        "matched_skills": list(dict.fromkeys(hits_skill))[:10],
    }

    return {
        "puntaje": final_score,
        "area": area,
        "razon": razon,
        "coincidencias": coincidencias,
        "match_breakdown": breakdown,
    }
