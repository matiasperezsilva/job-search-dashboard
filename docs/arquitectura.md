# Arquitectura V4

La interfaz Streamlit fue reemplazada por **Next.js/React**. El motor de scraping y matching continúa en Python para aprovechar los adaptadores existentes y evitar una reescritura innecesaria.

```text
                    Render Web Service
                          │
             ┌────────────┴────────────┐
             │                         │
          Next.js                  FastAPI
          React UI                   API
             │                         │
             └──────────┬──────────────┘
                        │
                      Python
             ┌──────────┼──────────┐
             ▼          ▼          ▼
         CV parser   Scoring    Scrapers
                        │          │
                        │          ▼
                        │     Portales empleo
                        ▼
                    Supabase
                Auth + PostgreSQL
```

## Motivo del cambio

Streamlit permitió validar rápidamente el flujo, pero limitaba demasiado la calidad visual y la interacción. Next.js permite controlar completamente layout, navegación, tarjetas, paneles de detalle, estados responsive y acciones de postulación.

## Seguridad

El navegador autentica mediante Supabase Auth. Cada llamada a FastAPI incluye el `access_token` del usuario. FastAPI valida el token contra Supabase y usa el mismo JWT en las consultas REST, por lo que las políticas RLS existentes siguen separando los datos por usuario.
