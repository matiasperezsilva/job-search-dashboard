import html as html_lib
import json
import re
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

from .common import USER_AGENT

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": USER_AGENT,
    "Accept-Language": "es-CL,es;q=0.9,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
})


class PortalBlocked(RuntimeError):
    pass


def get_html(url: str, timeout: int = 10) -> str:
    origin = urlsplit(url).hostname
    for _ in range(4):
        with SESSION.get(url, timeout=timeout, allow_redirects=False, stream=True) as response:
            if response.is_redirect:
                url = urljoin(url, response.headers["Location"])
                target = urlsplit(url)
                if target.scheme != "https" or target.hostname != origin or target.username or target.password:
                    raise ValueError("El portal redirigió fuera de su origen.")
                continue
            if response.status_code in {403, 429}:
                raise PortalBlocked()
            response.raise_for_status()
            data = bytearray()
            for chunk in response.iter_content(chunk_size=65536):
                data.extend(chunk)
                if len(data) > 12 * 1024 * 1024:
                    raise ValueError("La respuesta del portal supera el límite de lectura.")
            text = data.decode(response.encoding or "utf-8", errors="replace")
            if re.search(r"<title>[^<]*(?:just a moment|access denied|captcha|verificaci[oó]n de seguridad)", text[:8000], re.I):
                raise PortalBlocked()
            return text
    raise ValueError("El portal devolvió demasiadas redirecciones.")


def soup(url: str, timeout: int = 10) -> BeautifulSoup:
    return BeautifulSoup(get_html(url, timeout), "html.parser")


def _walk_json(obj):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _walk_json(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_json(v)


def jobposting_jsonld(doc: BeautifulSoup):
    for script in doc.find_all("script", attrs={"type": re.compile("ld\\+json", re.I)}):
        raw = script.string or script.get_text(" ", strip=True)
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue
        for item in _walk_json(data):
            tipo = item.get("@type")
            tipos = tipo if isinstance(tipo, list) else [tipo]
            if any(str(x).lower() == "jobposting" for x in tipos if x):
                return item
    return None


def text_from_html(value: str) -> str:
    if not value:
        return ""
    return BeautifulSoup(html_lib.unescape(str(value)), "html.parser").get_text(" ", strip=True)


def organization_name(value) -> str:
    if isinstance(value, dict):
        return str(value.get("name") or "")
    return str(value or "")


def date_posted(value) -> str:
    """Normaliza datePosted de JSON-LD sin inventar una fecha cuando no existe."""
    if isinstance(value, dict):
        value = value.get("datePosted")
    raw = str(value or "").strip()
    if not raw:
        return ""
    # Conservamos ISO/fecha del portal. PostgreSQL timestamptz puede parsear ISO comunes.
    m = re.match(r"^(\d{4}-\d{2}-\d{2})(?:[Tt ]([0-9:.+-]+|[0-9:.]+[Zz]))?", raw)
    if not m:
        return ""
    return raw


def location_text(value) -> str:
    if isinstance(value, list):
        return " · ".join(filter(None, (location_text(x) for x in value)))
    if not isinstance(value, dict):
        return str(value or "")
    addr = value.get("address", value)
    if isinstance(addr, dict):
        bits = [addr.get("addressLocality"), addr.get("addressRegion"), addr.get("addressCountry")]
        return ", ".join(str(x) for x in bits if x)
    return str(addr or "")


def absolute(base: str, href: str) -> str:
    return urljoin(base, href)
