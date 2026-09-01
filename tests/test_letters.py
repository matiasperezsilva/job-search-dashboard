import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import unittest

from jobsearch.services.letters import coincidencias_cv_oferta, generar_borrador_local, _extraer_contenido_chat


class TestLetters(unittest.TestCase):
    def setUp(self):
        self.perfil = {
            "resumen": {"skills_detectadas": ["Postman", "SQL", "AWS", "Selenium"]},
            "areas": {},
        }
        self.oferta = {
            "titulo": "Analista QA",
            "empresa": "Empresa Demo",
            "area": "QA / Testing",
            "descripcion": "Buscamos experiencia con Postman y SQL para pruebas de API.",
        }

    def test_coincidencias_solo_presentes_en_oferta(self):
        hits = coincidencias_cv_oferta(self.perfil, self.oferta)
        self.assertIn("Postman", hits)
        self.assertIn("SQL", hits)
        self.assertNotIn("AWS", hits)

    def test_borrador_local_usa_coincidencias_reales(self):
        carta = generar_borrador_local(self.oferta, self.perfil)
        self.assertIn("Postman", carta)
        self.assertIn("SQL", carta)
        self.assertNotIn("AWS", carta)
        self.assertIn("Empresa Demo", carta)

    def test_parse_chat_completions(self):
        data = {"choices": [{"message": {"content": "Carta lista"}}]}
        self.assertEqual(_extraer_contenido_chat(data), "Carta lista")


if __name__ == "__main__":
    unittest.main()


def test_sanitiza_contacto_antes_de_ia():
    from jobsearch.services.letters import _sanitizar_cv_para_ia
    texto = "Matías correo test@example.com teléfono +56 9 1234 5678 https://linkedin.com/in/test"
    limpio = _sanitizar_cv_para_ia(texto)
    assert "test@example.com" not in limpio
    assert "1234 5678" not in limpio
    assert "linkedin.com" not in limpio


def test_parse_gemini_content():
    from jobsearch.services.letters import _extraer_contenido_gemini
    data = {"candidates": [{"content": {"parts": [{"text": "Carta de prueba"}]}}]}
    assert _extraer_contenido_gemini(data) == "Carta de prueba"
