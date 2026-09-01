
from jobsearch.services.cv_profile import construir_perfil_desde_texto
from jobsearch.services.scoring import evaluar_oferta


def test_breakdown_matches_final_score():
    profile = construir_perfil_desde_texto(
        "Analista QA con 3 años de experiencia en testing, Postman, Selenium, Jira y SQL"
    )
    job = {
        "titulo": "Analista QA",
        "descripcion": "Buscamos 3 años de experiencia en testing con Postman, Selenium y Jira.",
        "modalidad": "Híbrido",
        "link": "https://example.com/job/qa-1",
        "fuente": "Test",
    }
    result = evaluar_oferta(job, profile)
    breakdown = result["match_breakdown"]
    assert breakdown["final_score"] == result["puntaje"]
    assert len(breakdown["components"]) >= 6
    labels = {c["label"] for c in breakdown["components"]}
    assert {"Cargo / rol", "Competencias", "Experiencia", "Seniority"} <= labels


def test_experience_penalty_is_visible_in_breakdown():
    profile = construir_perfil_desde_texto(
        "Analista QA con 2 años de experiencia en testing, Postman, Selenium y Jira"
    )
    job = {
        "titulo": "Analista QA",
        "descripcion": "Requisito: mínimo 5 años de experiencia en testing. Postman Selenium Jira.",
        "modalidad": "",
        "link": "https://example.com/job/qa-2",
        "fuente": "Test",
    }
    result = evaluar_oferta(job, profile)
    exp = next(c for c in result["match_breakdown"]["components"] if c["label"] == "Experiencia")
    assert exp["value"] == -24
    assert "5 años" in exp["detail"]
    assert "2" in exp["detail"]


def test_invalid_offer_has_explainable_zero():
    profile = construir_perfil_desde_texto("Analista QA con Postman y Selenium")
    job = {
        "titulo": "23 Ofertas de trabajo de qa en Tarapacá",
        "descripcion": "",
        "modalidad": "",
        "link": "https://cl.computrabajo.com/trabajo-de-qa",
        "fuente": "Computrabajo",
    }
    result = evaluar_oferta(job, profile)
    assert result["puntaje"] == 0
    assert result["match_breakdown"]["final_score"] == 0
    assert result["match_breakdown"]["verdict"] in {"Vacante inválida", "Fuera de perfil"}
