# Mejoras implementadas

La versión anterior cumplía su objetivo, pero había crecido como una cadena de scripts independientes y archivos intermedios. La refactorización prioriza mantenibilidad, portabilidad y una presentación adecuada para portafolio.

## Cambios principales

- Archivos JSON usados como estado principal → **SQLite**.
- Scripts separados de generación de tablas/reportes → **servicios reutilizables**.
- Filtro de relevancia basado en coincidencias sueltas → **clasificación más conservadora por título y área**.
- Puntaje dependiente de un servicio externo → **motor determinístico y configurable**.
- Ejecución dependiente de rutas de Windows → **rutas relativas y configuración por entorno**.
- Entorno virtual incluido dentro del proyecto → **`requirements.txt` + `.gitignore`**.
- Flujo solo por consola → **webapp multipágina**.
- Historial difícil de gestionar → **estados de postulación persistentes**.
- Sin pruebas automatizadas → **tests unitarios + GitHub Actions**.
- Archivos temporales y datos personales mezclados con código → **separación de configuración pública/local**.

## Compatibilidad con la versión anterior

`scripts/importar_legacy.py` permite cargar un `ofertas.json` anterior y, opcionalmente, conservar evaluaciones históricas desde `comparacion_cv.json`.
