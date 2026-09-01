# Job Search Dashboard

Aplicación web para buscar, priorizar y gestionar oportunidades laborales basándose en el currículum del usuario.


### Perfil profesional multipropósito

El motor no está limitado a TI. Al cargar un CV, construye un perfil con áreas, cargos objetivo, competencias y seniority. Si `GEMINI_API_KEY` está configurada, Gemini usa salida JSON estructurada para ampliar la cobertura a profesiones no incluidas en la taxonomía local; si la API no está disponible, existe un analizador local de respaldo. Los cargos objetivo siempre pueden editarse antes de buscar.

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
4. La app crea una corrida en segundo plano y consulta los portales seleccionados de forma secuencial.
5. Antes de puntuar, cada resultado debe validarse como una **vacante individual real**.
6. El matching descarta páginas SEO y vacantes fuera del perfil profesional activo; la evaluación es multiprofesional.
7. Las oportunidades se muestran ordenadas por calce.
8. Cada vacante incluye el botón **Ver oferta / Postular** hacia su publicación original.
9. El usuario puede gestionar estado, notas y carta de presentación.

## Correcciones de relevancia

La versión actual aplica reglas duras antes del scoring:

- `23 Ofertas de trabajo de qa en Tarapacá` → **0 puntos / Descartada**.
- URLs de Computrabajo `/trabajo-de-*` → **no son vacantes**.
- Solo se aceptan detalles de Computrabajo bajo `/ofertas-de-trabajo/oferta-de-trabajo-de-*`.
- QA industrial/minería puede ser relevante para un perfil de calidad industrial y no relevante para un perfil de QA software.
- El contexto profesional del CV determina si una vacante pertenece o no al objetivo del usuario.

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

El despliegue usa `render.yaml` con las siguientes variables:

- `SUPABASE_URL`
- `SUPABASE_PUBLISHABLE_KEY`
- `GEMINI_API_KEY` (secreto para cartas inteligentes)
- `GEMINI_MODEL=gemini-3.5-flash-lite`

El `Dockerfile` inicia Next.js y FastAPI dentro del mismo Web Service, por lo que sigue siendo compatible con el plan Free de Render.

## Base de datos reproducible

El esquema de Supabase se versiona en `supabase/migrations/001_initial_schema.sql` e incluye tablas, índices y políticas RLS.

## Privacidad

El archivo original del CV se procesa en memoria. La información procesada y las oportunidades se almacenan en Supabase con Row Level Security para separar los datos de cada usuario.

## Autor

Matías Pérez.


## Búsquedas en segundo plano

Las búsquedas se crean como corridas persistentes en Supabase. El frontend recibe un identificador inmediatamente y consulta el progreso sin mantener una petición HTTP abierta durante varios minutos. Esto evita timeouts de Render y permite aislar fallos por portal.

## Recuperación de contraseña

La aplicación incluye `¿Olvidaste tu contraseña?` y la ruta pública `/account/update-password`. En Supabase, agrega la URL de producción exacta a **Authentication → URL Configuration → Redirect URLs**:

```text
https://TU-SERVICIO.onrender.com/account/update-password
```

El `Site URL` debe apuntar a la raíz pública de la aplicación.

## Cartas inteligentes con Gemini

El modo **Inteligente · Gemini** usa la Gemini Developer API. En producción solo requiere `GEMINI_API_KEY`; el modelo predeterminado es `gemini-3.5-flash-lite`. La clave se guarda como secreto de Render y nunca se envía al navegador. Antes de enviar el CV al proveedor, la aplicación elimina correos, teléfonos y URLs del texto. El modo local sigue disponible sin ninguna API.

### Matching de experiencia
Cuando el CV permite determinar años de experiencia profesional con suficiente respaldo, el motor los compara con requisitos explícitos de las ofertas. La experiencia es una señal adicional: no sustituye el match de cargo, área y competencias.

### LinkedIn
La integración consulta únicamente páginas públicas de LinkedIn Jobs y no almacena credenciales ni cookies. LinkedIn no ofrece una API pública general de búsqueda de empleos para este caso; por ello la fuente puede limitar consultas automatizadas y, si ocurre, falla de forma aislada sin detener los demás portales.

## Match explicable

El puntaje no es una caja negra. Cada oportunidad guarda y muestra los componentes usados por el motor: coincidencia de cargo, competencias, afinidad del área, años de experiencia, seniority y requisitos adicionales. Las oportunidades evaluadas antes de esta versión pueden regenerar el desglose mediante **Reevaluar base**.

## Preferencias laborales

Además del CV, cada usuario puede definir condiciones personales de búsqueda:

- modalidades aceptadas: remoto, híbrido y/o presencial;
- ubicaciones preferidas;
- renta mínima mensual en CLP.

Estas preferencias son señales adicionales del matching, no filtros absolutos. Si una oferta no publica modalidad, ubicación o renta, ese dato se considera neutral. El desglose de cada oportunidad muestra cuánto aportó o penalizó cada preferencia.

## Curación de oportunidades

La vista de oportunidades permite marcar favoritas, ocultar vacantes que no interesan y restaurarlas posteriormente. Ocultar es una preferencia personal y no equivale a un rechazo de un proceso de selección. Las ofertas ocultas no reaparecen en el listado principal aunque sean encontradas nuevamente por los scrapers.

Cuando una fuente publica una fecha estructurada (`datePosted`), se conserva como `published_at`; si la fuente no la entrega, la interfaz muestra cuándo la aplicación encontró la oferta por primera vez. También se puede ordenar por mejor calce, publicación reciente o descubrimiento reciente.

## Deduplicación y frescura

La vista de oportunidades agrupa de forma conservadora publicaciones equivalentes cuando el cargo y la empresa coinciden claramente y las fechas son cercanas. No se fusionan vacantes sin empresa identificable.

Las ofertas con más de 30 días quedan fuera de la vista principal por defecto para reducir ruido, pero nunca se eliminan. El usuario puede activar **Incluir antiguas**, y las favoritas o con seguimiento se mantienen visibles independientemente de la antigüedad.
