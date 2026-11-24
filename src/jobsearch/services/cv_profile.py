from __future__ import annotations
from io import BytesIO
import json, re
from pathlib import Path
from datetime import date
from jobsearch.services.experience import _NOT_WORK, _TRAINING, _WORK, evidencias, requisitos

# Taxonomía deliberadamente transversal. No pretende adivinar una profesión por una
# sola palabra: combina títulos/funciones + competencias y deja los roles editables.
AREA_RULES = {
    "Tecnología / Software": {
        "roles": ["desarrollador", "developer", "software engineer", "programador", "frontend", "backend", "full stack", "analista de sistemas"],
        "skills": ["python", "java", "javascript", "typescript", "react", "node", "spring", "git", "github", "api", "sql"],
    },
    "QA / Testing": {
        "roles": ["analista qa", "qa analyst", "qa tester", "qa engineer", "tester software", "qa funcional", "qa automation", "sdet", "analista de pruebas"],
        "skills": ["postman", "selenium", "playwright", "cypress", "jmeter", "gherkin", "cucumber", "casos de prueba", "regresión", "testing", "jira"],
    },
    "Cloud / Operaciones": {
        "roles": ["cloud engineer", "cloud support", "soporte cloud", "devops", "sre", "cloud operations", "ingeniero cloud"],
        "skills": ["aws", "azure", "gcp", "ec2", "s3", "iam", "cloudwatch", "linux", "docker", "terraform", "kubernetes"],
    },
    "Soporte TI": {
        "roles": ["soporte ti", "soporte técnico", "service desk", "help desk", "mesa de ayuda", "support analyst"],
        "skills": ["active directory", "windows", "linux", "ticket", "incidentes", "office 365", "microsoft 365"],
    },
    "Datos / Analítica": {
        "roles": ["data analyst", "analista de datos", "data engineer", "business intelligence", "bi analyst", "científico de datos", "data scientist"],
        "skills": ["sql", "python", "power bi", "tableau", "excel", "etl", "pandas", "spark", "analytics"],
    },
    "Bases de datos": {
        "roles": ["dba", "database administrator", "administrador de base de datos", "administrador bases de datos"],
        "skills": ["sql server", "oracle", "postgresql", "mysql", "db2", "database", "base de datos"],
    },
    "Finanzas / Contabilidad": {
        "roles": ["contador", "contadora", "analista contable", "auditor", "auditora", "analista financiero", "tesorero", "tesorera"],
        "skills": ["contabilidad", "ifrs", "conciliación", "conciliaciones", "balance", "facturación", "tributario", "tesorería", "sap", "excel"],
    },
    "Administración / Operaciones": {
        "roles": ["administrativo", "administrativa", "analista de operaciones", "coordinador de operaciones", "asistente administrativo", "office manager"],
        "skills": ["excel", "gestión documental", "inventario", "proveedores", "operaciones", "erp", "reportes"],
    },
    "Recursos Humanos": {
        "roles": ["analista de recursos humanos", "reclutador", "recruiter", "talent acquisition", "generalista rrhh", "people analyst"],
        "skills": ["reclutamiento", "selección", "remuneraciones", "contratos", "onboarding", "recursos humanos", "rrhh"],
    },
    "Ventas / Comercial": {
        "roles": ["ejecutivo comercial", "ejecutiva comercial", "vendedor", "vendedora", "sales executive", "account manager", "key account manager", "business development"],
        "skills": ["ventas", "crm", "prospección", "negociación", "pipeline", "clientes", "salesforce"],
    },
    "Marketing / Comunicaciones": {
        "roles": ["marketing", "community manager", "content manager", "social media manager", "periodista", "comunicaciones", "growth marketer"],
        "skills": ["seo", "sem", "google analytics", "meta ads", "redes sociales", "contenido", "copywriting", "campañas"],
    },
    "Diseño / UX": {
        "roles": ["diseñador gráfico", "diseñadora gráfica", "ux designer", "ui designer", "product designer", "diseñador ux", "diseñadora ux"],
        "skills": ["figma", "photoshop", "illustrator", "adobe", "wireframe", "prototipo", "design system", "ux research"],
    },
    "Salud / Enfermería": {
        "roles": ["enfermero", "enfermera", "tens", "kinesiólogo", "kinesióloga", "matrona", "matrón", "terapeuta ocupacional"],
        "skills": ["pacientes", "urgencia", "uci", "upc", "hospital", "clínica", "clinica", "procedimientos", "salud"],
    },
    "Ingeniería / Construcción": {
        "roles": ["ingeniero civil", "ingeniera civil", "ingeniero de proyectos", "ingeniera de proyectos", "constructor civil", "constructora civil", "jefe de obra", "prevencionista"],
        "skills": ["autocad", "revit", "obra", "construcción", "proyectos", "planos", "prevención de riesgos", "primavera p6"],
    },
    "Minería / Calidad industrial": {
        "roles": ["ingeniero qa/qc", "ingeniera qa/qc", "supervisor qa/qc", "control de calidad", "aseguramiento de calidad", "inspector de calidad", "ingeniero de calidad"],
        "skills": ["minería", "faena", "iso 9001", "qa/qc", "inspección", "soldadura", "materiales", "haccp", "laboratorio", "manufactura"],
    },
    "Logística / Supply Chain": {
        "roles": ["analista logístico", "analista de logística", "supply chain", "encargado de bodega", "jefe de bodega", "planner", "comprador"],
        "skills": ["logística", "bodega", "inventario", "supply chain", "abastecimiento", "compras", "wms", "sap"],
    },
    "Educación": {
        "roles": ["profesor", "profesora", "docente", "educador", "educadora", "tutor", "tutora"],
        "skills": ["docencia", "aula", "planificación curricular", "evaluación", "estudiantes", "educación"],
    },
    "Legal": {
        "roles": ["abogado", "abogada", "procurador", "procuradora", "analista legal", "paralegal"],
        "skills": ["contratos", "jurídico", "juridico", "litigios", "compliance", "legal", "normativa"],
    },
}

