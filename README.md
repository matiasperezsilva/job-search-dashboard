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
