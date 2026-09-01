from jobsearch.scrapers.common import titulo_parece_relevante, es_relevante_perfil


def test_phrase_terms_do_not_hide_valid_qa_title():
    terms = ["qa software", "qa tester"]
    assert titulo_parece_relevante("Analista QA", terms)
    assert titulo_parece_relevante("Analista QA Funcional", terms)
    assert es_relevante_perfil("QA Engineer", "Testing de software", terms)


def test_phrase_terms_do_not_hide_valid_cloud_title():
    assert titulo_parece_relevante("Cloud Engineer Junior", ["cloud support", "operaciones cloud"])


def test_unrelated_title_stays_out_of_prefilter():
    assert not titulo_parece_relevante("Enfermero UCI", ["analista qa", "qa tester"])