GENERIC_SKILLS = sorted(set(s for cfg in AREA_RULES.values() for s in cfg["skills"]))
SENIOR_TERMS = ["senior", "sr.", "lead", "líder", "lider", "jefe", "manager", "director", "gerente", "arquitecto"]
ADVANCED_ENGLISH = ["english c1", "inglés c1", "advanced english", "inglés avanzado", "fluent english"]


def extraer_texto_cv(nombre: str, contenido: bytes) -> str:
    ext = Path(nombre).suffix.lower()
    if ext == ".pdf":
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError

        try:
            reader = PdfReader(BytesIO(contenido))
            if reader.is_encrypted or len(reader.pages) > 30:
                raise ValueError("Usa un PDF sin contraseña y de hasta 30 páginas.")
            return "\n".join((page.extract_text() or "") for page in reader.pages).strip()
        except PdfReadError as exc:
            raise ValueError("No se pudo leer el archivo PDF.") from exc
    if ext == ".docx":
        from zipfile import BadZipFile, ZipFile
        from docx import Document
        from docx.opc.exceptions import PackageNotFoundError
        from lxml.etree import XMLSyntaxError

        try:
            with ZipFile(BytesIO(contenido)) as archive:
                if sum(entry.file_size for entry in archive.infolist()) > 24 * 1024 * 1024:
                    raise ValueError("El contenido descomprimido del DOCX supera el límite permitido.")
            doc = Document(BytesIO(contenido))
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip()).strip()
        except (BadZipFile, PackageNotFoundError, KeyError, XMLSyntaxError) as exc:
            raise ValueError("No se pudo leer el archivo DOCX.") from exc
    if ext in {".txt", ".md"}: return contenido.decode("utf-8", errors="replace").strip()
    raise ValueError("Formato no soportado. Usa PDF, DOCX o TXT.")


def _norm(s: str) -> str: return re.sub(r"\s+", " ", (s or "").lower()).strip()
def _contiene(texto: str, termino: str) -> bool: return re.search(rf"(?<!\w){re.escape(_norm(termino))}(?!\w)", _norm(texto)) is not None


def _nivel(texto: str) -> str:
    low = _norm(texto)
    if any(x in low for x in ["gerente", "director", "head of", "10 años", "8 años"]): return "liderazgo"
    if any(x in low for x in ["senior", " sr ", "lead", "5 años", "6 años", "7 años"]): return "senior"
    if any(x in low for x in ["junior", "trainee", "práctica", "practica", "sin experiencia"]): return "junior"
    return "no especificado"



_MONTHS_ES = {
    "ene": 1, "enero": 1, "feb": 2, "febrero": 2, "mar": 3, "marzo": 3,
    "abr": 4, "abril": 4, "may": 5, "mayo": 5, "jun": 6, "junio": 6,
    "jul": 7, "julio": 7, "ago": 8, "agosto": 8, "sep": 9, "sept": 9,
    "septiembre": 9, "oct": 10, "octubre": 10, "nov": 11, "noviembre": 11,
    "dic": 12, "diciembre": 12,
}
def _month_index(year: int, month: int) -> int:
    return year * 12 + (month - 1)


