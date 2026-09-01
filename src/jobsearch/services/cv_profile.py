from __future__ import annotations

from collections import Counter
from io import BytesIO
import json
import re
from pathlib import Path

from pypdf import PdfReader
from docx import Document


AREA_RULES = {
    "QA / Testing": {
        "title_terms": ["qa", "tester", "quality assurance", "analista qa", "analista de pruebas", "sdet"],
        "skills": ["postman", "selenium", "playwright", "cypress", "jmeter", "gherkin", "cucumber", "test cases", "casos de prueba", "regresión", "regression", "api testing", "testing"],
    },
    "Cloud / Operaciones": {
        "title_terms": ["cloud", "cloud support", "cloud engineer", "cloud operations", "soporte cloud", "devops", "sre"],
        "skills": ["aws", "amazon web services", "ec2", "s3", "lambda", "cloudfront", "route 53", "iam", "cloudwatch", "linux", "docker", "terraform", "kubernetes"],
    },
    "Bases de datos": {
        "title_terms": ["dba", "database administrator", "administrador de base de datos", "administrador bases de datos"],
        "skills": ["sql", "sql server", "oracle", "postgresql", "mysql", "db2", "database", "base de datos"],
    },
    "Análisis funcional": {
        "title_terms": ["analista funcional", "business analyst", "analista de negocio", "functional analyst"],
        "skills": ["requerimientos", "historias de usuario", "user stories", "criterios de aceptación", "uml", "bpmn", "jira", "confluence"],
    },
    "Soporte TI": {
        "title_terms": ["soporte ti", "soporte técnico", "service desk", "help desk", "mesa de ayuda", "support analyst"],
        "skills": ["active directory", "windows", "linux", "ticket", "incidentes", "soporte n1", "soporte n2", "office 365", "microsoft 365"],
    },
    "Desarrollo": {
        "title_terms": ["developer", "desarrollador", "software engineer", "programador", "backend", "frontend", "full stack"],
        "skills": ["python", "java", "javascript", "typescript", "react", "node", "spring", "git", "github"],
    },
}

GENERIC_SKILLS = [
    "python", "java", "javascript", "typescript", "sql", "linux", "git", "github",
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "jenkins",
    "postman", "selenium", "playwright", "cypress", "jmeter", "jira", "confluence",
    "oracle", "postgresql", "mysql", "sql server", "db2", "active directory",
    "salesforce", "sap", "rest", "api", "agile", "scrum", "gherkin", "cucumber",
]

ROLE_NO_OBJETIVO = [
    "ejecutivo comercial", "ventas", "sales", "account manager", "marketing",
    "recruiter", "reclutador", "recursos humanos", "contador", "contable",
]

SENIOR_TERMS = ["senior", "sr.", "sr ", "lead", "líder", "lider", "jefe", "manager", "arquitecto"]
ADVANCED_ENGLISH = ["english c1", "inglés c1", "advanced english", "inglés avanzado", "fluent english"]


def extraer_texto_cv(nombre: str, contenido: bytes) -> str:
    ext = Path(nombre).suffix.lower()
    if ext == ".pdf":
        reader = PdfReader(BytesIO(contenido))
        return "\n".join((page.extract_text() or "") for page in reader.pages).strip()
    if ext == ".docx":
        doc = Document(BytesIO(contenido))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip()).strip()
    if ext in {".txt", ".md"}:
        return contenido.decode("utf-8", errors="replace").strip()
    raise ValueError("Formato no soportado. Usa PDF, DOCX o TXT.")


def _contiene(texto: str, termino: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(termino.lower())}(?!\w)", texto.lower()) is not None


def construir_perfil_desde_texto(texto: str) -> dict:
    limpio = re.sub(r"\s+", " ", texto).strip()
    lower = limpio.lower()

    areas = {}
    puntuaciones_area = {}
    for area, rules in AREA_RULES.items():
        title_hits = [t for t in rules["title_terms"] if _contiene(lower, t)]
        skill_hits = [s for s in rules["skills"] if _contiene(lower, s)]
        fuerza = len(title_hits) * 3 + len(skill_hits)
        if fuerza <= 0:
            continue
        puntuaciones_area[area] = fuerza
        # El peso deriva de la evidencia hallada en el CV, acotado para no dominar el scoring.
        peso = min(1.30, 0.85 + fuerza * 0.05)
        areas[area] = {
            "titulo": rules["title_terms"],
            "skills": list(dict.fromkeys(skill_hits + rules["skills"])),
            "peso": round(peso, 2),
            "nivel": "junior" if fuerza < 5 else "parcial" if fuerza < 9 else "experimentado",
        }

    # Si un CV es escueto, mantener las áreas con mayor probabilidad a partir de skills genéricas.
    if not areas:
        areas["Soporte TI"] = {
            "titulo": AREA_RULES["Soporte TI"]["title_terms"],
            "skills": AREA_RULES["Soporte TI"]["skills"],
            "peso": 0.9,
            "nivel": "junior",
        }

    skills_detectadas = [s for s in GENERIC_SKILLS if _contiene(lower, s)]
    dominios = []
    for term in ["retail", "banca", "banking", "ecommerce", "e-commerce", "crm", "salesforce", "fintech", "telecomunicaciones"]:
        if _contiene(lower, term):
            dominios.append(term)

    # Los términos de búsqueda deben describir CARGOS, no tecnologías aisladas.
    # Buscar por "sql", "linux" o "java" genera muchísimo ruido en portales generalistas.
    orden_areas = sorted(puntuaciones_area, key=puntuaciones_area.get, reverse=True)
    SEARCH_TERMS = {
        "QA / Testing": ["qa software", "qa tester", "analista qa", "tester software", "qa funcional", "qa automation"],
        "Cloud / Operaciones": ["cloud support", "soporte cloud", "cloud engineer junior", "operaciones cloud"],
        "Bases de datos": ["dba junior", "administrador base de datos", "database administrator junior"],
        "Análisis funcional": ["analista funcional ti", "business analyst ti"],
        "Soporte TI": ["soporte ti", "soporte técnico n1", "service desk", "help desk ti"],
        "Desarrollo": ["desarrollador junior", "software developer junior"],
    }
    terminos = []
    for area in orden_areas[:4]:
        terminos.extend(SEARCH_TERMS.get(area, AREA_RULES[area]["title_terms"][:3]))
    terminos = list(dict.fromkeys(t.strip() for t in terminos if t.strip()))[:14]

    return {
        "origen": "cv",
        "resumen": {
            "areas_detectadas": orden_areas,
            "skills_detectadas": skills_detectadas,
            "terminos_busqueda": terminos,
            "caracteres_cv": len(limpio),
        },
        "areas": areas,
        "dominios_valorados": dominios,
        "penalizaciones": {
            "roles_no_objetivo": ROLE_NO_OBJETIVO,
            "senioridad": SENIOR_TERMS,
            "ingles_avanzado": ADVANCED_ENGLISH,
        },
    }


def guardar_perfil_cv(perfil: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(perfil, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
