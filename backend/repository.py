from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
from datetime import datetime, timezone, timedelta
from backend.supabase_rest import SupabaseRest, UserContext, now_iso
from jobsearch.services.cv_profile import perfil_para_matching
from jobsearch.services.scoring import evaluar_oferta

logger = logging.getLogger(__name__)
MATCH_REVISION = "5.8.2"


def job_id(oferta):
    # Una publicación individual debe identificarse principalmente por su enlace.
    # El fallback mantiene compatibilidad con fuentes que no entreguen URL.
    link = str(oferta.get("link") or "").split("#", 1)[0].strip().lower()
    raw = link or "|".join(str(oferta.get(k, "")) for k in ("titulo", "empresa", "fuente"))
    return hashlib.sha1(raw.lower().strip().encode("utf-8")).hexdigest()[:16]


def _norm_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"\b(?:sr|jr|senior|junior)\.?\b", lambda m: m.group(0).lower(), value, flags=re.I)
    value = re.sub(r"[^a-zA-Z0-9]+", " ", value.lower())
    return re.sub(r"\s+", " ", value).strip()


def canonical_signature(job: dict) -> str:
    """Firma conservadora para agrupar la misma vacante publicada en varias fuentes.

    Solo usamos cargo + empresa. Si falta empresa no fusionamos: es preferible mostrar
    dos resultados a ocultar por error dos vacantes distintas.
    """
    title = _norm_text(job.get("titulo"))
    company = _norm_text(job.get("empresa"))
    if not title or not company or company in {"confidencial", "empresa confidencial", "sin informar"}:
        return ""
    return f"{title}|{company}"


