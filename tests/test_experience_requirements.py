from datetime import datetime, timezone
from types import SimpleNamespace

from backend.repository import Repository
from jobsearch.services.cv_profile import construir_perfil_desde_texto, perfil_para_matching
from jobsearch.services.experience import requisitos
from jobsearch.services.scoring import evaluar_oferta


CV = """Ingeniera en Informática
EXPERIENCIA PROFESIONAL
Analista QA — enero 2020 a diciembre 2023
Pruebas con Selenium y Jira.
Cloud Support — 01/2023 a 12/2023
Administración y monitoreo de AWS y CloudWatch.
Certificaciones
AWS Certified Cloud Practitioner — enero 2018 a diciembre 2025
Curso Terraform de 3 años de experiencia simulada
"""


def job(text, title="Cloud Support"):
    return {"titulo": title, "descripcion": text, "link": "https://example.com/vacante", "fuente": "Test"}


def evaluate(text, profile=None, title="Cloud Support"):
    return evaluar_oferta(job(text, title), profile or construir_perfil_desde_texto(CV))


def assessed(result):
    return result["match_breakdown"]["experience_requirements"]


def test_total_and_relevant_experience_are_independent_and_overlap_is_unioned():
    result = evaluate("3 años de experiencia profesional. 2 años de experiencia en AWS.")
    total, aws = assessed(result)
    assert (total["tipo"], total["acreditado_meses"], total["cumple"]) == ("total", 48, True)
    assert (aws["tipo"], aws["acreditado_meses"], aws["cumple"]) == ("tecnologia", 12, False)
    assert result["puntaje"] == 0
    assert result["match_breakdown"]["experience_blocked"]


def test_area_and_exact_job_have_separate_evidence():
    result = evaluate("1 año de experiencia en cloud. 2 años de experiencia como Cloud Engineer.")
    cloud, engineer = assessed(result)
    assert (cloud["tipo"], cloud["acreditado_meses"]) == ("area", 12)
    assert (engineer["tipo"], engineer["acreditado_meses"]) == ("cargo", 0)
    assert "2 años" in result["razon"]


def test_courses_and_certifications_never_credit_professional_time():
    cv = "Certificaciones\nAWS Certified Cloud Practitioner Ene 2020 - Dic 2024\nCurso de 5 años de experiencia simulada"
    profile = construir_perfil_desde_texto(cv)
    assert profile["resumen"]["meses_experiencia"] is None
    result = evaluate("12 meses de experiencia profesional.", profile)
    assert result["match_breakdown"]["experience_blocked"]
    assert "sin duración acreditada" in result["razon"]


def test_keyword_strength_does_not_override_the_largest_mandatory_requirement():
    result = evaluate("1 año de experiencia profesional. Mínimo 5 años de experiencia. AWS CloudWatch Selenium Jira Cloud Support.")
    assert result["puntaje"] == 0
    assert "5 años" in result["razon"]


def test_range_prefers_minimum_and_desirable_only_penalizes():
    result = evaluate("Entre 1 y 3 años de experiencia en AWS. Deseable: 5 años de experiencia en Terraform.")
    aws, terraform = assessed(result)
    assert (aws["minimo_meses"], aws["maximo_meses"], aws["cumple"]) == (12, 36, True)
    assert not terraform["obligatorio"]
    assert not result["match_breakdown"].get("experience_blocked")
    experience = next(x for x in result["match_breakdown"]["components"] if x["label"] == "Experiencia")
    assert experience["value"] == -6


def test_desirable_inline_clause_does_not_leak_to_the_next_mandatory_minimum():
    preferred, required = requisitos("5 años de experiencia en Azure (deseable), mínimo 2 años de experiencia en AWS")
    assert not preferred["obligatorio"] and required["obligatorio"]
    assert requisitos("Experiencia en AWS de 3 años")[0]["ambito"] == "aws"
    assert requisitos("3+ years of experience with AWS")[0]["minimo_meses"] == 36
    assert not requisitos("Somos una empresa con 20 años de experiencia en el mercado.")


def test_technology_lists_support_alternatives_and_do_not_credit_certification():
    result = evaluate("1 año de experiencia en AWS o Terraform.")
    assert assessed(result)[0]["cumple"]
    result = evaluate("1 año de experiencia en AWS y Terraform.")
    assert result["match_breakdown"]["experience_blocked"]


def test_matching_is_not_specific_to_technical_professions():
    profile = construir_perfil_desde_texto("EXPERIENCIA\nEnfermera — ene 2020 - dic 2021\nAtención de pacientes.")
    passes = evaluate("2 años en enfermería.", profile, "Enfermera")
    fails = evaluate("3 años en enfermería.", profile, "Enfermera")
    assert assessed(passes)[0]["cumple"]
    assert fails["match_breakdown"]["experience_blocked"]


def test_legacy_snapshot_is_rebuilt_from_the_cv():
    stored = {"profile_data": {"resumen": {"anos_experiencia": 20, "terminos_busqueda": ["Soporte Cloud"]}}, "cv_text": CV}
    profile = perfil_para_matching(stored)
    assert profile["resumen"]["meses_experiencia"] == 48
    assert profile["resumen"]["terminos_busqueda"] == ["Soporte Cloud"]


def test_persisted_offers_are_recomputed_before_filter_and_opt_in_preserves_detail():
    rows = [dict(job("5 años de experiencia en AWS."), id="legacy", puntaje=95, match_breakdown={},
                 first_seen=datetime.now(timezone.utc).isoformat())]

    class Storage:
        def select(self, table, params):
            if table == "profiles":
                return [{"profile_data": construir_perfil_desde_texto(CV), "cv_text": CV}]
            return rows if table == "jobs" else []

        def update(self, table, values, params):
            assert params["user_id"] == "eq.fixture"
            rows[0].update(values)

    repository = Repository.__new__(Repository)
    repository.ctx = SimpleNamespace(user_id="fixture")
    repository.db = Storage()
    assert not repository.jobs(min_score=40)
    assert rows[0]["puntaje"] == 0
    assert repository.jobs(min_score=40, include_experience_gaps=True)[0]["experience_blocked"]
