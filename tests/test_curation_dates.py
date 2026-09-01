from types import SimpleNamespace

from backend.repository import Repository
from jobsearch.scrapers.http_common import date_posted


def test_date_posted_accepts_iso_and_rejects_noise():
    assert date_posted({"datePosted": "2026-08-31"}) == "2026-08-31"
    assert date_posted({"datePosted": "2026-08-31T10:30:00-04:00"}).startswith("2026-08-31T10:30:00")
    assert date_posted({"datePosted": "hace 2 días"}) == ""
    assert date_posted({}) == ""


class FakeDb:
    def __init__(self):
        self.upserts=[]
        self.updated=[]

    def select(self, table, params=None):
        if table == "jobs" and params and params.get("select", "").startswith("id,link"):
            return [{
                "id": "same",
                "link": "https://example.com/job",
                "first_seen": "2026-08-20T12:00:00+00:00",
                "favorite": True,
                "hidden": True,
                "hidden_at": "2026-08-21T12:00:00+00:00",
                "published_at": "2026-08-19T12:00:00+00:00",
            }]
        return []

    def upsert(self, table, row, on_conflict):
        self.upserts.append((table,row,on_conflict))
        return [row]

    def update(self, table, values, params):
        self.updated.append((table,values,params))
        return [values]


def test_hidden_and_favorite_survive_future_scrape(monkeypatch):
    repo = Repository.__new__(Repository)
    repo.ctx = SimpleNamespace(user_id="user-1")
    repo.db = FakeDb()

    # Force the same existing ID so this test targets persistence behavior.
    monkeypatch.setattr("backend.repository.job_id", lambda _: "same")
    evaluator=lambda job,profile: {"puntaje":80,"area":"QA","razon":"ok","match_breakdown":{}}
    repo.save_jobs([{
        "titulo":"Analista QA",
        "empresa":"Acme",
        "descripcion":"Testing",
        "modalidad":"Remoto",
        "link":"https://example.com/job",
        "fuente":"Test",
        "published_at":"",
    }], {}, evaluator)

    row=repo.db.upserts[0][1]
    assert row["favorite"] is True
    assert row["hidden"] is True
    assert row["hidden_at"] == "2026-08-21T12:00:00+00:00"
    assert row["published_at"] == "2026-08-19T12:00:00+00:00"


def test_restore_clears_hidden_at():
    repo = Repository.__new__(Repository)
    repo.ctx = SimpleNamespace(user_id="user-1")
    repo.db = FakeDb()
    repo.update_job_flags("job-1", hidden=False)
    values=repo.db.updated[0][1]
    assert values["hidden"] is False
    assert values["hidden_at"] is None


def test_job_identity_prefers_individual_link():
    from backend.repository import job_id
    base={"titulo":"Analista QA","empresa":"Acme","fuente":"LinkedIn"}
    a={**base,"link":"https://www.linkedin.com/jobs/view/111"}
    b={**base,"link":"https://www.linkedin.com/jobs/view/222"}
    assert job_id(a) != job_id(b)
