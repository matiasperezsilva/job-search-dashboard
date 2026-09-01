"""GetOnBoard mediante páginas públicas, sin Chromium."""
from urllib.parse import urlparse
from .common import es_relevante_perfil
from .http_common import absolute, jobposting_jsonld, location_text, organization_name, soup, text_from_html

USES_BROWSER = False
NOMBRE = "GetOnBoard"
BASE_URL = "https://www.getonbrd.com"
CATEGORIAS_RAPIDAS = ["/jobs/sysadmin-devops-qa", "/jobs/data-science-analytics"]
CATEGORIAS_EXTRA = ["/jobs/innovation-agile", "/jobs/customer-support"]
MAX_DETALLES_RAPIDA = 20


def _links_categoria(path):
    doc = soup(BASE_URL + path, timeout=8)
    categoria = path.rstrip('/').split('/')[-1]
    links, seen = [], set()
    for a in doc.find_all('a', href=True):
        href = a.get('href','').strip()
        url = absolute(BASE_URL, href)
        parsed = urlparse(url)
        parts = [p for p in parsed.path.split('/') if p]
        # GetOnBoard utiliza /jobs/<categoria>/<slug> y también /empleos/<categoria>/<slug>.
        if len(parts) < 3 or parts[0] not in {'jobs','empleos'} or parts[1] != categoria:
            continue
        if not parts[2] or url in seen:
            continue
        seen.add(url); links.append(url.split('?')[0])
    return links


def _extraer(link):
    doc = soup(link, timeout=8)
    job = jobposting_jsonld(doc)
    if job:
        titulo = str(job.get('title') or '').strip()
        empresa = organization_name(job.get('hiringOrganization'))
        descripcion = text_from_html(job.get('description') or '')
        modalidad = location_text(job.get('jobLocation'))
    else:
        h1 = doc.find('h1'); titulo = h1.get_text(' ', strip=True) if h1 else ''
        descripcion = doc.get_text(' ', strip=True); empresa = ''; modalidad = ''
    if not titulo: raise ValueError('GetOnBoard no entregó título para la vacante')
    return {'titulo':titulo,'empresa':empresa,'descripcion':descripcion,'modalidad':modalidad,'link':link,'fuente':NOMBRE}


def buscar_ofertas(browser=None, terminos=None, modo='rapida', progreso=None):
    categorias = CATEGORIAS_RAPIDAS if modo == 'rapida' else CATEGORIAS_RAPIDAS + CATEGORIAS_EXTRA
    links, seen = [], set()
    for i, cat in enumerate(categorias,1):
        if progreso: progreso(f'GetOnBoard · categoría {i}/{len(categorias)}')
        try:
            for link in _links_categoria(cat):
                if link not in seen: seen.add(link); links.append(link)
        except Exception as exc:
            if progreso: progreso(f'GetOnBoard · categoría omitida: {type(exc).__name__}')
    limit = MAX_DETALLES_RAPIDA if modo == 'rapida' else 40
    ofertas=[]
    for i,link in enumerate(links[:limit],1):
        if progreso: progreso(f'GetOnBoard · analizando {i}/{min(len(links),limit)}')
        try:
            o=_extraer(link)
            if es_relevante_perfil(o['titulo'],o['descripcion']) or any(k in o['titulo'].lower() for k in ('qa','tester','cloud','devops','dba','sre')):
                ofertas.append(o)
        except Exception:
            continue
    return ofertas
