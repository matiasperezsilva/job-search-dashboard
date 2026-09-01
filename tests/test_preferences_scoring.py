
from jobsearch.services.cv_profile import construir_perfil_desde_texto
from jobsearch.services.scoring import evaluar_oferta, _extraer_renta_clp, _detectar_modalidad


def _qa_profile():
    p = construir_perfil_desde_texto(
        "Analista QA con 3 años de experiencia en testing, Postman, Selenium, Jira y SQL"
    )
    return p


def _job(desc, modalidad=""):
    return {
        "titulo": "Analista QA",
        "descripcion": desc,
        "modalidad": modalidad,
        "link": "https://example.com/jobs/qa-1",
        "fuente": "Test",
    }


def _component(result, label):
    return next(c for c in result["match_breakdown"]["components"] if c["label"] == label)


def test_remote_preference_adds_bonus_and_location_is_neutral():
    p = _qa_profile()
    p["preferencias"] = {
        "modalidades": ["remoto"],
        "ubicaciones": ["Santiago"],
        "renta_minima": 1200000,
        "moneda": "CLP",
    }
    r = evaluar_oferta(_job("Testing Postman Selenium Jira. Trabajo 100% remoto."), p)
    assert _component(r, "Modalidad")["value"] == 5
    assert _component(r, "Ubicación")["value"] == 0
    assert _component(r, "Renta")["value"] == 0


def test_declared_unwanted_modality_penalizes():
    p = _qa_profile()
    p["preferencias"] = {"modalidades": ["remoto"], "ubicaciones": [], "renta_minima": None}
    r = evaluar_oferta(_job("Testing Postman Selenium Jira.", "Presencial"), p)
    assert _component(r, "Modalidad")["value"] == -8


def test_location_match_adds_bonus():
    p = _qa_profile()
    p["preferencias"] = {"modalidades": [], "ubicaciones": ["Providencia"], "renta_minima": None}
    r = evaluar_oferta(_job("Testing Postman Selenium Jira. Oficina en Providencia."), p)
    assert _component(r, "Ubicación")["value"] == 4


def test_unknown_location_does_not_penalize():
    p = _qa_profile()
    p["preferencias"] = {"modalidades": [], "ubicaciones": ["Santiago"], "renta_minima": None}
    r = evaluar_oferta(_job("Testing Postman Selenium Jira. Ubicación a convenir."), p)
    assert _component(r, "Ubicación")["value"] == 0


def test_salary_below_minimum_penalizes_and_missing_salary_is_neutral():
    p = _qa_profile()
    p["preferencias"] = {"modalidades": [], "ubicaciones": [], "renta_minima": 1500000}
    low = evaluar_oferta(_job("Testing Postman Selenium Jira. Renta: $1.200.000 mensual."), p)
    missing = evaluar_oferta(_job("Testing Postman Selenium Jira. Renta acorde al mercado."), p)
    assert _component(low, "Renta")["value"] == -15
    assert _component(missing, "Renta")["value"] == 0


def test_salary_meets_minimum_adds_bonus():
    p = _qa_profile()
    p["preferencias"] = {"modalidades": [], "ubicaciones": [], "renta_minima": 1200000}
    r = evaluar_oferta(_job("Testing Postman Selenium Jira. Sueldo: $1.500.000 mensual."), p)
    assert _component(r, "Renta")["value"] == 6


def test_salary_parser_requires_salary_context():
    assert _extraer_renta_clp("Empresa fundada en 1.500.000 cosas") is None
    assert _extraer_renta_clp("Renta: $1.500.000 mensual") == {"min": 1500000, "max": 1500000}


def test_modality_parser():
    assert "remoto" in _detectar_modalidad("Trabajo remoto 100%")
    assert "híbrido" in _detectar_modalidad("Modalidad híbrida")
    assert "presencial" in _detectar_modalidad("Cargo presencial")
