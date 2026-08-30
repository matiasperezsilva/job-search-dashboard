import sqlite3
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from jobsearch.config import DB_PATH


class ConexionSQLite(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()



def conectar(db_path=None):
    path = Path(db_path or DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, factory=ConexionSQLite)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    return con


def inicializar(db_path=None):
    with conectar(db_path) as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS jobs(
              id TEXT PRIMARY KEY,
              titulo TEXT NOT NULL,
              empresa TEXT,
              descripcion TEXT,
              modalidad TEXT,
              link TEXT,
              fuente TEXT,
              puntaje INTEGER DEFAULT 0,
              area TEXT,
              razon TEXT,
              first_seen TEXT NOT NULL,
              last_seen TEXT NOT NULL,
              UNIQUE(titulo, empresa, fuente)
            );
            CREATE TABLE IF NOT EXISTS applications(
              job_id TEXT PRIMARY KEY,
              estado TEXT NOT NULL DEFAULT 'Guardada',
              notas TEXT DEFAULT '',
              updated_at TEXT NOT NULL,
              FOREIGN KEY(job_id) REFERENCES jobs(id)
            );
            CREATE TABLE IF NOT EXISTS runs(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              started_at TEXT NOT NULL,
              finished_at TEXT,
              sources TEXT,
              found INTEGER DEFAULT 0,
              errors TEXT DEFAULT '[]'
            );
            CREATE TABLE IF NOT EXISTS letters(
              job_id TEXT PRIMARY KEY,
              modo TEXT NOT NULL DEFAULT 'local',
              contenido TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY(job_id) REFERENCES jobs(id)
            );
        """)


def job_id(oferta):
    raw = "|".join(str(oferta.get(k, "")) for k in ("titulo", "empresa", "fuente"))
    return hashlib.sha1(raw.lower().strip().encode("utf-8")).hexdigest()[:16]


def guardar_ofertas(ofertas, perfil, evaluador, db_path=None):
    ahora = datetime.now(timezone.utc).isoformat()
    nuevas = 0
    with conectar(db_path) as con:
        for oferta in ofertas:
            ev = evaluador(oferta, perfil)
            jid = job_id(oferta)
            existe = con.execute("SELECT 1 FROM jobs WHERE id=?", (jid,)).fetchone()
            con.execute(
                """
                INSERT INTO jobs(
                    id,titulo,empresa,descripcion,modalidad,link,fuente,
                    puntaje,area,razon,first_seen,last_seen
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    descripcion=excluded.descripcion,
                    modalidad=excluded.modalidad,
                    link=excluded.link,
                    puntaje=excluded.puntaje,
                    area=excluded.area,
                    razon=excluded.razon,
                    last_seen=excluded.last_seen
                """,
                (
                    jid,
                    oferta.get("titulo", ""),
                    oferta.get("empresa", ""),
                    oferta.get("descripcion", ""),
                    oferta.get("modalidad", ""),
                    oferta.get("link", ""),
                    oferta.get("fuente", ""),
                    ev["puntaje"],
                    ev["area"],
                    ev["razon"],
                    ahora,
                    ahora,
                ),
            )
            if not existe:
                nuevas += 1
    return nuevas


def listar_ofertas(min_score=0, fuente=None, estado=None, db_path=None):
    q = """
        SELECT j.*, COALESCE(a.estado,'Sin gestionar') estado,
               COALESCE(a.notas,'') notas
        FROM jobs j
        LEFT JOIN applications a ON a.job_id=j.id
        WHERE j.puntaje>=?
    """
    args = [min_score]
    if fuente:
        q += " AND j.fuente=?"
        args.append(fuente)
    if estado:
        q += " AND COALESCE(a.estado,'Sin gestionar')=?"
        args.append(estado)
    q += " ORDER BY j.puntaje DESC, j.last_seen DESC"
    with conectar(db_path) as con:
        return [dict(r) for r in con.execute(q, args).fetchall()]


def guardar_estado(job_id_, estado, notas="", db_path=None):
    ahora = datetime.now(timezone.utc).isoformat()
    with conectar(db_path) as con:
        con.execute(
            """
            INSERT INTO applications(job_id,estado,notas,updated_at)
            VALUES(?,?,?,?)
            ON CONFLICT(job_id) DO UPDATE SET
                estado=excluded.estado,
                notas=excluded.notas,
                updated_at=excluded.updated_at
            """,
            (job_id_, estado, notas, ahora),
        )


def resumen(db_path=None):
    with conectar(db_path) as con:
        total = con.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        top = con.execute("SELECT COUNT(*) FROM jobs WHERE puntaje>=70").fetchone()[0]
        postuladas = con.execute("SELECT COUNT(*) FROM applications WHERE estado='Postulada'").fetchone()[0]
        entrevistas = con.execute("SELECT COUNT(*) FROM applications WHERE estado='Entrevista'").fetchone()[0]
        fuentes = [
            dict(r)
            for r in con.execute(
                "SELECT fuente,COUNT(*) cantidad FROM jobs GROUP BY fuente ORDER BY cantidad DESC"
            )
        ]
    return {
        "total": total,
        "top": top,
        "postuladas": postuladas,
        "entrevistas": entrevistas,
        "fuentes": fuentes,
    }


def guardar_carta(job_id_, contenido, modo="local", db_path=None):
    ahora = datetime.now(timezone.utc).isoformat()
    with conectar(db_path) as con:
        con.execute(
            """
            INSERT INTO letters(job_id,modo,contenido,updated_at)
            VALUES(?,?,?,?)
            ON CONFLICT(job_id) DO UPDATE SET
                modo=excluded.modo,
                contenido=excluded.contenido,
                updated_at=excluded.updated_at
            """,
            (job_id_, modo, contenido, ahora),
        )


def obtener_carta(job_id_, db_path=None):
    with conectar(db_path) as con:
        row = con.execute(
            "SELECT job_id,modo,contenido,updated_at FROM letters WHERE job_id=?",
            (job_id_,),
        ).fetchone()
    return dict(row) if row else None
