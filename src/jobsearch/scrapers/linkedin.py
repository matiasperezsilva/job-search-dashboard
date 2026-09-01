"""LinkedIn Jobs: búsqueda pública sin credenciales.

No solicita contraseña ni cookies. Si LinkedIn limita la consulta pública, la fuente
falla de forma aislada y el resto de portales continúa.
"""
from urllib.parse import quote_plus, urljoin
import re
from bs4 import BeautifulSoup
from .http_common import get_html

NOMBRE="LinkedIn"; BASE="https://www.linkedin.com"; SEARCH=BASE+"/jobs/search"; USES_BROWSER=False

def _job_id(href):
    m=re.search(r"/jobs/view/(?:[^/?#]*-)?(\d+)", href or "")
    return m.group(1) if m else ""

def _clean(href):
    jid=_job_id(href); return f"{BASE}/jobs/view/{jid}" if jid else ""

def _links(html):
    soup=BeautifulSoup(html,"html.parser"); out=[]
    for a in soup.select('a.base-card__full-link, a[href*="/jobs/view/"]'):
        u=_clean(urljoin(BASE,a.get("href","")))
        if u and u not in out: out.append(u)
    return out

def _detail(html,link):
    soup=BeautifulSoup(html,"html.parser")
    def txt(sel):
        e=soup.select_one(sel); return e.get_text(" ",strip=True) if e else ""
    title=txt("h1.top-card-layout__title, h1")
    if not title: return None
    time_el=soup.select_one("time[datetime], .posted-time-ago__text")
    published=(time_el.get("datetime") or "").strip() if time_el and time_el.has_attr("datetime") else ""
    return {"titulo":title,"empresa":txt(".topcard__org-name-link, .topcard__flavor a"),
            "descripcion":txt(".description__text, .show-more-less-html__markup"),
            "modalidad":txt(".topcard__flavor--bullet, .topcard__flavor"),
            "link":link,"fuente":NOMBRE,"published_at":published}

def buscar_ofertas(browser=None, terminos=None, modo="rapida", progreso=None):
    terms=list(dict.fromkeys(x.strip() for x in (terminos or []) if x and x.strip()))[:2 if modo=="rapida" else 5]
    max_links=12 if modo=="rapida" else 30; links=[]
    for i,term in enumerate(terms,1):
        if progreso: progreso(f"LinkedIn · búsqueda {i}/{len(terms)}: {term}")
        html=get_html(f"{SEARCH}?keywords={quote_plus(term)}&location=Chile&f_TPR=r2592000",timeout=12)
        if "authwall" in html.lower() or "checkpoint" in html.lower():
            raise RuntimeError("LinkedIn solicitó autenticación y limitó la consulta pública.")
        for u in _links(html):
            if u not in links: links.append(u)
            if len(links)>=max_links: break
        if len(links)>=max_links: break
    offers=[]
    for i,link in enumerate(links,1):
        try:
            if progreso: progreso(f"LinkedIn · leyendo {i}/{len(links)}")
            o=_detail(get_html(link,timeout=10),link)
            if o: offers.append(o)
        except Exception: continue
    return offers
