from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path: sys.path.insert(0, str(SRC))

from fastapi import BackgroundTasks, Depends, FastAPI, File, Header, HTTPException, Query, UploadFile
from pydantic import BaseModel

from backend.repository import Repository
from backend.supabase_rest import SupabaseRest, UserContext
from jobsearch.services.collector import recolectar
from jobsearch.services.cv_profile import construir_perfil_desde_texto, extraer_texto_cv
from jobsearch.services.profile_ai import enriquecer_perfil_con_gemini
from jobsearch.services.letters import ConfigAPI, config_api_desde_entorno, config_gemini_desde_entorno, generar_borrador_local, generar_carta_gemini, generar_carta_inteligente
from jobsearch.services.scoring import evaluar_oferta

app = FastAPI(title="Job Search API", version="5.6")


def auth_context(authorization: Annotated[str | None, Header()] = None) -> UserContext:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Sesión requerida")
    token = authorization.split(" ", 1)[1].strip()
    try:
        return SupabaseRest(token).verify_user()
    except Exception:
        raise HTTPException(401, "Sesión inválida o expirada")


def repo(ctx: UserContext = Depends(auth_context)):
    return Repository(ctx)


class TermsBody(BaseModel):
    terms: list[str]

class PreferencesBody(BaseModel):
    modalidades: list[str] = []
    ubicaciones: list[str] = []
    renta_minima: int | None = None
    moneda: str = "CLP"


class SearchBody(BaseModel):
    sources: list[str]
    mode: str = "rapida"
    terms: list[str] | None = None

class ApplicationBody(BaseModel):
    state: str
    notes: str = ""

class JobFlagsBody(BaseModel):
    favorite: bool | None = None
    hidden: bool | None = None

class LetterGenerateBody(BaseModel):
    mode: str = "local"
    api_base_url: str | None = None
    api_key: str | None = None
    api_model: str | None = None

class LetterSaveBody(BaseModel):
    content: str
    mode: str = "local"


@app.get("/health")
def health():
    return {"ok": True, "frontend": "nextjs", "backend": "fastapi"}

@app.get("/me")
def me(ctx: UserContext = Depends(auth_context)):
    return {"id": ctx.user_id, "email": ctx.email}

@app.get("/settings/ai")
def ai_settings():
    cfg = config_gemini_desde_entorno()
    return {
        "configured": bool(cfg),
        "provider": "Gemini" if cfg else None,
        "model": cfg.model if cfg else None,
    }

@app.get("/dashboard")
def dashboard(r: Repository = Depends(repo)):
    return r.dashboard()

@app.get("/profile")
def profile(r: Repository = Depends(repo)):
    row = r.profile()
    if not row:
        return {"active": False}
    data = row.get("profile_data") or {}
    return {"active": True, "cv_name": row.get("cv_name", ""), "profile": data}

@app.post("/profile/upload")
async def upload_profile(file: UploadFile = File(...), r: Repository = Depends(repo)):
    content = await file.read()
    try:
        text = extraer_texto_cv(file.filename or "cv.pdf", content)
        if len(text.strip()) < 80:
            raise ValueError("El currículum no contiene suficiente texto legible.")
        profile = construir_perfil_desde_texto(text)
        gemini = config_gemini_desde_entorno()
        if gemini:
            profile = enriquecer_perfil_con_gemini(text, profile, gemini)
        r.save_profile(profile, text, file.filename or "curriculum")
        return {"ok": True, "cv_name": file.filename, "profile": profile}
    except ValueError as exc:
        raise HTTPException(400, str(exc))

@app.put("/profile/terms")
def update_terms(body: TermsBody, r: Repository = Depends(repo)):
    terms = list(dict.fromkeys(t.strip() for t in body.terms if t.strip()))[:16]
    r.update_profile_terms(terms)
    return {"ok": True, "terms": terms}


