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

    def test_pagina_seo_computrabajo_siempre_es_cero(self):
        oferta = {
            "titulo": "23 Ofertas de trabajo de qa en Tarapacá",
            "descripcion": "qa tester software",
            "fuente": "Computrabajo",
            "link": "https://cl.computrabajo.com/trabajo-de-qa-en-tarapaca",
        }
        resultado = evaluar_oferta(oferta, self.perfil)
        self.assertEqual(resultado["puntaje"], 0)
        self.assertEqual(resultado["area"], "Descartada")

    def test_qa_industrial_computrabajo_es_cero(self):
        oferta = {
            "titulo": "Supervisor QA QC",
            "descripcion": "minería, faena, ISO 9001, control de calidad e inspección",
            "fuente": "Computrabajo",
            "link": "https://cl.computrabajo.com/ofertas-de-trabajo/oferta-de-trabajo-de-supervisor-qa-qc-abc",
        }
        self.assertEqual(evaluar_oferta(oferta, self.perfil)["puntaje"], 0)

    def test_generalista_no_sube_por_skills_sin_cargo_objetivo(self):
        oferta = {
            "titulo": "Coordinador de Operaciones Comerciales",
            "descripcion": "Uso de SQL, Jira, APIs REST, Linux y AWS para coordinar procesos.",
            "fuente": "Computrabajo",
            "link": "https://cl.computrabajo.com/ofertas-de-trabajo/oferta-de-trabajo-de-coordinador-operaciones-abc",
        }
        self.assertLess(evaluar_oferta(oferta, self.perfil)["puntaje"], 30)



if __name__ == "__main__":
    unittest.main()
