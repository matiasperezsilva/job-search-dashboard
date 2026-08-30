import hashlib
from datetime import datetime, timezone
from jobsearch.services.auth import client_autenticado, usuario_actual


def _uid():
    user = usuario_actual()
    if not user:
        raise RuntimeError('Debes iniciar sesión.')
    return str(user.id)


def job_id(oferta):
    raw = '|'.join(str(oferta.get(k, '')) for k in ('titulo', 'empresa', 'fuente'))
    return hashlib.sha1(raw.lower().strip().encode('utf-8')).hexdigest()[:16]


def guardar_perfil(perfil, cv_texto, cv_name=''):
    row = {'user_id': _uid(), 'cv_name': cv_name, 'cv_text': cv_texto, 'profile_data': perfil, 'updated_at': datetime.now(timezone.utc).isoformat()}
    return client_autenticado().table('profiles').upsert(row, on_conflict='user_id').execute()


def obtener_perfil():
    res = client_autenticado().table('profiles').select('*').eq('user_id', _uid()).limit(1).execute()
    return res.data[0] if res.data else None


def eliminar_perfil():
    return client_autenticado().table('profiles').delete().eq('user_id', _uid()).execute()


def guardar_ofertas(ofertas, perfil, evaluador):
    uid = _uid(); now = datetime.now(timezone.utc).isoformat(); client = client_autenticado(); nuevas = 0
    for oferta in ofertas:
        jid = job_id(oferta)
        existing = client.table('jobs').select('id').eq('user_id', uid).eq('id', jid).limit(1).execute().data
        ev = evaluador(oferta, perfil)
        row = {'id': jid, 'user_id': uid, 'titulo': oferta.get('titulo',''), 'empresa': oferta.get('empresa',''), 'descripcion': oferta.get('descripcion',''), 'modalidad': oferta.get('modalidad',''), 'link': oferta.get('link',''), 'fuente': oferta.get('fuente',''), 'puntaje': ev['puntaje'], 'area': ev['area'], 'razon': ev['razon'], 'first_seen': existing[0].get('first_seen', now) if existing and 'first_seen' in existing[0] else now, 'last_seen': now}
        client.table('jobs').upsert(row, on_conflict='user_id,id').execute()
        if not existing: nuevas += 1
    return nuevas


def listar_ofertas(min_score=0, fuente=None, estado=None):
    uid = _uid(); client = client_autenticado()
    q = client.table('jobs').select('*').eq('user_id', uid).gte('puntaje', min_score).order('puntaje', desc=True).order('last_seen', desc=True)
    if fuente: q = q.eq('fuente', fuente)
    jobs = q.execute().data or []
    apps = client.table('applications').select('job_id,estado,notas').eq('user_id', uid).execute().data or []
    by_job = {a['job_id']: a for a in apps}
    rows = []
    for j in jobs:
        a = by_job.get(j['id'], {})
        j['estado'] = a.get('estado', 'Sin gestionar'); j['notas'] = a.get('notas','')
        if estado and j['estado'] != estado: continue
        rows.append(j)
    return rows


def guardar_estado(job_id_, estado, notas=''):
    row = {'user_id': _uid(), 'job_id': job_id_, 'estado': estado, 'notas': notas, 'updated_at': datetime.now(timezone.utc).isoformat()}
    return client_autenticado().table('applications').upsert(row, on_conflict='user_id,job_id').execute()


def guardar_carta(job_id_, contenido, modo='local'):
    row = {'user_id': _uid(), 'job_id': job_id_, 'modo': modo, 'contenido': contenido, 'updated_at': datetime.now(timezone.utc).isoformat()}
    return client_autenticado().table('letters').upsert(row, on_conflict='user_id,job_id').execute()


def obtener_carta(job_id_):
    res = client_autenticado().table('letters').select('*').eq('user_id', _uid()).eq('job_id', job_id_).limit(1).execute()
    return res.data[0] if res.data else None


def resumen():
    rows = listar_ofertas(0)
    return {'total': len(rows), 'top': sum(r['puntaje'] >= 70 for r in rows), 'postuladas': sum(r['estado']=='Postulada' for r in rows), 'entrevistas': sum(r['estado']=='Entrevista' for r in rows), 'fuentes': _fuentes(rows)}


def _fuentes(rows):
    counts = {}
    for r in rows: counts[r.get('fuente','')]=counts.get(r.get('fuente',''),0)+1
    return [{'fuente': k, 'cantidad': v} for k,v in sorted(counts.items(), key=lambda x:x[1], reverse=True)]
