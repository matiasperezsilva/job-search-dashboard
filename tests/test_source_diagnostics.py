
from types import SimpleNamespace
from unittest.mock import patch

from jobsearch.services.collector import recolectar


def _job(title="Analista QA"):
    return {
        "titulo": title,
        "empresa": "Acme",
        "descripcion": "Testing QA Selenium Postman",
        "modalidad": "Remoto",
        "link": "https://example.com/job/1",
        "fuente": "Fake",
    }


class FakeModule:
    USES_BROWSER = False
    def __init__(self, offers, diag):
        self.offers = offers
        self.diag = diag
    def buscar_ofertas(self, browser=None, terminos=None, modo="rapida", progreso=None):
        return list(self.offers)
    def get_last_diagnostic(self):
        return dict(self.diag)


def _run(module):
    with patch("jobsearch.services.collector.importlib.import_module", return_value=module):
        return recolectar(["GetOnBoard"], ["analista qa"], True, "rapida")


def test_source_diagnostic_ok_when_relevant_jobs_exist():
    jobs, errors, stats = _run(FakeModule([_job()], {
        "links_found": 3, "offers_extracted": 1, "detail_errors": 0, "query_errors": 0, "blocked": False
    }))
    assert len(jobs) == 1
    assert not errors
    assert stats[0]["estado"] == "ok"
    assert stats[0]["links_found"] == 3


def test_source_diagnostic_no_links_is_not_reported_as_no_matching_jobs():
    jobs, errors, stats = _run(FakeModule([], {
        "links_found": 0, "offers_extracted": 0, "detail_errors": 0, "query_errors": 0, "blocked": False
    }))
    assert jobs == []
    assert stats[0]["estado"] == "no_links"
    assert "enlaces" in stats[0]["diagnostico"].lower()


def test_source_diagnostic_extract_error():
    jobs, errors, stats = _run(FakeModule([], {
        "links_found": 5, "offers_extracted": 0, "detail_errors": 5, "query_errors": 0, "blocked": False
    }))
    assert stats[0]["estado"] == "extract_error"
    assert stats[0]["detail_errors"] == 5


def test_source_diagnostic_blocked():
    jobs, errors, stats = _run(FakeModule([], {
        "links_found": 0, "offers_extracted": 0, "detail_errors": 0, "query_errors": 0, "blocked": True
    }))
    assert stats[0]["estado"] == "blocked"
    assert stats[0]["ok"] is False


def test_source_diagnostic_filtered_when_extracted_offer_does_not_match_terms():
    jobs, errors, stats = _run(FakeModule([_job("Contador Auditor")], {
        "links_found": 1, "offers_extracted": 1, "detail_errors": 0, "query_errors": 0, "blocked": False
    }))
    assert jobs == []
    assert stats[0]["estado"] == "filtered"
    assert stats[0]["filtered_count"] == 1


def test_failed_browser_does_not_prevent_http_portal():
    browser_adapter = SimpleNamespace(USES_BROWSER=True)
    http_adapter = FakeModule([_job()], {})
    with patch("jobsearch.services.collector.sync_playwright", side_effect=RuntimeError):
        with patch("jobsearch.services.collector.importlib.import_module", side_effect=[browser_adapter, http_adapter]):
            jobs, errors, stats = recolectar(["BNE", "GetOnBoard"], ["analista qa"])
    assert [item["estado"] for item in stats] == ["error", "ok"]
    assert errors[0]["fuente"] == "BNE"
    assert len(jobs) == 1


def test_database_failure_propagates_outside_portal_handling():
    from pytest import raises

    def fail_to_save(*_):
        raise RuntimeError("database unavailable")

    with patch("jobsearch.services.collector.importlib.import_module", return_value=FakeModule([_job()], {})):
        with raises(RuntimeError, match="database unavailable"):
            recolectar(["GetOnBoard"], ["analista qa"], on_source_result=fail_to_save)