@app.put("/profile/preferences")
def update_preferences(body: PreferencesBody, r: Repository = Depends(repo)):
    modalidades_validas = {"remoto", "híbrido", "presencial"}
    modalidades = list(dict.fromkeys(
        x.strip().lower() for x in body.modalidades if x.strip().lower() in modalidades_validas
    ))
    ubicaciones = list(dict.fromkeys(x.strip() for x in body.ubicaciones if x.strip()))[:12]
    renta = body.renta_minima if body.renta_minima and body.renta_minima > 0 else None
    preferencias = {
        "modalidades": modalidades,
        "ubicaciones": ubicaciones,
        "renta_minima": renta,
        "moneda": (body.moneda or "CLP").upper(),
    }
    r.update_profile_preferences(preferencias)
    return {"ok": True, "preferencias": preferencias}

def _execute_search(ctx: UserContext, run_id: str, sources: list[str], terms: list[str], mode: str):
    r = Repository(ctx)
    row = r.profile()
    profile = (row or {}).get("profile_data") or {}
    progress_state = {"message": "Preparando búsqueda", "current_source": "", "source_index": 0, "source_total": len(sources), "source_states": {name: {"status": "pending"} for name in sources}}
    r.update_search_run(run_id, {"status": "running", "progress": progress_state})

    def progress(event):
        nonlocal progress_state
        if isinstance(event, dict):
            fuente = event.get("fuente")
            if event.get("mensaje"):
                progress_state["message"] = event.get("mensaje")
            if fuente:
                progress_state["current_source"] = fuente
            if event.get("indice") is not None:
                progress_state["source_index"] = event.get("indice")
            if event.get("total") is not None:
                progress_state["source_total"] = event.get("total")
            states = dict(progress_state.get("source_states") or {})
            if fuente and event.get("tipo") == "fuente":
                states[fuente] = {"status": "running"}
            if fuente and event.get("tipo") == "resultado_fuente":
                stat = event.get("estadistica") or {}
                states[fuente] = {
                    "status": "completed" if stat.get("ok") else "failed",
                    "cantidad": stat.get("cantidad", 0),
                    "segundos": stat.get("segundos", 0),
                }
            progress_state["source_states"] = states
        else:
            progress_state["message"] = str(event)
        try:
            r.update_search_run(run_id, {"progress": progress_state})
        except Exception:
            pass

    try:
        new_count = 0

        def persist_source(_source, source_jobs):
            nonlocal new_count
            if source_jobs:
                new_count += r.save_jobs(source_jobs, profile, evaluar_oferta)

        jobs, errors, stats = recolectar(sources, terms, True, mode, progress, persist_source)
        relevant = [j for j in jobs if evaluar_oferta(j, profile)["puntaje"] >= 30]
        result = {"found": len(relevant), "new": new_count, "stats": stats, "errors": errors}
        r.update_search_run(run_id, {"status": "completed", "result": result, "progress": {**progress_state, "message": "Búsqueda finalizada"}})
    except Exception as exc:
        r.update_search_run(run_id, {"status": "failed", "error": str(exc), "progress": {**progress_state, "message": "La búsqueda se interrumpió"}})


@app.post("/search")
def search(body: SearchBody, background_tasks: BackgroundTasks, ctx: UserContext = Depends(auth_context)):
    r = Repository(ctx)
    active = r.active_search_run()
    if active:
        return {"run_id": active["id"], "status": active["status"], "reused": True}
    row = r.profile()
    if not row:
        raise HTTPException(400, "Sube y activa un currículum antes de buscar.")
    profile = row.get("profile_data") or {}
    terms = body.terms or profile.get("resumen", {}).get("terminos_busqueda", [])
    terms = list(dict.fromkeys(t.strip() for t in terms if t and t.strip()))[:12]
    allowed = {"GetOnBoard", "Computrabajo", "ChileTrabajos", "Laborum", "Trabajando.com", "BNE", "LinkedIn"}
    sources = [s for s in body.sources if s in allowed]
    if not sources:
        raise HTTPException(400, "Selecciona al menos una fuente.")
    run = r.create_search_run(body.mode, sources, terms)
    if not run:
        raise HTTPException(500, "No se pudo crear la corrida de búsqueda.")
    run_id = run["id"]
    background_tasks.add_task(_execute_search, ctx, run_id, sources, terms, body.mode)
    return {"run_id": run_id, "status": "queued"}


