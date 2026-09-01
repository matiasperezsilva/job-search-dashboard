
from bs4 import BeautifulSoup

from jobsearch.scrapers import laborum, trabajando, bne


def test_trabajando_slug_matches_public_search_route():
    assert trabajando._slug("Analista QA") == "analista-qa"
    assert trabajando._slug("QA") == "qa"


def test_laborum_api_job_normalizes_public_record():
    raw = {
        "jobId": "1118319239",
        "title": "Ingeniero Informático",
        "company": {"name": "Acme"},
        "location": {"name": "Santiago"},
        "workModality": "Híbrido",
        "datePosted": "2026-08-30",
        "jobUrl": "https://www.laborum.cl/empleos/ingeniero-informatico-1118319239.html",
        "description": "<p>Python, SQL y APIs.</p>",
    }
    job = laborum._api_job(raw)
    assert job["titulo"] == "Ingeniero Informático"
    assert job["empresa"] == "Acme"
    assert "Santiago" in job["modalidad"]
    assert job["published_at"] == "2026-08-30"
    assert "Python" in job["descripcion"]


def test_laborum_detects_job_objects_flexibly():
    assert laborum._looks_like_job({"title":"QA","jobId":"123"}) is True
    assert laborum._looks_like_job({"titulo":"QA","url":"/empleos/qa-123.html"}) is True
    assert laborum._looks_like_job({"foo":"bar"}) is False


def test_bne_text_after_label_handles_public_detail_shape():
    doc = BeautifulSoup("""
      <article>
        <h1>Analista QA</h1>
        <p>Empresa: USERCODE SPA</p>
        <p>Tipo de contrato: Mixta (Teletrabajo + Presencial)</p>
      </article>
    """, "html.parser")
    assert "USERCODE" in bne._text_after_label(doc, "Empresa")
    assert "Mixta" in bne._text_after_label(doc, "Tipo de contrato")


def test_bne_offer_link_pattern_supports_internal_and_external():
    import re
    assert re.search(r"/(?:oferta|ofertaEmpleoExterno)/[^/?#]+", "https://www.bne.cl/oferta/2026-094270")
    assert re.search(r"/(?:oferta|ofertaEmpleoExterno)/[^/?#]+", "https://www.bne.cl/ofertaEmpleoExterno/8360362")
