from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Annotated

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path: sys.path.insert(0, str(SRC))

from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
import requests

from backend.repository import Repository
from backend.supabase_rest import SupabaseRest, UserContext
from jobsearch.services.collector import recolectar
from jobsearch.services.cv_profile import construir_perfil_desde_texto, extraer_texto_cv
from jobsearch.services.letters import ConfigAPI, config_api_desde_entorno, generar_borrador_local, generar_carta_inteligente
from jobsearch.services.scoring import evaluar_oferta

app = FastAPI(title="Job Search API", version="4.0")


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

class SearchBody(BaseModel):
    sources: list[str]
    mode: str = "rapida"
    terms: list[str] | None = None

class ApplicationBody(BaseModel):
    state: str
    notes: str = ""

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
        r.save_profile(profile, text, file.filename or "curriculum")
        return {"ok": True, "cv_name": file.filename, "profile": profile}
    except ValueError as exc:
        raise HTTPException(400, str(exc))

@app.put("/profile/terms")
def update_terms(body: TermsBody, r: Repository = Depends(repo)):
    terms = list(dict.fromkeys(t.strip() for t in body.terms if t.strip()))[:16]
    r.update_profile_terms(terms)
    return {"ok": True, "terms": terms}

@app.post("/search")
async def search(body: SearchBody, r: Repository = Depends(repo)):
    row = r.profile()
    if not row:
        raise HTTPException(400, "Sube y activa un currículum antes de buscar.")
    profile = row.get("profile_data") or {}
    terms = body.terms or profile.get("resumen", {}).get("terminos_busqueda", [])
    allowed = {"GetOnBoard", "Computrabajo", "ChileTrabajos", "Laborum", "Trabajando.com", "BNE", "LinkedIn"}
    sources = [s for s in body.sources if s in allowed]
    if not sources:
        raise HTTPException(400, "Selecciona al menos una fuente.")
    try:
        jobs, errors, stats = await run_in_threadpool(recolectar, sources, terms, True, body.mode, None)
        new_count = r.save_jobs(jobs, profile, evaluar_oferta)
        relevant = [j for j in jobs if evaluar_oferta(j, profile)["puntaje"] >= 30]
        return {"found": len(relevant), "new": new_count, "stats": stats, "errors": errors}
    except Exception as exc:
        raise HTTPException(500, f"La búsqueda no pudo completarse: {exc}")

@app.get("/jobs")
def jobs(
    min_score: int = Query(40, ge=0, le=100), source: str | None = None,
    state: str | None = None, q: str | None = None, r: Repository = Depends(repo)
):
    return {"items": r.jobs(min_score, source, state, q)}

@app.post("/jobs/reevaluate")
def reevaluate(r: Repository = Depends(repo)):
    row = r.profile()
    if not row:
        raise HTTPException(400, "No hay currículum activo.")
    return r.reevaluate(row.get("profile_data") or {}, evaluar_oferta)

@app.put("/jobs/{job_id}/application")
def save_application(job_id: str, body: ApplicationBody, r: Repository = Depends(repo)):
    r.save_application(job_id, body.state, body.notes)
    return {"ok": True}

@app.get("/jobs/{job_id}/letter")
def get_letter(job_id: str, r: Repository = Depends(repo)):
    return r.letter(job_id) or {"contenido": "", "modo": "local"}

@app.post("/jobs/{job_id}/letter/generate")
def generate_letter(job_id: str, body: LetterGenerateBody, r: Repository = Depends(repo)):
    jobs = [j for j in r.jobs(0) if j["id"] == job_id]
    if not jobs: raise HTTPException(404, "Oferta no encontrada")
    row = r.profile()
    if not row: raise HTTPException(400, "No hay currículum activo")
    job, profile, cv = jobs[0], row.get("profile_data") or {}, row.get("cv_text") or ""
    if body.mode == "inteligente":
        cfg = None
        if body.api_base_url and body.api_key and body.api_model:
            cfg = ConfigAPI(body.api_base_url, body.api_key, body.api_model)
        else:
            cfg = config_api_desde_entorno()
        if not cfg: raise HTTPException(400, "Configura una API compatible para generación inteligente.")
        content = generar_carta_inteligente(job, profile, cv, cfg)
    else:
        content = generar_borrador_local(job, profile)
    return {"content": content, "mode": body.mode}

@app.put("/jobs/{job_id}/letter")
def save_letter(job_id: str, body: LetterSaveBody, r: Repository = Depends(repo)):
    r.save_letter(job_id, body.content, body.mode)
    return {"ok": True}
