# Arquitectura V5

La aplicación separa la experiencia web del motor de búsqueda para evitar que los scrapers condicionen la interfaz.

```text
                        Render Web Service
                              │
                 ┌────────────┴────────────┐
                 │                         │
              Next.js                  FastAPI
              React UI                   API
                 │                         │
                 │                  Background task
                 │                         │
                 │                  Motor Python
                 │             ┌───────────┼───────────┐
                 │             ▼           ▼           ▼
                 │         CV parser    Scoring     Scrapers
                 │                                     │
                 │                                     ▼
                 │                               Portales empleo
                 │
                 └──────────────────┬──────────────────┘
                                    ▼
                                Supabase
                     Auth + PostgreSQL + RLS
```

## Búsquedas asíncronas

El endpoint `POST /search` ya no espera a que terminen todos los portales. Crea una fila en `search_runs`, responde inmediatamente con un `run_id` y ejecuta la recolección en segundo plano.

React consulta `GET /search/{run_id}` cada pocos segundos. El estado persiste en Supabase y contiene progreso por portal, resultados y errores aislados.

Esto evita mantener una petición HTTP abierta durante varios minutos y reduce los timeouts en Render Free.

## Matching

El pipeline aplica validación antes del scoring:

1. comprobar que la URL corresponde a una vacante individual;
2. descartar páginas SEO/listados;
3. separar QA de software de QA/QC industrial;
4. descartar roles comerciales y fuera de objetivo;
5. exigir coincidencia de cargo en portales generalistas;
6. recién entonces calcular el puntaje contra el perfil extraído del CV.

## Seguridad

El navegador autentica mediante Supabase Auth. Cada llamada a FastAPI incluye el `access_token` del usuario. FastAPI valida la sesión contra Supabase y consulta PostgreSQL usando ese mismo JWT.

Todas las tablas públicas de la aplicación tienen Row Level Security y políticas de propiedad por `user_id`. No se utiliza `service_role` en el frontend ni en FastAPI.
