# Job Search Dashboard

Aplicación web para buscar, priorizar y gestionar oportunidades laborales basándose en el currículum del usuario.

## Arquitectura

- **Next.js 16 + React 19**: interfaz web.
- **FastAPI**: API interna y orquestación del motor Python.
- **Playwright + HTTP**: adaptadores de portales laborales.
- **Supabase Auth + PostgreSQL**: autenticación y persistencia por usuario.
- **Render**: despliegue Docker en un único Web Service.

```text
Navegador
   │
   ▼
Next.js / React
   │
   ▼
FastAPI
   │
   ├── CV → perfil / términos
   ├── matching y scoring
   ├── generación de cartas
   └── scrapers
          │
          ▼
     Portales laborales
   │
   ▼
Supabase
```

## Flujo principal

1. El usuario crea una cuenta o inicia sesión.
2. Sube su currículum PDF, DOCX o TXT.
3. El backend extrae áreas, skills y roles de búsqueda.
4. La app consulta los portales seleccionados.
5. Antes de puntuar, cada resultado debe validarse como una **vacante individual real**.
6. El matching descarta páginas SEO, QA/QC industrial y cargos fuera del perfil TI.
7. Las oportunidades se muestran ordenadas por calce.
8. Cada vacante incluye el botón **Ver oferta / Postular** hacia su publicación original.
9. El usuario puede gestionar estado, notas y carta de presentación.

## Correcciones de relevancia

La versión actual aplica reglas duras antes del scoring:

- `23 Ofertas de trabajo de qa en Tarapacá` → **0 puntos / Descartada**.
- URLs de Computrabajo `/trabajo-de-*` → **no son vacantes**.
- Solo se aceptan detalles de Computrabajo bajo `/ofertas-de-trabajo/oferta-de-trabajo-de-*`.
- QA industrial/minería/alimentos/ISO 9001 sin contexto software → descartado.
- QA funcional, tester software, QA automation, APIs, Selenium, Postman, regresión, SDLC, etc. → contexto TI válido.

## Desarrollo local

Necesitas Node.js, Python y Chromium de Playwright.

```bash
npm install
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

Inicia FastAPI:

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

En otra terminal:

```bash
npm run dev
```

## Despliegue en Render

El repositorio mantiene el mismo `render.yaml` y las mismas variables que la versión anterior:

- `SUPABASE_URL`
- `SUPABASE_PUBLISHABLE_KEY`
- `ENABLE_LINKEDIN=false`
- variables opcionales `LETTER_API_*`

El `Dockerfile` inicia Next.js y FastAPI dentro del mismo Web Service, por lo que sigue siendo compatible con el plan Free de Render.

## Privacidad

El archivo original del CV se procesa en memoria. La información procesada y las oportunidades se almacenan en Supabase con Row Level Security para separar los datos de cada usuario.

## Autores

Matías Pérez y colaboradores del proyecto.
