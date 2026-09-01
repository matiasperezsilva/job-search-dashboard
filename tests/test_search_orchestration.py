import unittest
from unittest.mock import patch

from backend.main import _execute_search
from backend.supabase_rest import UserContext


class FakeRepository:
    instances = []

    def __init__(self, ctx):
        self.ctx = ctx
        self.updates = []
        self.saved = []
        FakeRepository.instances.append(self)

    def profile(self):
        return {"profile_data": {"areas": {}, "penalizaciones": {}}}

    def update_search_run(self, run_id, values):
        self.updates.append((run_id, values))
        return [values]

    def save_jobs(self, jobs, profile, evaluator):
        self.saved.extend(jobs)
        return len(jobs)


def fake_recolectar(sources, terms, headless, mode, progress, on_source_result=None):
    progress({"tipo": "fuente", "fuente": "GetOnBoard", "indice": 1, "total": 1, "mensaje": "Consultando GetOnBoard…"})
    jobs = [{"titulo": "QA Junior", "descripcion": "software testing", "fuente": "GetOnBoard", "link": "https://www.getonbrd.com/jobs/sysadmin-devops-qa/qa-junior-x"}]
    if on_source_result:
        on_source_result("GetOnBoard", jobs)
    progress({"tipo": "resultado_fuente", "fuente": "GetOnBoard", "mensaje": "GetOnBoard: 1 vacante relevante", "estadistica": {"fuente": "GetOnBoard", "cantidad": 1, "segundos": 1.2, "ok": True}})
    return (jobs, [], [{"fuente": "GetOnBoard", "cantidad": 1, "segundos": 1.2, "ok": True}])


class SearchOrchestrationTests(unittest.TestCase):
    def setUp(self):
        FakeRepository.instances.clear()

    @patch("backend.main.Repository", FakeRepository)
    @patch("backend.main.recolectar", fake_recolectar)
    @patch("backend.main.evaluar_oferta", lambda job, profile: {"puntaje": 70, "area": "QA / Testing", "razon": "ok"})
    def test_background_search_persists_progress_and_result(self):
        ctx = UserContext(token="token", user_id="user")
        _execute_search(ctx, "run-1", ["GetOnBoard"], ["qa software"], "rapida")
        repo = FakeRepository.instances[-1]
        self.assertEqual(len(repo.saved), 1)
        final = repo.updates[-1][1]
        self.assertEqual(final["status"], "completed")
        self.assertEqual(final["result"]["found"], 1)
        states = final["progress"]["source_states"]
        self.assertEqual(states["GetOnBoard"]["status"], "completed")
        self.assertEqual(states["GetOnBoard"]["cantidad"], 1)


if __name__ == "__main__":
    unittest.main()
