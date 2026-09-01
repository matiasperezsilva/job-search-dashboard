from __future__ import annotations
import json
from urllib import error, parse, request
from jobsearch.services.letters import ConfigGemini, _sanitizar_cv_para_ia, _extraer_contenido_gemini


def enriquecer_perfil_con_gemini(cv_texto: str, base: dict, config: ConfigGemini) -> dict:
    """Convierte cualquier CV en un perfil laboral estructurado.

    Gemini amplía cobertura para profesiones fuera de la taxonomía local. El usuario
    mantiene control porque los cargos objetivo siguen siendo editables en la UI.
    """
    cv = _sanitizar_cv_para_ia(cv_texto)[:18000]
    schema = {
        "type": "OBJECT",
        "properties": {
            "area_principal": {"type": "STRING"},
            "areas_secundarias": {"type": "ARRAY", "items": {"type": "STRING"}},
            "roles_objetivo": {"type": "ARRAY", "items": {"type": "STRING"}},
            "competencias": {"type": "ARRAY", "items": {"type": "STRING"}},
            "seniority": {"type": "STRING"},
            "industrias": {"type": "ARRAY", "items": {"type": "STRING"}},
            "anos_experiencia_relevante": {"type": "NUMBER"},
        },
        "required": ["area_principal", "areas_secundarias", "roles_objetivo", "competencias", "seniority", "industrias", "anos_experiencia_relevante"],
    }
    prompt = f"""Analiza este currículum para un buscador laboral multiprofesional.
No asumas que pertenece a tecnología. Extrae únicamente información respaldada por el CV.
Los roles_objetivo deben ser nombres de cargos reales que la persona podría buscar por su experiencia/formación, no tecnologías aisladas.
Para area_principal y roles_objetivo, prioriza en este orden: experiencia profesional real, título/encabezado profesional del CV y luego formación. Un proyecto académico, proyecto de título o tesis puede aportar competencias, pero NO debe desplazar a la experiencia laboral como área principal.
No clasifiques QA de software como calidad industrial/minería solo por frases genéricas como "aseguramiento de calidad"; exige señales industriales explícitas como faena, minería, ISO 9001, QA/QC, inspección, manufactura, laboratorio o similares.
Devuelve entre 2 y 10 roles objetivo y hasta 25 competencias. No incluyas datos personales.
Calcula anos_experiencia_relevante usando SOLO experiencia profesional/laboral respaldada por fechas o duración explícita. No sumes períodos superpuestos, estudios ni proyectos académicos. Si no puede determinarse con seguridad, usa 0.

CURRÍCULUM:
{cv}"""
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{parse.quote(config.model, safe='-_.')}:generateContent"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 1000, "responseMimeType": "application/json", "responseSchema": schema},
    }
    req = request.Request(endpoint, data=json.dumps(payload).encode(), headers={"x-goog-api-key": config.api_key, "Content-Type": "application/json"}, method="POST")
    try:
        with request.urlopen(req, timeout=min(config.timeout, 45)) as resp:
            raw = _extraer_contenido_gemini(json.loads(resp.read().decode()))
            ai = json.loads(raw)
    except Exception:
        return base  # El CV nunca deja de funcionar si la IA/cuota falla.

    roles = list(dict.fromkeys(str(x).strip() for x in ai.get("roles_objetivo", []) if str(x).strip()))[:16]
    skills = list(dict.fromkeys(str(x).strip().lower() for x in ai.get("competencias", []) if str(x).strip()))[:40]
    areas_names = [str(ai.get("area_principal", "")).strip()] + [str(x).strip() for x in ai.get("areas_secundarias", [])]
    areas_names = list(dict.fromkeys(x for x in areas_names if x))[:5]
    if not roles or not areas_names:
        return base

    # Cada área comparte el conjunto inferido de roles/competencias; el scoring exige
    # coincidencia de cargo o varias competencias, evitando matches por una sola keyword.
    areas = {}
    for i, area in enumerate(areas_names):
        areas[area] = {"titulo": roles, "skills": skills, "peso": 1.15 if i == 0 else 0.95, "nivel": str(ai.get("seniority") or "no especificado").lower()}
    out = dict(base)
    out["origen"] = "cv+gemini"
    out["version_perfil"] = 3
    out["areas"] = areas
    out["dominios_valorados"] = [str(x).strip() for x in ai.get("industrias", []) if str(x).strip()][:12]
    resumen = dict(base.get("resumen") or {})
    local_years = resumen.get("anos_experiencia")
    ai_years = max(0, float(ai.get("anos_experiencia_relevante") or 0))
    # Una estimación determinística por rangos de fechas tiene prioridad. Gemini solo
    # completa cuando el parser local no pudo obtener duración laboral.
    final_years = local_years if local_years is not None else (ai_years if ai_years > 0 else None)
    resumen.update({"areas_detectadas": areas_names, "skills_detectadas": skills, "roles_objetivo": roles, "terminos_busqueda": roles, "seniority_estimado": str(ai.get("seniority") or "no especificado"), "anos_experiencia": final_years})
    if final_years is not None and resumen.get("meses_experiencia") is None:
        resumen["meses_experiencia"] = int(round(float(final_years) * 12))
        resumen["experiencia_fuente"] = "gemini"
    out["resumen"] = resumen
    return out
