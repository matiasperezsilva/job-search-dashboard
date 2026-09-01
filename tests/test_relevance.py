import unittest
from jobsearch.scrapers.common import es_relevante_perfil, es_pagina_busqueda


class RelevanceTests(unittest.TestCase):
    def test_rechaza_pagina_seo_computrabajo(self):
        self.assertTrue(es_pagina_busqueda('Ofertas de trabajo de qa en Tarapacá'))
        self.assertFalse(es_relevante_perfil('Ofertas de trabajo de qa en Tarapacá', ''))

    def test_rechaza_qa_mineria(self):
        self.assertFalse(es_relevante_perfil(
            'Ingeniero de Aseguramiento y Control de Calidad QA/QC',
            'Proyecto de minería, ISO 9001, inspección en faena y control de materiales.'
        ))

    def test_rechaza_calidad_alimentos(self):
        self.assertFalse(es_relevante_perfil(
            'Analista de control de calidad',
            'Planta de alimentos, HACCP, BPM y laboratorio.'
        ))

    def test_acepta_qa_software(self):
        self.assertTrue(es_relevante_perfil(
            'Analista QA Funcional',
            'Pruebas de aplicaciones web, APIs REST con Postman, casos de prueba, Jira y regresión.'
        ))

    def test_acepta_qa_junior(self):
        self.assertTrue(es_relevante_perfil(
            'QA Junior',
            'Validación de aplicaciones backend y frontend, testing funcional y reporte de defectos.'
        ))


if __name__ == '__main__':
    unittest.main()
