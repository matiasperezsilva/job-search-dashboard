# Rolvora

**Career match workspace** — analiza tu CV, encuentra oportunidades multiprofesionales, explica el calce y organiza cada postulación.

Aplicación web para buscar, priorizar y gestionar oportunidades laborales basándose en el currículum del usuario.


### Perfil profesional multipropósito

Al cargar un CV, Rolvora extrae experiencia, áreas, competencias y menciones de certificaciones. El análisis local funciona con cualquier perfil y permite editar los cargos objetivo. Si el administrador habilita el envío de texto a Gemini bajo condiciones de tratamiento compatibles, cada persona puede optar por ampliar el análisis. Los años de experiencia se calculan con la evidencia del CV.

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

Copia `.env.example` a `.env`. Usa Python 3.12, Node.js 22 y un proyecto Supabase de desarrollo con todas las migraciones aplicadas en orden.

Inicia FastAPI:

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --env-file .env
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

Aplica en orden los archivos de `supabase/migrations/`. Incluyen tablas, índices, políticas RLS y el índice que limita a una búsqueda activa por cuenta.

## Privacidad

El archivo del CV se procesa durante la solicitud. Supabase conserva el texto extraído y el perfil. El análisis con Gemini requiere elegirlo al subir el CV. La información procesada y las oportunidades se almacenan en Supabase con Row Level Security para separar los datos de cada usuario.

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

El modo **Inteligente · Gemini** usa la Gemini Developer API. En producción solo requiere `GEMINI_API_KEY`; el modelo predeterminado es `gemini-3.5-flash-lite`. La clave se guarda como secreto de Render y nunca se envía al navegador. Por defecto Gemini redacta una frase de cierre sin recibir el CV ni los datos de la oferta. Rolvora personaliza el resto de la carta localmente. `GEMINI_ALLOW_CV_TEXT` habilita el análisis ampliado y la generación desde texto con datos de contacto omitidos cuando las condiciones del proveedor permiten ese tratamiento.

### Matching de experiencia
Cuando el CV permite determinar años de experiencia profesional con suficiente respaldo, el motor los compara con requisitos explícitos de las ofertas. La experiencia es una señal adicional: no sustituye el match de cargo, área y competencias.

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

## Cuenta y seguridad

La administración de contraseña vive en una sección independiente del currículum. El perfil profesional contiene únicamente CV, cargos objetivo y preferencias laborales.

## Robustez de portales

Los adaptadores aceptan enlaces relativos o absolutos y usan un prefiltro permisivo por tokens. El scoring completo sigue siendo la autoridad final para decidir si una vacante es relevante. Las fuentes que responden sin coincidencias se muestran de forma distinta a las fuentes que fallan.

## Cálculo de experiencia profesional

El motor calcula experiencia desde rangos de fechas dentro del bloque de experiencia laboral, fusiona períodos superpuestos y excluye expresamente proyectos de título, tesis y proyectos académicos del total profesional. Si el CV declara menos de un año, la interfaz muestra meses.

El score explicable limita primero las señales positivas a 100 y luego aplica penalizaciones. De esta forma una incompatibilidad visible —por ejemplo, modalidad presencial cuando el usuario solo acepta remoto— siempre reduce el puntaje final.

## Guardado verificable de cartas

Los borradores de cartas se almacenan en Supabase por usuario y oferta. La interfaz muestra el estado del guardado y verifica el contenido persistido mediante una relectura posterior, evitando confirmaciones falsas o errores silenciosos.

## Diagnóstico de fuentes

La búsqueda distingue entre ausencia de coincidencias y fallos técnicos del portal. Cada adaptador puede informar enlaces detectados, fichas extraídas, descartes por matching, errores de extracción, errores de consulta y bloqueos anti-bot. Esto evita presentar un `0` ambiguo como si necesariamente significara que el portal no tiene vacantes.

## Gestión de postulaciones

La sección de seguimiento permite editar el estado y las notas de cada proceso. Si una vacante fue marcada por error, **Quitar seguimiento** elimina únicamente el registro de seguimiento y devuelve la oferta a Oportunidades como `Sin gestionar`; la vacante no se elimina de la base.

## Fuentes de empleo

Get on Board utiliza su feed público. Computrabajo, ChileTrabajos y BNE conservan adaptadores de páginas públicas que se detienen ante restricciones de acceso detectadas. LinkedIn, Trabajando.com y Laborum se abren en sus portales. La [auditoría de estabilización](docs/estabilizacion.md) registra el estado de cada integración.

## Ejemplo de perfil individual

En **Perfil → Cargos objetivo**, un perfil orientado a AWS puede guardar `AWS Cloud Support, Cloud Engineer Junior, Cloud Operations, Cloud Analyst, DevOps Junior, Infraestructura TI, QA Cloud, SDET`. La certificación AWS Certified Cloud Practitioner y la experiencia en QA, bases de datos y operaciones TI se incorporan al cargar un CV donde figuren esos antecedentes. Los cargos y preferencias se guardan en la cuenta que los configura.

## Validación

Desde la raíz, instala `requirements-dev.txt`, configura `PYTHONPATH=src:.` en Linux o `PYTHONPATH=src;.` en Windows y ejecuta `python -m pytest -q`. El frontend se valida con `npm run typecheck` y `npm run build`. GitHub Actions ejecuta las pruebas, la compilación y las auditorías de dependencias. La [guía de Render](docs/despliegue_render.md) describe el despliegue y su verificación.
