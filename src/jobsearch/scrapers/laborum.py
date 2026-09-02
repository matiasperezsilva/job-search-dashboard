"""Laborum: API pública de búsqueda + fallback HTML/navegador.

El portal Jobint expone /api/avisos/searchV2. Se consulta primero ese endpoint
para evitar los bloqueos anti-bot que afectan al HTML de búsqueda desde Render.
Si el contrato del endpoint cambia, se intenta HTML público y finalmente navegador.
"""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .common import nueva_pagina
from .http_common import SESSION, text_from_html

USES_BROWSER = True
NOMBRE = "Laborum"
BASE_URL = "https://www.laborum.cl"
API_URL = f"{BASE_URL}/api/avisos/searchV2"
SITE_ID = "BMCL"
_LAST_DIAGNOSTIC = {}


def get_last_diagnostic():
    return dict(_LAST_DIAGNOSTIC)


def _slug(text: str) -> str:
    value = unicodedata.normalize("NFKD", (text or "").lower())
    value = "".join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")


def _blocked_text(text: str) -> bool:
    low = (text or "").lower()
    return any(x in low for x in (
        "captcha", "access denied", "verify you are human",
        "verifica que eres humano", "cloudflare", "request blocked",
    ))


def _walk(obj):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from _walk(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _walk(value)


def _looks_like_job(item: dict) -> bool:
    if not isinstance(item, dict):
        return False
    keys = {str(k).lower() for k in item}
    has_title = bool(keys & {"title", "titulo", "nombre", "jobtitle"})
    has_id = bool(keys & {"id", "idaviso", "jobid", "avisoid", "postingid"})
    has_url = bool(keys & {"url", "joburl", "applyurl", "link", "slug"})
    return has_title and (has_id or has_url)


def _first(item: dict, *names):
    lower = {str(k).lower(): v for k, v in item.items()}
    for name in names:
        value = lower.get(name.lower())
        if value not in (None, "", []):
            return value
    return ""


def _company(value):
    if isinstance(value, dict):
        return str(value.get("name") or value.get("nombre") or value.get("razonSocial") or "")
    return str(value or "")


def _location(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " · ".join(filter(None, (_location(x) for x in value)))
    if isinstance(value, dict):
        bits = [
            value.get("name"), value.get("nombre"), value.get("localidad"),
            value.get("provincia"), value.get("region"),
        ]
        return ", ".join(str(x) for x in bits if x)
    return ""


def _canonical_url(item: dict) -> str:
    direct = _first(item, "jobUrl", "applyUrl", "url", "link")
    if direct:
        return urljoin(BASE_URL, str(direct))
    job_id = _first(item, "jobId", "idAviso", "avisoId", "postingId", "id")
    slug = _slug(str(_first(item, "title", "titulo", "nombre") or "empleo"))
    if job_id:
        return f"{BASE_URL}/empleos/{slug}-{job_id}.html"
    return ""


def _api_job(item: dict):
    title = str(_first(item, "title", "titulo", "nombre", "jobTitle") or "").strip()
    if not title:
        return None
    company = _company(_first(item, "company", "empresa", "hiringOrganization", "companyName"))
    description = _first(item, "description", "descripcion", "detalle", "content")
    if isinstance(description, (list, dict)):
        chunks = []
        for obj in _walk(description):
            text = _first(obj, "text", "texto", "description", "descripcion")
            if text:
                chunks.append(str(text))
        description = " ".join(chunks)
    description = text_from_html(str(description or ""))
    modality = _first(item, "workModality", "modalidad", "employmentType", "tipoTrabajo")
    location = _location(_first(item, "location", "ubicacion", "jobLocation"))
    published = str(_first(item, "datePosted", "publishedAt", "fechaPublicacion") or "")
    return {
        "titulo": title,
        "empresa": company,
        "descripcion": description,
        "modalidad": " · ".join(x for x in (str(modality or "").strip(), location.strip()) if x),
        "link": _canonical_url(item),
        "fuente": NOMBRE,
        "published_at": published if re.match(r"^\d{4}-\d{2}-\d{2}", published) else "",
    }


def _api_search(term: str):
    """Prueba variantes compatibles del endpoint SearchV2.

    Jobint ha cambiado nombres de parámetros entre portales/versiones, por lo que
    probamos contratos GET equivalentes y aceptamos el primero que entregue avisos.
    """
    variants = [
        {"siteId": SITE_ID, "portal": "bumeran", "page": 0, "pageSize": 50, "query": term},
        {"siteId": SITE_ID, "portal": "bumeran", "page": 0, "pageSize": 50, "keyword": term},
        {"siteId": SITE_ID, "page": 0, "pageSize": 50, "query": term},
        {"siteId": SITE_ID, "page": 0, "pageSize": 50, "keyword": term},
    ]
    last_error = None
    for params in variants:
        try:
            r = SESSION.get(
                API_URL, params=params, timeout=12, allow_redirects=True,
                headers={"Accept": "application/json,text/plain,*/*", "Referer": BASE_URL + "/"},
            )
            if r.status_code in (403, 429):
                _LAST_DIAGNOSTIC["blocked"] = True
                last_error = RuntimeError(f"HTTP {r.status_code}")
                continue
            r.raise_for_status()
            content_type = (r.headers.get("content-type") or "").lower()
            if "json" not in content_type and not r.text.lstrip().startswith(("{", "[")):
                if _blocked_text(r.text):
                    _LAST_DIAGNOSTIC["blocked"] = True
                continue
            data = r.json()
            items, seen = [], set()
            for obj in _walk(data):
                if not _looks_like_job(obj):
                    continue
                job = _api_job(obj)
                if not job or not job["link"]:
                    continue
                key = job["link"]
                if key in seen:
                    continue
                seen.add(key)
                items.append(job)
            if items:
                return items
        except Exception as exc:
            last_error = exc
    if last_error:
        raise last_error
    return []


def _browser_api_search(page, term: str):
    """Consulta SearchV2 desde el contexto del navegador para reutilizar cookies/origen.

    Render puede recibir 403 vía requests mientras el endpoint sigue respondiendo al
    frontend real. Este fallback no resuelve CAPTCHA; solo usa el mismo contexto
    público que la página.
    """
    page.goto(BASE_URL + "/", wait_until="domcontentloaded", timeout=15000)
    page.wait_for_timeout(700)
    params = {
        "siteId": SITE_ID,
        "portal": "bumeran",
        "page": 0,
        "pageSize": 50,
        "query": term,
    }
    from urllib.parse import urlencode
    url = API_URL + "?" + urlencode(params)
    result = page.evaluate(
        """async (url) => {
          try {
            const r = await fetch(url, {
              method: 'GET',
              credentials: 'include',
              headers: {'accept':'application/json,text/plain,*/*'}
            });
            const text = await r.text();
            return {status:r.status, contentType:r.headers.get('content-type')||'', text};
          } catch (e) {
            return {status:0, contentType:'', text:String(e)};
          }
        }""",
        url,
    )
    status = int(result.get("status") or 0)
    text = result.get("text") or ""
    if status in (403, 429) or _blocked_text(text):
        _LAST_DIAGNOSTIC["blocked"] = True
        return []
    if status < 200 or status >= 300:
        raise RuntimeError(f"SearchV2 browser HTTP {status}")
    import json
    data = json.loads(text)
    items, seen = [], set()
    for obj in _walk(data):
        if not _looks_like_job(obj):
            continue
        job = _api_job(obj)
        if not job or not job["link"] or job["link"] in seen:
            continue
        seen.add(job["link"])
        items.append(job)
    return items


def _html_links(term: str):
    url = f"{BASE_URL}/empleos-busqueda-{_slug(term)}.html"
    r = SESSION.get(url, timeout=12, allow_redirects=True)
    if r.status_code in (403, 429) or _blocked_text(r.text):
        _LAST_DIAGNOSTIC["blocked"] = True
        return []
    r.raise_for_status()
    doc = BeautifulSoup(r.text, "html.parser")
    out = []
    for a in doc.select('a[href*="/empleos/"]'):
        link = urljoin(BASE_URL, a.get("href") or "").split("?")[0]
        if re.search(r"/empleos/[^/]+-\d+\.html$", link):
            out.append(link)
    return list(dict.fromkeys(out))


def _browser_links(page, term: str):
    url = f"{BASE_URL}/empleos-busqueda-{_slug(term)}.html"
    page.goto(url, wait_until="domcontentloaded", timeout=12000)
    page.wait_for_timeout(500)
    body = page.locator("body").inner_text(timeout=3000) if page.locator("body").count() else ""
    if _blocked_text(body):
        _LAST_DIAGNOSTIC["blocked"] = True
        return []
    raw = page.locator('a[href*="/empleos/"]').evaluate_all("els => els.map(e => e.href)")
    return list(dict.fromkeys(x.split("?")[0] for x in raw if re.search(r"/empleos/[^/]+-\d+\.html", x)))


def _detail_http(link: str):
    r = SESSION.get(link, timeout=12, allow_redirects=True)
    r.raise_for_status()
    doc = BeautifulSoup(r.text, "html.parser")
    # JSON-LD first.
    for script in doc.find_all("script", attrs={"type": re.compile("ld\\+json", re.I)}):
        try:
            import json
            data = json.loads(script.string or script.get_text())
        except Exception:
            continue
        for obj in _walk(data):
            if str(obj.get("@type") or "").lower() == "jobposting":
                return _api_job({
                    "title": obj.get("title"),
                    "company": obj.get("hiringOrganization"),
                    "description": obj.get("description"),
                    "jobLocation": obj.get("jobLocation"),
                    "datePosted": obj.get("datePosted"),
                    "jobUrl": link,
                })
    h1 = doc.find("h1")
    title = h1.get_text(" ", strip=True) if h1 else ""
    if not title:
        raise ValueError("Laborum no entregó título")
    return {
        "titulo": title,
        "empresa": "",
        "descripcion": doc.get_text(" ", strip=True),
        "modalidad": "",
        "link": link,
        "fuente": NOMBRE,
        "published_at": "",
    }


def buscar_ofertas(browser, terminos=None, modo="rapida", progreso=None):
    global _LAST_DIAGNOSTIC
    _LAST_DIAGNOSTIC = {
        "links_found": 0, "offers_extracted": 0, "detail_errors": 0,
        "query_errors": 0, "blocked": False, "transport": "searchV2",
    }
    terms = list(dict.fromkeys(t for t in (terminos or []) if t))[:4 if modo == "rapida" else 7]
    offers, seen = [], set()

    # 1) API pública: es la vía principal.
    for idx, term in enumerate(terms, 1):
        if progreso:
            progreso(f"Laborum · API {idx}/{len(terms)} · {term}")
        try:
            for job in _api_search(term):
                if job["link"] not in seen:
                    seen.add(job["link"])
                    offers.append(job)
        except Exception:
            _LAST_DIAGNOSTIC["query_errors"] += 1

    if offers:
        _LAST_DIAGNOSTIC["links_found"] = len(offers)
        _LAST_DIAGNOSTIC["offers_extracted"] = len(offers)
        return offers[:12 if modo == "rapida" else 25]

    # 2) SearchV2 desde contexto de navegador. Se intenta incluso si requests recibió
    # 403, porque el frontend público puede tener cookies/origen aceptados.
    if browser is not None:
        _LAST_DIAGNOSTIC["transport"] = "browser-api"
        page = nueva_pagina(browser)
        try:
            for idx, term in enumerate(terms[:2 if modo == "rapida" else 4], 1):
                if progreso:
                    progreso(f"Laborum · API navegador {idx} · {term}")
                try:
                    for job in _browser_api_search(page, term):
                        if job["link"] not in seen:
                            seen.add(job["link"])
                            offers.append(job)
                except Exception:
                    _LAST_DIAGNOSTIC["query_errors"] += 1
        finally:
            page.close()
        if offers:
            _LAST_DIAGNOSTIC["links_found"] = len(offers)
            _LAST_DIAGNOSTIC["offers_extracted"] = len(offers)
            _LAST_DIAGNOSTIC["blocked"] = False
            return offers[:12 if modo == "rapida" else 25]

    # 3) HTML público directo.
    _LAST_DIAGNOSTIC["transport"] = "html-fallback"
    links = []
    for term in terms[:2 if modo == "rapida" else 4]:
        try:
            links.extend(_html_links(term))
        except Exception:
            _LAST_DIAGNOSTIC["query_errors"] += 1
    links = list(dict.fromkeys(links))

    # 4) Navegador final. Un 403 de requests no impide probar el contexto del browser.
    if not links and browser is not None:
        _LAST_DIAGNOSTIC["transport"] = "playwright-fallback"
        page = nueva_pagina(browser)
        for term in terms[:2]:
            try:
                links.extend(_browser_links(page, term))
            except Exception:
                _LAST_DIAGNOSTIC["query_errors"] += 1
        page.close()
        links = list(dict.fromkeys(links))

    _LAST_DIAGNOSTIC["links_found"] = len(links)
    limit = 6 if modo == "rapida" else 15
    for link in links[:limit]:
        try:
            job = _detail_http(link)
            if job:
                offers.append(job)
                _LAST_DIAGNOSTIC["offers_extracted"] += 1
        except Exception:
            _LAST_DIAGNOSTIC["detail_errors"] += 1
    return offers
