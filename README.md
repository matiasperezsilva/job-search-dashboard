# Job Search Dashboard

Webapp en Python que analiza un currículum, genera búsquedas de empleo basadas en el perfil detectado, recopila ofertas desde múltiples portales, calcula su nivel de coincidencia y permite gestionar postulaciones y cartas de presentación.

## Funcionalidades

- Registro e inicio de sesión.
- Carga de CV en PDF, DOCX o TXT.
- Extracción automática de áreas, tecnologías y términos de búsqueda.
- Scraping modular con Playwright.
- Scoring CV ↔ oferta.
- Gestión de ofertas y estados de postulación.
- Generación local de cartas de presentación.
- Generación inteligente opcional mediante API compatible con Chat Completions.
- Persistencia en Supabase PostgreSQL.
- Aislamiento de datos por usuario con Row Level Security.
- Docker y Blueprint de Render incluidos.

## Arquitectura

```text
Navegador
   │
   ▼
Render · Streamlit + Playwright/Chromium
   │
   ├── Portales laborales
   │
   └── Supabase
       ├── Auth
       └── PostgreSQL + RLS
```

## Desarrollo local

```bash
python -m venv .venv
pip install -r requirements.txt
playwright install chromium
```

Copia `.env.example` a `.env`, configura Supabase y ejecuta:

```bash
streamlit run streamlit_app.py
```

## Despliegue

Consulta [`docs/despliegue_render.md`](docs/despliegue_render.md).

## Privacidad

El archivo original del CV se procesa en memoria y no se almacena. La aplicación guarda el texto extraído y el perfil derivado en la cuenta del usuario para permitir matching y generación de cartas. Las tablas están protegidas mediante RLS.

## Tecnologías

Python · Streamlit · Playwright · Chromium · Supabase · PostgreSQL · Docker · Render · GitHub Actions

## Licencia

MIT.

## Mejoras de experiencia y rendimiento

La versión actual incorpora un modo de búsqueda rápida optimizado para hosting gratuito en Render: limita términos y resultados por portal, bloquea recursos visuales innecesarios en Chromium, evita esperas `networkidle` y muestra progreso/tiempos por fuente. GetOnBoard consulta sus categorías técnicas públicas para reducir dependencia del buscador JavaScript.

La interfaz utiliza una capa visual personalizada sobre Streamlit con dashboard, navegación lateral, tarjetas, estados y vistas más orientadas a producto.

## Calidad de resultados

La aplicación aplica una validación de relevancia antes del scoring. Las búsquedas usan nombres de cargos en lugar de tecnologías aisladas y los roles QA ambiguos requieren señales de software/TI. Páginas de resultados, QA/QC industrial, minería, construcción, alimentos y otros contextos de calidad no tecnológicos se descartan.

GetOnBoard y Computrabajo utilizan consultas HTTP sobre contenido público para reducir consumo de recursos en Render. Las demás fuentes mantienen adaptadores aislados para que el fallo de un portal no detenga toda la búsqueda.