def _merge_month_intervals(intervals):
    """Une intervalos [inicio, fin_exclusivo) para no duplicar experiencia superpuesta."""
    if not intervals:
        return []
    intervals = sorted(intervals)
    merged = [list(intervals[0])]
    for start, end in intervals[1:]:
        if start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [tuple(x) for x in merged]


def _experiencia_por_fechas(texto: str, today=None):
    """Estima experiencia profesional desde rangos de fechas del bloque EXPERIENCIA.

    Excluye explícitamente proyectos académicos/título/tesis y evita sumar periodos
    superpuestos. Devuelve None cuando no hay rangos laborales interpretables.
    """
    today = today or date.today()
    lines = (texto or "").splitlines()
    has_work_heading = any(_WORK.fullmatch(line) for line in lines)
    work = not has_work_heading
    names = "|".join(sorted(_MONTHS_ES, key=len, reverse=True))
    pattern = re.compile(
        rf"(?<!\d)(?P<m1>{names}|0?[1-9]|1[0-2])\.?[ /.-]+(?P<y1>(?:19|20)\d{{2}})"
        rf"\s*(?:[-–—]|a|hasta|to)\s*"
        rf"(?:(?P<m2>{names}|0?[1-9]|1[0-2])\.?[ /.-]+(?P<y2>(?:19|20)\d{{2}})|(?P<current>actualidad|actual|presente|present|actualmente))\b", re.I,
    )
    year_only = re.compile(r"(?<!\d)(?P<y1>(?:19|20)\d{2})\s*[-–—]\s*(?P<y2>(?:19|20)\d{2}|actualidad|actual|presente|present)\b", re.I)
    intervals, ignored, entries = [], [], []
    previous = ""
    active = None
    for line in lines:
        if _WORK.fullmatch(line):
            work, previous, active = True, "", None
            continue
        if _NOT_WORK.fullmatch(line):
            work, previous, active = False, "", None
            continue
        if not work or not line.strip():
            continue
        match = pattern.search(line)
        annual = year_only.search(line) if has_work_heading and not match else None
        if not match and not annual:
            if active is not None and not _TRAINING.search(line):
                active["actividad"] += " " + line.strip()
            previous = line.strip()
            continue
        match = match or annual
        prefix = line[:match.start()].strip(" -–—|:•") or line[match.end():].strip(" -–—|:•") or previous
        if annual:
            # Only the complete intervening years are guaranteed by year-only dates.
            start_year, start_month = int(match["y1"]) + 1, 1
            if match["y2"].isdigit():
                end_year, end_month = int(match["y2"]) - 1, 12
            else:
                end_year, end_month = today.year, today.month
        else:
            start_year, start_month = int(match["y1"]), _MONTHS_ES.get(match["m1"].lower()) or int(match["m1"])
            if match["current"]:
                end_year, end_month = today.year, today.month
            else:
                end_year, end_month = int(match["y2"]), _MONTHS_ES.get(match["m2"].lower()) or int(match["m2"])
        if (end_year, end_month) > (today.year, today.month):
            end_year, end_month = today.year, today.month
        start = _month_index(start_year, start_month)
        end = _month_index(end_year, end_month) + 1
        active = None
        if end <= start or end - start > 600 or not prefix:
            continue
        academic = bool(_TRAINING.search(prefix))
        info = {
            "etiqueta": prefix[:150], "inicio": f"{start_year:04d}-{start_month:02d}",
            "fin": f"{end_year:04d}-{end_month:02d}", "meses": end - start,
            "academico": academic, "actividad": "",
        }
        entries.append(info)
        if academic:
            ignored.append(info)
        else:
            intervals.append((start, end))
            active = info

    if not intervals:
        return None
    merged = _merge_month_intervals(intervals)
    months = sum(end - start for start, end in merged)
    return {
        "meses": months,
        "anos": round(months / 12, 2),
        "fuente": "rangos_fechas",
        "periodos": entries,
        "periodos_academicos_excluidos": ignored,
    }


def extraer_experiencia(texto: str) -> dict:
    dated = _experiencia_por_fechas(texto) or {}
    periodos = dated.get("periodos", [])
    evidence = evidencias(texto, periodos, AREA_RULES)
    declared = max((item["minimo_meses"] for item in evidence["declarada"]), default=None)
    months = dated.get("meses", declared)
    return {
        "meses_experiencia": months,
        "anos_experiencia": round(months / 12, 2) if months is not None else None,
        "experiencia_fuente": dated.get("fuente") or ("declaracion_explicita" if declared is not None else None),
        "periodos_experiencia": [{k: v for k, v in item.items() if k != "actividad"} for item in periodos],
        "experiencia_acreditada": evidence,
    }


