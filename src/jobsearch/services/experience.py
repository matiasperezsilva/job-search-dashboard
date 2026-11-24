"""Evidence and experience requirements measured in whole months."""

import re
import unicodedata


def normalizar(text):
    text = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in text.casefold() if not unicodedata.combining(c))


def menciona(text, term):
    return bool(term and re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text))


AREA_ALIASES = {
    "Cloud / Operaciones": ("cloud", "nube", "computacion en la nube", "cloud computing", "infraestructura cloud"),
    "QA / Testing": ("qa", "testing", "pruebas de software", "control de calidad de software"),
    "Tecnología / Software": ("desarrollo", "desarrollo de software", "software", "programacion"),
    "Datos / Analítica": ("datos", "analitica", "analisis de datos", "ciencia de datos"),
    "Bases de datos": ("bases de datos", "base de datos", "administracion de bases de datos"),
    "Soporte TI": ("soporte tecnico", "soporte ti", "mesa de ayuda", "infraestructura ti"),
    "Ventas / Comercial": ("ventas", "comercial", "venta consultiva"),
    "Finanzas / Contabilidad": ("auditoria", "contabilidad", "finanzas"),
    "Salud / Enfermería": ("enfermeria", "salud"),
    "Logística / Supply Chain": ("logistica", "cadena de suministro"),
    "Minería / Calidad industrial": ("mineria", "calidad industrial", "qa/qc"),
}

_TECH_ALIASES = {
    "aws": ("amazon web services", "aws"), "azure": ("microsoft azure", "azure"),
    "gcp": ("google cloud platform", "google cloud", "gcp"),
    "kubernetes": ("kubernetes", "k8s"), "javascript": ("javascript", "js"),
    "typescript": ("typescript", "ts"), "node": ("node.js", "nodejs", "node"),
    "sql server": ("microsoft sql server", "sql server"), "postgresql": ("postgresql", "postgres"),
    "c#": ("c#",), ".net": (".net", "dotnet"),
}

_ROLE_ALIASES = {
    "cloud support": ("cloud support", "soporte cloud", "soporte en la nube"),
    "cloud engineer": ("cloud engineer", "ingeniero cloud", "ingeniera cloud", "ingeniero de nube"),
    "cloud operations": ("cloud operations", "operaciones cloud", "operaciones en la nube"),
    "analista qa": ("analista qa", "qa analyst", "analista de pruebas"),
    "dba": ("dba", "database administrator", "administrador de base de datos"),
}

_TRAINING = re.compile(r"\b(?:cursos?|certificaciones?|certificados?|certified|capacitaci[oó]n|bootcamp|talleres?|diplomados?|tesis|proyecto de t[ií]tulo|proyecto acad[eé]mico|capstone|proyecto universitario|estudios?)\b", re.I)
_NOT_WORK = re.compile(r"^\s*(?:educaci[oó]n(?: y formaci[oó]n)?|formaci[oó]n(?: acad[eé]mica| complementaria| profesional)?|(?:cursos y )?certificaciones?|cursos?|capacitaciones?|proyectos?(?: acad[eé]micos?)?|habilidades|competencias|idiomas|educational background|education|certifications|training|skills)\s*[:\s]*$", re.I)
_WORK = re.compile(r"^\s*(?:experiencia(?: (?:profesional|laboral|relevante))?|trayectoria profesional|historial laboral|work experience|professional experience|employment history)\s*[:\s]*$", re.I)

_N = r"\d{1,2}(?:[.,]\d+)?"
_UNIT = r"anos?|mes(?:es)?|years?|months?|yrs?"
_AMOUNT = rf"(?P<min>{_N})(?:\s*(?:a|to|y|and|[-–—])\s*(?P<max>{_N}))?\s*\+?\s*(?P<unit>{_UNIT})\b(?:\s*\+)?"
_EXP = r"(?:experiencia|experience)"
_QUANTIFIED = re.compile(
    rf"(?:(?P<before>{_EXP}(?:\s+(?:laboral|profesional|relevante|previa|required|minimum|minima|comprobable|demostrable))?"
    rf"(?:\s+(?:en|con|como|in|with|as)\s+[^;:\n\d]{{1,65}}?)?[\s:]*"
    rf"(?:(?:de|of|entre|between|minim[oa](?: de)?|al menos|mas de|hasta|at least|more than)\s+)?)"
    rf"{_AMOUNT}|(?:{_AMOUNT.replace('?P<min>', '?P<min2>').replace('?P<max>', '?P<max2>').replace('?P<unit>', '?P<unit2>')})"
    rf"(?:\s+(?:de|of))?\s+(?:{_EXP}|(?=(?:en|con|como|in|with|as)\b)))", re.I,
)
_DESIRABLE = r"\b(?:deseables?|preferid[oa]s?|preferentemente|idealmente|valorables?|opcional(?:es)?|no (?:excluyentes?|obligatori[oa]s?|indispensables?)|plus|preferred|desirable|nice to have|a (?:plus|bonus))\b"
_REQUIRED = r"\b(?:requisitos?(?: minimos?)?|obligatori[oa]s?|excluyentes?|indispensables?|imprescindibles?|se requiere[n]?|must(?: have)?|required|requirements?|minimum)\b"
_HEADING = re.compile(rf"(?:^|(?<=[.!?;\n])|\s)\s*(?P<label>(?:requisitos?\s+)?(?:{_DESIRABLE}|{_REQUIRED})|funciones|beneficios|responsabilidades)\s*:\s*", re.I)
_SCOPE = re.compile(r"\b(?P<link>como|en|con|as|in|with|usando|utilizando)\s+(?P<name>.+)", re.I)


