"""Vacantes obtenidas desde el feed público de Get on Board."""

from xml.etree import ElementTree

from .common import es_relevante_perfil, oferta_es_valida, titulo_parece_relevante
from .http_common import date_posted, get_html, text_from_html

USES_BROWSER = False
NOMBRE = "GetOnBoard"
FEED_URL = "https://www.getonbrd.com/jobs/feed.xml"


def _feed_jobs(xml: str):
    root = ElementTree.fromstring(xml)
    for item in [*root.findall(".//job"), *root.findall(".//item")]:
        link = item.findtext("url") or item.findtext("link") or ""
        job = {
            "titulo": (item.findtext("title") or "").strip(),
            "empresa": (item.findtext("company") or item.findtext("company_name") or "").strip(),
            "descripcion": text_from_html(item.findtext("description") or ""),
            "modalidad": (item.findtext("location") or "").strip(),
            "link": link.strip(),
            "fuente": NOMBRE,
            "published_at": date_posted({"datePosted": item.findtext("date") or item.findtext("datePosted")}),
        }
        if job["link"] and oferta_es_valida(job):
            yield job


def buscar_ofertas(browser=None, terminos=None, modo="rapida", progreso=None):
    if progreso:
        progreso("Consultando el feed público de Get on Board.")
    jobs = list(_feed_jobs(get_html(FEED_URL, timeout=15)))
    jobs = [job for job in jobs if es_relevante_perfil(job["titulo"], job["descripcion"], terminos)]
    jobs.sort(key=lambda job: not titulo_parece_relevante(job["titulo"], terminos))
    return jobs[:14 if modo == "rapida" else 36]
