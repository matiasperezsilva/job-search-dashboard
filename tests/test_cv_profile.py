import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import unittest
from jobsearch.services.cv_profile import construir_perfil_desde_texto


class CVProfileTests(unittest.TestCase):
    def test_cv_qa_cloud_generates_relevant_terms(self):
        texto = """
        Ingeniero en Informática. Analista QA con experiencia en pruebas funcionales,
        Postman, Selenium, SQL y Jira. Formación en AWS, Linux, EC2, S3 e IAM.
        """
        perfil = construir_perfil_desde_texto(texto)
        resumen = perfil["resumen"]
        self.assertIn("QA / Testing", resumen["areas_detectadas"])
        self.assertIn("Cloud / Operaciones", resumen["areas_detectadas"])
        self.assertIn("postman", resumen["skills_detectadas"])
        self.assertTrue(any(t in resumen["terminos_busqueda"] for t in ["qa", "tester", "analista qa"]))

    def test_sales_is_not_created_as_target_area(self):
        perfil = construir_perfil_desde_texto("Ejecutivo comercial de ventas B2B y marketing")
        self.assertNotIn("Ventas", perfil["areas"])


if __name__ == "__main__":
    unittest.main()
