# Arquitectura

## Objetivo

La aplicación convierte un currículum en un perfil de búsqueda dinámico y usa ese perfil tanto para descubrir ofertas como para ordenarlas por relevancia.

## Componentes

### Interfaz web

Streamlit concentra todo el flujo que antes podía requerir scripts independientes: carga de CV, configuración, búsqueda, visualización y seguimiento.

### Procesamiento de CV

`services/cv_profile.py` soporta PDF, DOCX y TXT. El archivo se procesa en memoria y se convierte en un perfil estructurado con:

- áreas profesionales detectadas;
- skills y tecnologías;
- términos de búsqueda;
- penalizaciones y reglas del scoring.

### Recolección

`services/collector.py` recibe los términos generados desde el CV y los entrega a cada adaptador de portal. Los adaptadores son independientes entre sí.

### Matching

`services/scoring.py` compara cada oferta con el perfil activo. El título del cargo tiene más peso que las palabras aisladas de la descripción, reduciendo falsos positivos.

### Persistencia

SQLite almacena ofertas y estados de postulación. El CV original no se almacena.

## Autenticación en portales

No es requisito del núcleo. Para portales que necesiten login, una futura implementación puede aceptar un estado de sesión de Playwright creado previamente por el usuario. Las credenciales no deberían guardarse ni solicitarse directamente desde el scraper.