def _meses(value, unit):
    number = float(value.replace(",", "."))
    return round(number * (1 if unit.startswith(("mes", "month")) else 12))


def requisitos(texto):
    """Extract scoped minima. An upper endpoint describes the range, not a cap."""
    text = normalizar(texto)
    text = _HEADING.sub(lambda m: f"\n{m['label']}:\n", text)
    section = True
    output = []
    for line in re.split(r"[\n;•]+|[.!?](?!\d)\s+", text):
        line = line.strip(" \t:-–—")
        if not line:
            continue
        if re.fullmatch(rf"(?:requisitos?\s+)?(?:{_DESIRABLE})", line):
            section = False
            continue
        if re.fullmatch(rf"(?:{_REQUIRED}|funciones|beneficios|responsabilidades)", line):
            section = True
            continue
        if re.match(r"(?:somos|empresa|contamos|fundad[ao]|trayectoria de la empresa|we are|our company)\b", line):
            continue
        matches = list(_QUANTIFIED.finditer(line))
        for i, match in enumerate(matches):
            left = 0 if i == 0 else matches[i - 1].end()
            right = matches[i + 1].start() if i + 1 < len(matches) else len(line)
            prefix = line[left:match.start()].rsplit(",", 1)[-1].strip()
            suffix = line[match.end():right].strip()
            # Commas and conjunctions before a new duration delimit independent requirements.
            tail = re.sub(r"(?:[,.;]\s*|\s+(?:y|and)\s*)$", "", suffix)
            context = f"{prefix} {match.group()} {tail}"
            if re.search(r"\b(?:somos|empresa con|contamos con|our company has)\b", prefix):
                continue
            if i + 1 < len(matches):
                context = re.split(r",\s*(?=(?:{0}|{1})\b)".format(_DESIRABLE, _REQUIRED), context)[0]
            if re.search(r"\b(?:hasta|up to)\s*$", prefix) or re.search(r"\b(?:hasta|up to)\s+\d", match.group()):
                continue
            digit = match['min'] or match['min2']
            unit = match['unit'] or match['unit2']
            max_digit = match['max'] or match['max2']
            minimum = _meses(digit, unit)
            if re.search(r"\b(?:mas de|more than)\s*$", prefix) or re.search(r"\b(?:mas de|more than)\s+\d", match.group()):
                minimum += 1
            if not 0 < minimum <= 600:
                continue
            scope = _SCOPE.search(tail) or _SCOPE.search(match['before'] or "")
            name = scope['name'] if scope else ""
            name = re.split(rf"\s*\([^)]*(?:{_DESIRABLE}|{_REQUIRED})[^)]*\)|\s+(?:{_DESIRABLE}|{_REQUIRED})(?:\b|$)", name)[0]
            name = re.sub(r"\s+(?:de|of|entre|between|al menos|at least)\s*$", "", name).strip(" .,:-–—")
            if name in {"el cargo", "el puesto", "cargos similares", "roles similares", "the role", "a similar role"}:
                scope_kind = "cargo_oferta"
            else:
                scope_kind = "cargo" if scope and scope['link'] in {"como", "as"} else "ambito" if name else "total"
            output.append({
                "minimo_meses": minimum, "maximo_meses": _meses(max_digit, unit) if max_digit else None,
                "obligatorio": bool(not re.search(_DESIRABLE, context) and (section or re.search(_REQUIRED, context))),
                "alcance": scope_kind, "ambito": name[:110], "texto": match.group().strip()[:135],
            })
    return output


def areas_de_cargo(text, reglas):
    return [a for a, cfg in reglas.items() if any(menciona(text, normalizar(role)) for role in cfg["roles"])]