@app.get("/search/active")
def active_search(r: Repository = Depends(repo)):
    return r.active_search_run() or {}


@app.get("/search/{run_id}")
def search_status(run_id: str, r: Repository = Depends(repo)):
    run = r.search_run(run_id)
    if not run:
        raise HTTPException(404, "Búsqueda no encontrada.")
    return run


@app.get("/jobs")
def jobs(
    min_score: int = Query(40, ge=0, le=100), source: str | None = None,
    state: str | None = None, q: str | None = None, favorite_only: bool = False,
    include_hidden: bool = False, only_hidden: bool = False, sort: str = "score",
    include_old: bool = False, deduplicate: bool = True,
    r: Repository = Depends(repo),
):
    return {"items": r.jobs(
        min_score, source, state, q, favorite_only, include_hidden, only_hidden,
        sort, include_old, deduplicate
    )}

@app.post("/jobs/reevaluate")
def reevaluate(r: Repository = Depends(repo)):
    row = r.profile()
    if not row:
        raise HTTPException(400, "No hay currículum activo.")
    return r.reevaluate(row.get("profile_data") or {}, evaluar_oferta)

@app.put("/jobs/{job_id}/flags")
def update_job_flags(job_id: str, body: JobFlagsBody, r: Repository = Depends(repo)):
    r.update_job_flags(job_id, body.favorite, body.hidden)
    return {"ok": True}

@app.put("/jobs/{job_id}/application")
def save_application(job_id: str, body: ApplicationBody, r: Repository = Depends(repo)):
    r.save_application(job_id, body.state, body.notes)
    return {"ok": True}

@app.get("/jobs/{job_id}/letter")
def get_letter(job_id: str, r: Repository = Depends(repo)):
    return r.letter(job_id) or {"contenido": "", "modo": "local"}

@app.post("/jobs/{job_id}/letter/generate")
def generate_letter(job_id: str, body: LetterGenerateBody, r: Repository = Depends(repo)):
    jobs = [j for j in r.jobs(0, include_hidden=True, include_old=True, deduplicate=False) if j["id"] == job_id]
    if not jobs: raise HTTPException(404, "Oferta no encontrada")
    row = r.profile()
    if not row: raise HTTPException(400, "No hay currículum activo")
    job, profile, cv = jobs[0], row.get("profile_data") or {}, row.get("cv_text") or ""
    if body.mode == "inteligente":
        try:
            gemini = config_gemini_desde_entorno()
            if gemini:
                content = generar_carta_gemini(job, profile, cv, gemini)
            else:
                # Compatibilidad con configuraciones genéricas anteriores.
                cfg = None
                if body.api_base_url and body.api_key and body.api_model:
                    cfg = ConfigAPI(body.api_base_url, body.api_key, body.api_model)
                else:
                    cfg = config_api_desde_entorno()
                if not cfg:
                    raise HTTPException(400, "La generación inteligente requiere GEMINI_API_KEY en Render.")
                content = generar_carta_inteligente(job, profile, cv, cfg)
        except HTTPException:
            raise
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(502, str(exc)) from exc
    else:
        content = generar_borrador_local(job, profile)
    return {"content": content, "mode": body.mode}

@app.put("/jobs/{job_id}/letter")
def save_letter(job_id: str, body: LetterSaveBody, r: Repository = Depends(repo)):
    r.save_letter(job_id, body.content, body.mode)
    return {"ok": True}
