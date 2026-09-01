import unittest
from jobsearch.scrapers.common import es_relevante_perfil, es_pagina_busqueda


class RelevanceTests(unittest.TestCase):
    def test_rechaza_pagina_seo_computrabajo(self):
        self.assertTrue(es_pagina_busqueda('Ofertas de trabajo de qa en Tarapacá'))
        self.assertFalse(es_relevante_perfil('Ofertas de trabajo de qa en Tarapacá', ''))

    def test_rechaza_qa_mineria(self):
        self.assertTrue(es_relevante_perfil(
            'Ingeniero de Aseguramiento y Control de Calidad QA/QC',
            'Proyecto de minería, ISO 9001, inspección en faena y control de materiales.'
        ))

    def test_rechaza_calidad_alimentos(self):
        self.assertTrue(es_relevante_perfil(
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

    def test_pagina_seo_con_numero_se_descarta(self):
        self.assertTrue(es_pagina_busqueda('23 Ofertas de trabajo de qa en Tarapacá'))
        self.assertTrue(es_pagina_busqueda('91 Empleos de qa Jornada extraordinaria'))

    def test_computrabajo_listing_url_no_es_vacante(self):
        from jobsearch.scrapers.common import oferta_es_valida
        self.assertFalse(oferta_es_valida({'titulo':'Coordinador QA','fuente':'Computrabajo','link':'https://cl.computrabajo.com/trabajo-de-qa'}))
        self.assertTrue(oferta_es_valida({'titulo':'Coordinador QA Automatizador','fuente':'Computrabajo','link':'https://cl.computrabajo.com/ofertas-de-trabajo/oferta-de-trabajo-de-coordinador-qa-abc'}))

    def test_getonboard_job_urls_son_validas(self):
        from jobsearch.scrapers.common import oferta_es_valida
        self.assertTrue(oferta_es_valida({
            "titulo": "QA Funcional",
            "fuente": "GetOnBoard",
            "link": "https://www.getonbrd.com/empleos/sysadmin-devops-qa/qa-funcional-empresa-santiago",
        }))
        self.assertTrue(oferta_es_valida({
            "titulo": "QA Engineer",
            "fuente": "GetOnBoard",
            "link": "https://www.getonbrd.cl/jobs/sysadmin-devops-qa/qa-engineer-empresa",
        }))



if __name__ == '__main__':
    unittest.main()
