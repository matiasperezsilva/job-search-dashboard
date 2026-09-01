
from types import SimpleNamespace
import pytest

from backend.repository import Repository


class LetterDb:
    def __init__(self):
        self.rows = {}
        self.upserts = []

    def upsert(self, table, row, on_conflict):
        assert table == "letters"
        key = (row["user_id"], row["job_id"])
        self.rows[key] = dict(row)
        self.upserts.append((table, dict(row), on_conflict))
        return [dict(row)]

    def select(self, table, params=None):
        if table != "letters":
            return []
        uid = (params.get("user_id") or "").removeprefix("eq.")
        jid = (params.get("job_id") or "").removeprefix("eq.")
        row = self.rows.get((uid, jid))
        return [dict(row)] if row else []


def _repo():
    repo = Repository.__new__(Repository)
    repo.ctx = SimpleNamespace(user_id="user-1")
    repo.db = LetterDb()
    return repo


def test_save_letter_persists_and_verifies_content():
    repo = _repo()
    saved = repo.save_letter("job-1", "  Mi carta de presentación  ", "inteligente")
    assert saved["contenido"] == "Mi carta de presentación"
    assert saved["modo"] == "inteligente"
    loaded = repo.letter("job-1")
    assert loaded["contenido"] == "Mi carta de presentación"


def test_save_letter_rejects_empty_content():
    repo = _repo()
    with pytest.raises(ValueError, match="vacío"):
        repo.save_letter("job-1", "   ", "local")


def test_save_letter_rejects_unknown_mode():
    repo = _repo()
    with pytest.raises(ValueError, match="Modo"):
        repo.save_letter("job-1", "Carta", "desconocido")
