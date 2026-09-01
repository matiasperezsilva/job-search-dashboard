
from datetime import datetime, timezone, timedelta

from backend.repository import canonical_signature, _is_old


def test_canonical_signature_matches_same_title_company_across_sources():
    a={"titulo":"Analista QA","empresa":"Acme","fuente":"LinkedIn"}
    b={"titulo":"Analista QA","empresa":"ACME","fuente":"Computrabajo"}
    assert canonical_signature(a)==canonical_signature(b)


def test_canonical_signature_is_conservative_without_company():
    assert canonical_signature({"titulo":"Analista QA","empresa":"","fuente":"LinkedIn"})==""
    assert canonical_signature({"titulo":"Analista QA","empresa":"Empresa confidencial"})==""


def test_old_offer_uses_published_date():
    old=(datetime.now(timezone.utc)-timedelta(days=40)).isoformat()
    recent=(datetime.now(timezone.utc)-timedelta(days=5)).isoformat()
    assert _is_old({"published_at":old}) is True
    assert _is_old({"published_at":recent}) is False


def test_old_offer_falls_back_to_first_seen():
    old=(datetime.now(timezone.utc)-timedelta(days=35)).isoformat()
    assert _is_old({"published_at":None,"first_seen":old}) is True


def test_offer_without_dates_is_not_assumed_old():
    assert _is_old({}) is False
