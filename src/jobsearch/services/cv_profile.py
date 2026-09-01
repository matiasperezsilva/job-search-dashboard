from __future__ import annotations
from io import BytesIO
import json, re
from pathlib import Path
from pypdf import PdfReader
from docx import Document

# Taxonomía deliberadamente transversal. No pretende adivinar una profesión por una
# sola palabra: combina títulos/funciones + competencias y deja los roles editables.
AREA_RULES = {
    "Tecnología / Software": {
        "roles": ["desarrollador", "developer", "software engineer", "programador", "frontend", "backend", "full stack", "analista de sistemas"],
        "skills": ["python", "java", "javascript", "typescript", "react", "node", "spring", "git", "github", "api", "sql"],
    },
    "QA / Testing": {
        "roles": ["analista qa", "qa tester", "qa engineer", "tester software", "qa funcional", "qa automation", "sdet", "analista de pruebas"],
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
        reader = PdfReader(BytesIO(contenido)); return "\n".join((p.extract_text() or "") for p in reader.pages).strip()
    if ext == ".docx":
        doc = Document(BytesIO(contenido)); return "\n".join(p.text for p in doc.paragraphs if p.text.strip()).strip()
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



def _anos_experiencia_explicitos(texto: str):
    """Extrae una cifra solo cuando el CV declara explícitamente años de experiencia.
    Evita sumar rangos de educación/proyectos y producir una precisión falsa."""
    vals=[]
    for m in re.finditer(r"(?i)(?:más de|mas de|sobre|aprox(?:imadamente)?\.?|al menos)?\s*(\d{1,2})\s*\+?\s*años?\s+(?:de\s+)?experiencia", texto):
        n=int(m.group(1))
        if 0 <= n <= 50: vals.append(n)
    return max(vals) if vals else None


def _requisito_experiencia(oferta_texto: str):
    """Devuelve el mínimo de años solicitado por una oferta cuando es explícito."""
    patterns=[
        r"(?i)(?:mínimo|minimo|al menos)\s+(\d{1,2})\s*años?\s+(?:de\s+)?experiencia",
        r"(?i)(\d{1,2})\s*(?:a|[-–])\s*\d{1,2}\s*años?\s+(?:de\s+)?experiencia",
        r"(?i)(\d{1,2})\s*\+?\s*años?\s+(?:de\s+)?experiencia",
        r"(?i)experiencia\s+(?:mínima|minima)?\s*(?:de)?\s*(\d{1,2})\s*años?",
    ]
    vals=[]
    for pat in patterns:
        for m in re.finditer(pat, oferta_texto or ""):
            n=int(m.group(1))
            if 0 < n <= 30: vals.append(n)
    return min(vals) if vals else None


def construir_perfil_desde_texto(texto: str) -> dict:
    limpio = re.sub(r"\s+", " ", texto).strip()
    scored = []
    for area, cfg in AREA_RULES.items():
        role_hits = [r for r in cfg["roles"] if _contiene(limpio, r)]
        skill_hits = [s for s in cfg["skills"] if _contiene(limpio, s)]
        score = len(role_hits) * 5 + len(skill_hits) * 2
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
            areas[area] = {"titulo": cfg["roles"], "skills": cfg["skills"], "peso": peso, "nivel": _nivel(limpio)}
            # Prioriza cargos realmente presentes; completa con variantes del área solo cuando hay evidencia fuerte.
            roles.extend(role_hits)
            if score >= 6: roles.extend(cfg["roles"][:4])
        areas_detectadas = [x[1] for x in scored[:5]]

    skills = [s for s in GENERIC_SKILLS if _contiene(limpio, s)]
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
            "roles_objetivo": roles,
            "terminos_busqueda": roles,  # compatibilidad con el resto de la app
            "seniority_estimado": _nivel(limpio),
            "anos_experiencia": _anos_experiencia_explicitos(limpio),
            "caracteres_cv": len(limpio),
        },
        "areas": areas,
        "dominios_valorados": [],
        "penalizaciones": {"senioridad": SENIOR_TERMS, "ingles_avanzado": ADVANCED_ENGLISH},
    }


def guardar_perfil_cv(perfil: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(perfil, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
