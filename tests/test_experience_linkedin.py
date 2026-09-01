from jobsearch.services.cv_profile import construir_perfil_desde_texto, _requisito_experiencia
from jobsearch.services.scoring import evaluar_oferta
from jobsearch.scrapers.linkedin import _links, _detail

def test_cv_explicit_years_are_captured():
    p=construir_perfil_desde_texto("Analista QA con 3 años de experiencia en testing, Postman y Jira")
    assert p["resumen"]["anos_experiencia"] == 3

def test_job_required_years_are_parsed():
    assert _requisito_experiencia("Se requieren mínimo 5 años de experiencia en auditoría") == 5
    assert _requisito_experiencia("Experiencia de 2 a 4 años de experiencia en ventas") == 2

def test_experience_gap_penalizes_match():
    profile=construir_perfil_desde_texto("Analista QA con 2 años de experiencia en testing Postman Selenium Jira")
    job={"titulo":"Analista QA","descripcion":"Buscamos mínimo 5 años de experiencia. Postman Selenium Jira testing","modalidad":"","link":"https://example.com/job/1","fuente":"Test"}
    r=evaluar_oferta(job,profile)
    assert r["puntaje"] < 80
    assert "5 años" in r["razon"]

def test_linkedin_public_links_and_detail():
    listing='<a class="base-card__full-link" href="https://cl.linkedin.com/jobs/view/analista-qa-at-acme-1234567890?trk=x">Ver</a>'
    assert _links(listing)==["https://www.linkedin.com/jobs/view/1234567890"]
    detail='<h1 class="top-card-layout__title">Analista QA</h1><a class="topcard__org-name-link">Acme</a><div class="description__text">Testing API Postman</div>'
    o=_detail(detail,"https://www.linkedin.com/jobs/view/1234567890")
    assert o["titulo"]=="Analista QA" and o["empresa"]=="Acme"
