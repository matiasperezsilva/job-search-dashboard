
from datetime import date
from jobsearch.services.cv_profile import _experiencia_por_fechas, construir_perfil_desde_texto
from jobsearch.services.scoring import evaluar_oferta


BERNARDITA_EXPERIENCE = """
EXPERIENCIA
QA Tester & Automatización Ene 2025 - Abr 2025
KIS Chile Santiago, Chile
Participé en migración de plataforma web, casos de prueba, Jira, UAT y Burp Suite.
Full Stack Developer - Proyecto de Título Jul 2024 - Dic 2024
Duoc UC Santiago, Chile
Desarrollé una aplicación web full stack.
EDUCACIÓN Y FORMACIÓN
Ingeniería en Informática 2020 - 2024
"""


def test_date_ranges_count_professional_months_and_exclude_academic_project():
    exp = _experiencia_por_fechas(BERNARDITA_EXPERIENCE, today=date(2026, 9, 1))
    assert exp["meses"] == 4
    assert exp["anos"] == 0.33
    assert len(exp["periodos_academicos_excluidos"]) == 1
    assert "Proyecto de Título" in exp["periodos_academicos_excluidos"][0]["etiqueta"]


def test_generic_quality_phrase_does_not_create_industrial_area_without_context():
    profile = construir_perfil_desde_texto(
        "QA Tester Ingeniera en Informática con experiencia en aseguramiento de calidad, "
        "testing web, Jira, Selenium, casos de prueba, APIs REST y SQL."
    )
    assert "QA / Testing" in profile["resumen"]["areas_detectadas"]
    assert "Minería / Calidad industrial" not in profile["resumen"]["areas_detectadas"]


def test_visible_modality_penalty_always_reduces_score_below_100():
    profile = {
        "areas": {
            "QA / Testing": {
                "titulo": ["analista qa", "qa tester"],
                "skills": ["postman", "selenium", "jira", "testing", "sql"],
                "peso": 1.30,
                "nivel": "intermedio",
            }
        },
        "resumen": {"anos_experiencia": 4},
        "preferencias": {"modalidades": ["remoto"], "ubicaciones": [], "renta_minima": None},
        "penalizaciones": {"senioridad": [], "ingles_avanzado": []},
    }
    job = {
        "titulo": "Analista QA Tester",
        "descripcion": "Testing Postman Selenium Jira SQL. 3 años de experiencia.",
        "modalidad": "Presencial",
        "link": "https://example.com/job/qa-100",
        "fuente": "Test",
    }
    result = evaluar_oferta(job, profile)
    modality = next(c for c in result["match_breakdown"]["components"] if c["label"] == "Modalidad")
    assert modality["value"] == -8
    assert result["match_breakdown"]["positive_score"] == 100
    assert result["match_breakdown"]["penalties_total"] == -8
    assert result["puntaje"] == 92


def test_professional_header_prioritizes_qa_over_academic_development_project():
    text = """
    Bernardita Muñoz
    QA Analyst | QA Tester | Ingeniera en Informática
    PERFIL PROFESIONAL
    QA Tester con experiencia en testing web, Selenium, Jira y casos de prueba.
    EXPERIENCIA
    QA Tester & Automatización Ene 2025 - Abr 2025
    Testing, Jira, Selenium.
    Full Stack Developer - Proyecto de Título Jul 2024 - Dic 2024
    JavaScript Node.js SQL Git.
    EDUCACIÓN Y FORMACIÓN
    Ingeniería en Informática 2020 - 2024
    """
    profile = construir_perfil_desde_texto(text)
    assert profile["resumen"]["areas_detectadas"][0] == "QA / Testing"
