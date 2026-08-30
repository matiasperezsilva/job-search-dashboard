"""Importa ofertas del formato JSON utilizado por la versión anterior."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jobsearch.config import cargar_perfil
from jobsearch.services.scoring import evaluar_oferta
from jobsearch.services.storage import inicializar, guardar_ofertas, conectar


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("ofertas", type=Path, help="Ruta al archivo ofertas.json anterior")
    parser.add_argument("--comparacion", type=Path, help="Ruta opcional a comparacion_cv.json")
    args = parser.parse_args()

    ofertas = json.loads(args.ofertas.read_text(encoding="utf-8-sig"))
    inicializar()
    nuevas = guardar_ofertas(ofertas, cargar_perfil(), evaluar_oferta)
    print(f"Importadas {len(ofertas)} ofertas ({nuevas} nuevas).")

    if args.comparacion and args.comparacion.exists():
        comp = json.loads(args.comparacion.read_text(encoding="utf-8-sig"))
        mapa = {(x.get("titulo"), x.get("empresa"), x.get("fuente")): x for x in comp}
        actualizadas = 0
        with conectar() as con:
            rows = con.execute("SELECT id,titulo,empresa,fuente FROM jobs").fetchall()
            for row in rows:
                antiguo = mapa.get((row["titulo"], row["empresa"], row["fuente"]))
                if antiguo:
                    con.execute(
                        "UPDATE jobs SET puntaje=?, razon=? WHERE id=?",
                        (antiguo.get("puntaje", 0), antiguo.get("razon", ""), row["id"]),
                    )
                    actualizadas += 1
        print(f"Se conservaron {actualizadas} evaluaciones históricas.")


if __name__ == "__main__":
    main()