def _tecnologias(reglas):
    return {**{normalizar(skill): (normalizar(skill),) for cfg in reglas.values() for skill in cfg["skills"]}, **_TECH_ALIASES}


def _claves(text, terms):
    return [key for key, aliases in terms.items() if any(menciona(text, alias) for alias in aliases)]


def evidencias(texto, periodos, reglas):
    periods = []
    technologies = _tecnologias(reglas)
    for item in periodos:
        if item.get("academico"):
            continue
        title = normalizar(item.get("etiqueta", ""))
        context = normalizar(item.get("actividad", ""))
        periods.append({
            "inicio": item["inicio"], "fin": item["fin"], "meses": item["meses"],
            "cargo": title, "areas": areas_de_cargo(title, reglas),
            "tecnologias": _claves(f"{title} {context}", technologies),
        })
    declared = []
    for line in (texto or "").splitlines():
        if _NOT_WORK.fullmatch(line) or _WORK.fullmatch(line):
            break
        if not _TRAINING.search(line):
            for req in requisitos(line):
                data = {**req, "cargo_declarado": normalizar(line)[:110]}
                declared.append(data)
    return {"periodos": periods, "declarada": declared}


def _ord(month):
    year, mon = map(int, month.split("-"))
    return year * 12 + mon - 1


def meses_periodos(periods):
    intervals = sorted((_ord(p["inicio"]), _ord(p["fin"]) + 1) for p in periods)
    end = total = 0
    for start, stop in intervals:
        total += max(0, stop - max(start, end))
        end = max(end, stop)
    return total


def _alcance(req, title, rules):
    name = req["ambito"]
    kind = req["alcance"]
    if kind == "total":
        return "total", []
    if kind == "cargo_oferta":
        name = normalizar(title)
    if kind in {"cargo", "cargo_oferta"}:
        return "cargo", [name]
    name = re.split(r"[,;]", name)[0].strip()
    roles = _claves(name, _ROLE_ALIASES)
    if roles or any(normalizar(role) == name for cfg in rules.values() for role in cfg["roles"]):
        return "cargo", roles or [name]
    terms = {key: tuple(dict.fromkeys((normalizar(key), *AREA_ALIASES.get(key, ())))) for key in rules}
    terms.update({key: tuple((*aliases, normalizar(key))) for key, aliases in AREA_ALIASES.items()})
    exact_areas = [key for key, aliases in terms.items() if name in aliases]
    if exact_areas:
        return "area", exact_areas
    tech = _claves(name, _tecnologias(rules))
    if tech:
        # Avoid overlapping names (SQL inside SQL Server, Node inside Node.js).
        return "tecnologia", [t for t in tech if not any(t != other and menciona(other, t) for other in tech)]
    areas = _claves(name, terms)
    return ("area", areas or [name])


def _coincide_cargo(label, role):
    role = re.sub(r"\b(?:senior|junior|semi senior|sr|jr|lead)\b", "", role).strip()
    aliases = next((aliases for key, aliases in _ROLE_ALIASES.items() if key == role or any(menciona(role, a) for a in aliases)), ())
    return any(menciona(label, a) for a in (role, *aliases))


def evaluar_requisitos(description, title, summary, rules):
    evidence = summary.get("experiencia_acreditada") or {}
    periods = evidence.get("periodos") or []
    explicit = evidence.get("declarada") or []
    total = summary.get("meses_experiencia")
    if total is None and summary.get("anos_experiencia") is not None:
        try:
            total = round(float(summary["anos_experiencia"]) * 12)
        except (TypeError, ValueError, OverflowError):
            pass
    evaluated = []
    for req in requisitos(description):
        kind, keys = _alcance(req, title, rules)
        if kind == "total":
            actual = total
        else:
            measured = []
            for key in keys:
                def relevant(period):
                    if kind == "cargo":
                        return _coincide_cargo(period["cargo"], key)
                    return key in period["areas" if kind == "area" else "tecnologias"]

                dated = meses_periodos([period for period in periods if relevant(period)])
                claimed = [item["minimo_meses"] for item in explicit if (kind, [key]) == _alcance(item, item["cargo_declarado"], rules)]
                measured.append(dated or max(claimed, default=0))
            alternative = bool(re.search(r"\b(?:o|or)\b", req["ambito"]))
            actual = (max(measured) if alternative else min(measured)) if measured else 0
        evaluated.append({**req, "tipo": kind, "categorias": keys, "acreditado_meses": actual,
                          "cumple": actual is not None and actual >= req["minimo_meses"]})
    return evaluated
