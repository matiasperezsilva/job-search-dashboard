
from types import SimpleNamespace

from backend.repository import Repository


class ApplicationDb:
    def __init__(self):
        self.deleted=[]
        self.upserts=[]

    def delete(self, table, params):
        self.deleted.append((table,params))
        return True

    def upsert(self, table, row, on_conflict):
        self.upserts.append((table,row,on_conflict))
        return [row]


def _repo():
    r=Repository.__new__(Repository)
    r.ctx=SimpleNamespace(user_id="user-1")
    r.db=ApplicationDb()
    return r


def test_delete_application_only_removes_tracking_record():
    r=_repo()
    assert r.delete_application("job-1") is True
    table,params=r.db.deleted[0]
    assert table=="applications"
    assert params["user_id"]=="eq.user-1"
    assert params["job_id"]=="eq.job-1"


def test_save_application_still_upserts_state_and_notes():
    r=_repo()
    r.save_application("job-1","Entrevista","Llamar el viernes")
    table,row,conflict=r.db.upserts[0]
    assert table=="applications"
    assert row["estado"]=="Entrevista"
    assert row["notas"]=="Llamar el viernes"
    assert conflict=="user_id,job_id"
