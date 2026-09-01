from __future__ import annotations

import hashlib
from backend.supabase_rest import SupabaseRest, UserContext, now_iso


def job_id(oferta):
    raw = "|".join(str(oferta.get(k, "")) for k in ("titulo", "empresa", "fuente"))
    return hashlib.sha1(raw.lower().strip().encode("utf-8")).hexdigest()[:16]


class Repository:
    def __init__(self, ctx: UserContext):
        self.ctx = ctx
        self.db = SupabaseRest(ctx.token)

    def profile(self):
        rows = self.db.select("profiles", {
            "select": "*", "user_id": f"eq.{self.ctx.user_id}", "limit": "1"
        })
        return rows[0] if rows else None

    def save_profile(self, profile: dict, cv_text: str, cv_name: str):
        return self.db.upsert("profiles", {
            "user_id": self.ctx.user_id, "cv_name": cv_name, "cv_text": cv_text,
            "profile_data": profile, "updated_at": now_iso(),
        }, "user_id")

    def update_profile_terms(self, terms: list[str]):
        current = self.profile()
        if not current:
            raise ValueError("No hay currículum activo.")
        data = current.get("profile_data") or {}
        data.setdefault("resumen", {})["terminos_busqueda"] = terms
        return self.db.update("profiles", {"profile_data": data, "updated_at": now_iso()}, {
            "user_id": f"eq.{self.ctx.user_id}"
        })

    def save_jobs(self, jobs: list[dict], profile: dict, evaluator):
        existing = self.db.select("jobs", {"select": "id,first_seen", "user_id": f"eq.{self.ctx.user_id}"})
        by_id = {r["id"]: r for r in existing}
        new_count = 0
        for job in jobs:
            jid = job_id(job)
            ev = evaluator(job, profile)
            row = {
                "id": jid, "user_id": self.ctx.user_id,
                "titulo": job.get("titulo", ""), "empresa": job.get("empresa", ""),
                "descripcion": job.get("descripcion", ""), "modalidad": job.get("modalidad", ""),
                "link": job.get("link", ""), "fuente": job.get("fuente", ""),
                "puntaje": ev["puntaje"], "area": ev["area"], "razon": ev["razon"],
                "first_seen": by_id.get(jid, {}).get("first_seen", now_iso()), "last_seen": now_iso(),
            }
            self.db.upsert("jobs", row, "user_id,id")
            if jid not in by_id:
                new_count += 1
        return new_count

    def jobs(self, min_score=0, source=None, state=None, search=None):
        params = {
            "select": "*", "user_id": f"eq.{self.ctx.user_id}",
            "puntaje": f"gte.{int(min_score)}", "order": "puntaje.desc,last_seen.desc",
        }
        if source:
            params["fuente"] = f"eq.{source}"
        jobs = self.db.select("jobs", params)
        apps = self.db.select("applications", {
            "select": "job_id,estado,notas", "user_id": f"eq.{self.ctx.user_id}"
        })
        by_job = {a["job_id"]: a for a in apps}
        out = []
        q = (search or "").lower().strip()
        for job in jobs:
            app = by_job.get(job["id"], {})
            job["estado"] = app.get("estado", "Sin gestionar")
            job["notas"] = app.get("notas", "")
            if state and job["estado"] != state:
                continue
            if q and q not in f"{job.get('titulo','')} {job.get('empresa','')}".lower():
                continue
            out.append(job)
        return out

    def save_application(self, job_id_: str, state: str, notes: str):
        return self.db.upsert("applications", {
            "user_id": self.ctx.user_id, "job_id": job_id_, "estado": state,
            "notas": notes, "updated_at": now_iso(),
        }, "user_id,job_id")

    def letter(self, job_id_: str):
        rows = self.db.select("letters", {
            "select": "*", "user_id": f"eq.{self.ctx.user_id}", "job_id": f"eq.{job_id_}", "limit": "1"
        })
        return rows[0] if rows else None

    def save_letter(self, job_id_: str, content: str, mode: str):
        return self.db.upsert("letters", {
            "user_id": self.ctx.user_id, "job_id": job_id_, "modo": mode,
            "contenido": content, "updated_at": now_iso(),
        }, "user_id,job_id")

    def dashboard(self):
        rows = self.jobs(0)
        sources = {}
        for row in rows:
            src = row.get("fuente") or "Sin fuente"
            sources[src] = sources.get(src, 0) + 1
        return {
            "total": len(rows), "top": sum(r["puntaje"] >= 70 for r in rows),
            "postuladas": sum(r["estado"] == "Postulada" for r in rows),
            "entrevistas": sum(r["estado"] == "Entrevista" for r in rows),
            "sources": [{"name": k, "count": v} for k, v in sorted(sources.items(), key=lambda x: x[1], reverse=True)],
            "recent": rows[:6],
        }

    def reevaluate(self, profile: dict, evaluator):
        rows = self.db.select("jobs", {"select": "*", "user_id": f"eq.{self.ctx.user_id}"})
        discarded = 0
        for job in rows:
            ev = evaluator(job, profile)
            self.db.update("jobs", {"puntaje": ev["puntaje"], "area": ev["area"], "razon": ev["razon"]}, {
                "user_id": f"eq.{self.ctx.user_id}", "id": f"eq.{job['id']}"
            })
            if ev["puntaje"] < 30:
                discarded += 1
        return {"updated": len(rows), "discarded": discarded}
