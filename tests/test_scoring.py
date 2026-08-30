import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from jobsearch.services.scoring import evaluar_oferta


class ScoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.perfil = json.loads((ROOT / "config/perfil.example.json").read_text(encoding="utf-8"))

    def test_qa_scores_high(self):
        oferta = {
            "titulo": "Analista QA Funcional",
            "descripcion": "pruebas funcionales, regresión, UAT y gestión de defectos",
        }
        self.assertGreaterEqual(evaluar_oferta(oferta, self.perfil)["puntaje"], 70)

    def test_sales_cloud_is_rejected(self):
        oferta = {
            "titulo": "Ejecutivo Comercial Cloud",
            "descripcion": "venta de soluciones AWS y Azure",
        }
        self.assertLessEqual(evaluar_oferta(oferta, self.perfil)["puntaje"], 15)

    def test_senior_penalty(self):
        junior = evaluar_oferta(
            {"titulo": "DBA Junior", "descripcion": "SQL Server Oracle Linux"}, self.perfil
        )["puntaje"]
        senior = evaluar_oferta(
            {"titulo": "DBA Senior", "descripcion": "SQL Server Oracle Linux"}, self.perfil
        )["puntaje"]
        self.assertGreater(junior, senior)


if __name__ == "__main__":
    unittest.main()