def _requisito_experiencia(oferta_texto: str):
    minima = [item["minimo_meses"] for item in requisitos(oferta_texto) if item["obligatorio"]]
    return max(minima) / 12 if minima else None


def perfil_para_matching(row):
    profile = dict(row.get("profile_data") or {})
    summary = dict(profile.get("resumen") or {})
    if row.get("cv_text"):
        summary.update(extraer_experiencia(row["cv_text"]))
    profile["resumen"] = summary
    return profile


def construir_perfil_desde_texto(texto: str) -> dict:
    experiencia = extraer_experiencia(texto)
    limpio = re.sub(r"\s+", " ", texto).strip()
    # El encabezado profesional (antes de PERFIL PROFESIONAL) representa mejor
    # el rol declarado que tecnologías mencionadas en proyectos académicos.
    raw_headline = re.split(r"(?i)\bPERFIL PROFESIONAL\b", texto or "", maxsplit=1)[0]
    headline = re.sub(r"\s+", " ", raw_headline[:700]).strip()
    scored = []
    for area, cfg in AREA_RULES.items():
        role_hits = [r for r in cfg["roles"] if _contiene(limpio, r)]
        headline_role_hits = [r for r in cfg["roles"] if _contiene(headline, r)]
        skill_hits = [s for s in cfg["skills"] if _contiene(limpio, s)]
        if area == "Minería / Calidad industrial":
            industrial_evidence = [x for x in skill_hits if x in {
                "minería", "faena", "iso 9001", "qa/qc", "inspección", "soldadura",
                "materiales", "haccp", "laboratorio", "manufactura"
            }]
            if not industrial_evidence:
                role_hits = [x for x in role_hits if x not in {"aseguramiento de calidad", "control de calidad"}]
                headline_role_hits = [x for x in headline_role_hits if x not in {"aseguramiento de calidad", "control de calidad"}]
        score = len(role_hits) * 5 + len(skill_hits) * 2 + len(headline_role_hits) * 20
        if score: scored.append((score, area, role_hits, skill_hits))
    scored.sort(reverse=True)

    # No inventar Soporte TI si el CV no da señales. Perfil genérico explícito.
    if not scored:
        areas = {"Perfil general": {"titulo": [], "skills": [], "peso": 1.0, "nivel": _nivel(limpio)}}
        areas_detectadas = ["Perfil general"]
        roles = []
    else:
        areas, roles = {}, []
        top_score = scored[0][0]
        for score, area, role_hits, skill_hits in scored[:5]:
            cfg = AREA_RULES[area]
            peso = round(max(.75, min(1.30, .85 + (score / max(top_score, 1)) * .35)), 2)
            areas[area] = {"titulo": cfg["roles"], "skills": skill_hits, "peso": peso, "nivel": _nivel(limpio)}
            # Prioriza cargos realmente presentes; completa con variantes del área solo cuando hay evidencia fuerte.
            roles.extend(role_hits)
            if score >= 6: roles.extend(cfg["roles"][:4])
        areas_detectadas = [x[1] for x in scored[:5]]

    skills = [s for s in GENERIC_SKILLS if _contiene(limpio, s)]
    certifications = list(dict.fromkeys(
        line.strip(" \t•-–") for line in texto.splitlines()
        if re.search(r"\b(?:certified|certificación|certificacion|certificado|certificada|credencial)\b", line, re.I)
        and 8 <= len(line.strip()) <= 180
        and len(line.split()) >= 2
        and not re.search(r"\b(?:en curso|en preparación|preparando|previst[ao]|expirad[ao]|vencid[ao])\b", line, re.I)
    ))[:12]
    roles = list(dict.fromkeys(r.strip() for r in roles if r.strip()))[:16]
    # Si no se detectaron títulos, usa el nombre del área como búsqueda solo como fallback editable.
    if not roles and areas_detectadas != ["Perfil general"]:
        roles = [a for a in areas_detectadas[:3]]

    return {
        "origen": "cv",
        "version_perfil": 2,
        "resumen": {
            "areas_detectadas": areas_detectadas,
            "skills_detectadas": skills[:40],
            "certificaciones_detectadas": certifications,
            "roles_objetivo": roles,
            "terminos_busqueda": roles,  # compatibilidad con el resto de la app
            "seniority_estimado": _nivel(limpio),
            **experiencia,
            "caracteres_cv": len(limpio),
        },
        "areas": areas,
        "dominios_valorados": [],
        "penalizaciones": {"senioridad": SENIOR_TERMS, "ingles_avanzado": ADVANCED_ENGLISH},
    }


def guardar_perfil_cv(perfil: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(perfil, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