def _parse_dt(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _is_old(job: dict, days: int = 30) -> bool:
    reference = _parse_dt(job.get("published_at")) or _parse_dt(job.get("first_seen"))
    if not reference:
        return False
    return datetime.now(timezone.utc) - reference > timedelta(days=days)


def source_snapshot_expired(job: dict) -> bool:
    if job.get("fuente") != "GetOnBoard":
        return False
    last_seen = _parse_dt(job.get("last_seen"))
    return not last_seen or datetime.now(timezone.utc) - last_seen >= timedelta(hours=24)


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
        current = self.profile()
        current_data = (current or {}).get("profile_data") or {}
        if current_data.get("preferencias") and not profile.get("preferencias"):
            profile["preferencias"] = current_data["preferencias"]
        current_summary = current_data.get("resumen") or {}
        if "cargos_configurados" in current_summary:
            profile["resumen"]["cargos_configurados"] = current_summary["cargos_configurados"]
            profile["resumen"]["terminos_busqueda"] = current_summary["cargos_configurados"]
        return self.db.upsert("profiles", {
            "user_id": self.ctx.user_id, "cv_name": cv_name, "cv_text": cv_text,
            "profile_data": profile, "updated_at": now_iso(),
        }, "user_id")

    def update_profile_preferences(self, preferences: dict):
        current = self.profile()
        if not current:
            raise ValueError("No hay currículum activo.")
        data = current.get("profile_data") or {}
        data["preferencias"] = preferences
        return self.db.update("profiles", {"profile_data": data, "updated_at": now_iso()}, {
            "user_id": f"eq.{self.ctx.user_id}"
        })

    def update_profile_terms(self, terms: list[str]):
        current = self.profile()
        if not current:
            raise ValueError("No hay currículum activo.")
        data = current.get("profile_data") or {}
        data.setdefault("resumen", {}).update(terminos_busqueda=terms, cargos_configurados=terms)
        return self.db.update("profiles", {"profile_data": data, "updated_at": now_iso()}, {
            "user_id": f"eq.{self.ctx.user_id}"
        })


    def create_search_run(self, mode: str, sources: list[str], terms: list[str]):
        rows = self.db.insert("search_runs", {
            "user_id": self.ctx.user_id, "status": "queued", "mode": mode,
            "sources": sources, "terms": terms, "progress": {"message": "Búsqueda en cola"},
            "updated_at": now_iso(),
        })
        return rows[0] if rows else None

    def search_run(self, run_id: str):
        rows = self.db.select("search_runs", {
            "select": "*", "user_id": f"eq.{self.ctx.user_id}", "id": f"eq.{run_id}", "limit": "1"
        })
        return self._expire_search_run(rows[0]) if rows else None

    def update_search_run(self, run_id: str, values: dict):
        values = {**values, "updated_at": now_iso()}
        return self.db.update("search_runs", values, {
            "user_id": f"eq.{self.ctx.user_id}", "id": f"eq.{run_id}",
            "status": "in.(queued,running)",
        })



    def active_search_run(self):
        rows = self.db.select("search_runs", {
            "select": "*", "user_id": f"eq.{self.ctx.user_id}",
            "status": "in.(queued,running)", "order": "created_at.desc", "limit": "1"
        })
        if not rows:
            return None
        run = self._expire_search_run(rows[0])
        return run if run["status"] in {"queued", "running"} else None

    def _expire_search_run(self, run: dict):
        updated = _parse_dt(run.get("updated_at"))
        if run["status"] not in {"queued", "running"} or not updated or datetime.now(timezone.utc) - updated <= timedelta(minutes=30):
            return run
        failed = {"status": "failed", "error": "La búsqueda se interrumpió. Puedes iniciar otra."}
        rows = self.db.update("search_runs", {**failed, "updated_at": now_iso()}, {
            "user_id": f"eq.{self.ctx.user_id}", "id": f"eq.{run['id']}",
            "status": "in.(queued,running)", "updated_at": f"eq.{run['updated_at']}",
        })
        return rows[0] if rows else run

    @staticmethod
    def _match_fields(job, profile, evaluator, revision):
        result = evaluator(job, profile)
        return {
            "puntaje": result["puntaje"], "area": result["area"], "razon": result["razon"],
            "match_breakdown": {**(result.get("match_breakdown") or {}), "revision": revision},
        }

    @staticmethod
    def match_revision(profile):
        return profile.get("_match_revision") or MATCH_REVISION

    def matching_profile(self, row):
        profile = perfil_para_matching(row)
        profile["_match_revision"] = f"{MATCH_REVISION}:{row.get('updated_at') or '-'}:{datetime.now(timezone.utc):%Y-%m}"
        return profile

    def _all_jobs(self, params):
        rows = []
        while True:
            page = self.db.select("jobs", {**params, "limit": "200", "offset": str(len(rows))})
            rows.extend(page)
            if len(page) < 200:
                return rows

    def _refresh_matches(self, jobs, profile, evaluator, *, force=False):
        updated = 0
        revision = self.match_revision(profile)
        for job in jobs:
            if not force and (job.get("match_breakdown") or {}).get("revision") == revision:
                continue
            fields = self._match_fields(job, profile, evaluator, revision)
            params = {"user_id": f"eq.{self.ctx.user_id}", "id": f"eq.{job['id']}"}
            if job.get("last_seen"):
                params["last_seen"] = f"eq.{job['last_seen']}"
            try:
                self.db.update("jobs", fields, params)
            except RuntimeError:
                if force:
                    raise
                logger.warning("No se pudo persistir el calce recalculado de una oferta.")
            job.update(fields)
            updated += 1
        return updated

    def save_jobs(self, jobs: list[dict], profile: dict, evaluator):
        existing = self.db.select("jobs", {"select": "id,link,first_seen,favorite,hidden,hidden_at,published_at", "user_id": f"eq.{self.ctx.user_id}"})
        by_id = {r["id"]: r for r in existing}
        by_link = {str(r.get("link") or "").split("#", 1)[0].strip().lower(): r for r in existing if r.get("link")}
        new_count = 0
        for job in jobs:
            normalized_link = str(job.get("link") or "").split("#", 1)[0].strip().lower()
            previous = by_link.get(normalized_link) if normalized_link else None
            jid = previous.get("id") if previous else job_id(job)
            fields = self._match_fields(job, profile, evaluator, self.match_revision(profile))
            row = {
                "id": jid, "user_id": self.ctx.user_id,
                "titulo": job.get("titulo", ""), "empresa": job.get("empresa", ""),
                "descripcion": job.get("descripcion", ""), "modalidad": job.get("modalidad", ""),
                "link": job.get("link", ""), "fuente": job.get("fuente", ""),
                **fields,
                "published_at": job.get("published_at") or by_id.get(jid, {}).get("published_at") or None,
                "favorite": bool(by_id.get(jid, {}).get("favorite", False)),
                "hidden": bool(by_id.get(jid, {}).get("hidden", False)),
                "hidden_at": by_id.get(jid, {}).get("hidden_at"),
                "first_seen": by_id.get(jid, {}).get("first_seen", now_iso()), "last_seen": now_iso(),
            }
            self.db.upsert("jobs", row, "user_id,id")
            if jid not in by_id:
                new_count += 1
        return new_count

    def jobs(self, min_score=0, source=None, state=None, search=None, favorite_only=False, include_hidden=False, only_hidden=False, sort="score", include_old=False, deduplicate=True, include_experience_gaps=False):
        params = {
            "select": "*", "user_id": f"eq.{self.ctx.user_id}",
            "order": "id.asc",
        }
        if only_hidden:
            params["hidden"] = "eq.true"
        elif not include_hidden:
            params["hidden"] = "eq.false"
        if favorite_only:
            params["favorite"] = "eq.true"
        if source:
            params["fuente"] = f"eq.{source}"
        jobs = self._all_jobs(params)
        row = self.profile()
        if row:
            self._refresh_matches(jobs, self.matching_profile(row), evaluar_oferta)
        apps = self.db.select("applications", {
            "select": "job_id,estado,notas", "user_id": f"eq.{self.ctx.user_id}"
        })
        by_job = {a["job_id"]: a for a in apps}
        out = []
        q = (search or "").lower().strip()
        for job in jobs:
            blocked = bool((job.get("match_breakdown") or {}).get("experience_blocked"))
            if blocked and not include_experience_gaps:
                continue
            if not blocked and int(job.get("puntaje") or 0) < min_score:
                continue
            app = by_job.get(job["id"], {})
            job["experience_blocked"] = blocked
            job["estado"] = app.get("estado", "Sin gestionar")
            job["notas"] = app.get("notas", "")
            if state and job["estado"] != state:
                continue
            if q and q not in f"{job.get('titulo','')} {job.get('empresa','')}".lower():
                continue
            job["is_old"] = _is_old(job)
            if not include_old and job["is_old"] and job.get("estado") == "Sin gestionar" and not job.get("favorite"):
                continue
            if source_snapshot_expired(job):
                if not app and not job.get("favorite") and not job.get("hidden"):
                    continue
                job.update(
                    titulo="Oferta guardada en Get on Board", empresa="", modalidad="", descripcion="",
                    razon="Consulta la publicación original para ver la información vigente.",
                    match_breakdown={}, source_snapshot_expired=True,
                )
            out.append(job)

        if deduplicate:
            grouped = {}
            passthrough = []
            for job in out:
                sig = canonical_signature(job)
                if not sig:
                    passthrough.append(job)
                    continue
                current = grouped.get(sig)
                if not current:
                    clone = dict(job)
                    clone["duplicate_sources"] = [job.get("fuente")] if job.get("fuente") else []
                    clone["duplicate_count"] = 1
                    grouped[sig] = clone
                    continue

                # Solo fusionar publicaciones razonablemente cercanas en el tiempo.
                a = _parse_dt(current.get("published_at")) or _parse_dt(current.get("first_seen"))
                b = _parse_dt(job.get("published_at")) or _parse_dt(job.get("first_seen"))
                close_enough = True
                if a and b:
                    close_enough = abs(a - b) <= timedelta(days=21)
                if not close_enough:
                    passthrough.append(job)
                    continue

                sources = list(dict.fromkeys((current.get("duplicate_sources") or []) + ([job.get("fuente")] if job.get("fuente") else [])))
                current["duplicate_sources"] = sources
                current["duplicate_count"] = int(current.get("duplicate_count") or 1) + 1

                # Conserva la representación más útil: mejor score, descripción y enlace.
                better = job if int(job.get("puntaje") or 0) > int(current.get("puntaje") or 0) else current
                if better is job:
                    keep_sources = sources
                    keep_count = current["duplicate_count"]
                    clone = dict(job)
                    clone["duplicate_sources"] = keep_sources
                    clone["duplicate_count"] = keep_count
                    grouped[sig] = clone
            out = list(grouped.values()) + passthrough

        if sort == "recent":
            out.sort(key=lambda j: (j.get("published_at") or j.get("first_seen") or ""), reverse=True)
        elif sort == "found":
            out.sort(key=lambda j: j.get("first_seen") or "", reverse=True)
        else:
            out.sort(key=lambda j: (int(j.get("puntaje") or 0), j.get("published_at") or j.get("last_seen") or ""), reverse=True)
        if include_experience_gaps:
            out.sort(key=lambda job: job["experience_blocked"])
        return out

    def job(self, job_id_: str):
        rows = self.db.select("jobs", {
            "select": "*", "user_id": f"eq.{self.ctx.user_id}", "id": f"eq.{job_id_}", "limit": "1",
        })
        return rows[0] if rows else None

    def update_job_flags(self, job_id_: str, favorite=None, hidden=None):
        values = {}
        if favorite is not None:
            values["favorite"] = bool(favorite)
        if hidden is not None:
            values["hidden"] = bool(hidden)
            values["hidden_at"] = now_iso() if hidden else None
        if not values:
            return []
        return self.db.update("jobs", values, {
            "user_id": f"eq.{self.ctx.user_id}", "id": f"eq.{job_id_}"
        })

    def save_application(self, job_id_: str, state: str, notes: str):
        return self.db.upsert("applications", {
            "user_id": self.ctx.user_id, "job_id": job_id_, "estado": state,
            "notas": notes, "updated_at": now_iso(),
        }, "user_id,job_id")


    def delete_application(self, job_id_: str):
        return self.db.delete("applications", {
            "user_id": f"eq.{self.ctx.user_id}",
            "job_id": f"eq.{job_id_}",
        })

    def letter(self, job_id_: str):
        rows = self.db.select("letters", {
            "select": "*", "user_id": f"eq.{self.ctx.user_id}", "job_id": f"eq.{job_id_}", "limit": "1"
        })
        return rows[0] if rows else None

    def save_letter(self, job_id_: str, content: str, mode: str):
        clean = (content or "").strip()
        if not clean:
            raise ValueError("El borrador está vacío.")
        if mode not in {"local", "inteligente"}:
            raise ValueError("Modo de carta no válido.")
        self.db.upsert("letters", {
            "user_id": self.ctx.user_id, "job_id": job_id_, "modo": mode,
            "contenido": clean, "updated_at": now_iso(),
        }, "user_id,job_id")
        # Verificación de persistencia: la API solo confirma éxito si puede releer
        # exactamente la carta del usuario autenticado.
        saved = self.letter(job_id_)
        if not saved or saved.get("contenido") != clean or saved.get("modo") != mode:
            raise RuntimeError("El borrador no pudo verificarse después de guardarlo.")
        return saved

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
        rows = self._all_jobs({"select": "*", "user_id": f"eq.{self.ctx.user_id}", "order": "id.asc"})
        updated = self._refresh_matches(rows, profile, evaluator, force=True)
        return {"updated": updated, "discarded": sum(bool(r["match_breakdown"].get("experience_blocked")) for r in rows)}
