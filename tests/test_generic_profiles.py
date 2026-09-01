import unittest
from jobsearch.services.cv_profile import construir_perfil_desde_texto
from jobsearch.services.scoring import evaluar_oferta

class GenericProfileTests(unittest.TestCase):
    def test_enfermeria(self):
        p=construir_perfil_desde_texto('Enfermera clínica con experiencia hospitalaria, pacientes, urgencia y UCI.')
        self.assertIn('Salud / Enfermería', p['resumen']['areas_detectadas'])
        self.assertTrue(any('enfermer' in x for x in p['resumen']['terminos_busqueda']))

    def test_contabilidad(self):
        p=construir_perfil_desde_texto('Contador auditor. Conciliaciones, IFRS, SAP, Excel y facturación.')
        self.assertIn('Finanzas / Contabilidad', p['resumen']['areas_detectadas'])
        self.assertTrue(any('contador' in x or 'auditor' in x for x in p['resumen']['terminos_busqueda']))

    def test_qa_mineria_es_valido_para_perfil_mineria(self):
        p=construir_perfil_desde_texto('Ingeniero QA/QC en minería, faena, ISO 9001, inspección y control de calidad de materiales.')
        j={'titulo':'Ingeniero QA/QC','descripcion':'Minería, faena, ISO 9001 e inspección de materiales','fuente':'ChileTrabajos','link':'https://example.com/job/1'}
        ev=evaluar_oferta(j,p)
        self.assertGreaterEqual(ev['puntaje'], 50)
        self.assertEqual(ev['area'], 'Minería / Calidad industrial')

    def test_qa_mineria_no_calza_con_qa_software(self):
        p=construir_perfil_desde_texto('Analista QA de software con Selenium, Postman, Jira, testing y casos de prueba.')
        j={'titulo':'Ingeniero QA/QC','descripcion':'Minería, faena, ISO 9001 e inspección de materiales','fuente':'ChileTrabajos','link':'https://example.com/job/1'}
        self.assertLess(evaluar_oferta(j,p)['puntaje'], 30)

if __name__=='__main__': unittest.main()
