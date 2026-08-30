# Despliegue gratuito en Render + Supabase

La aplicación está preparada para ejecutarse como Web Service Docker en Render y usar Supabase para autenticación y persistencia.

## Variables requeridas

- `SUPABASE_URL`
- `SUPABASE_PUBLISHABLE_KEY`

## Variables opcionales

- `ENABLE_LINKEDIN=false`
- `LETTER_API_BASE_URL`
- `LETTER_API_KEY`
- `LETTER_API_MODEL`

## Render

El repositorio incluye `render.yaml`. Crea un Blueprint desde el repositorio, selecciona el plan Free y carga las dos variables de Supabase. Render construirá la imagen Docker, instalará Chromium mediante Playwright y expondrá la aplicación usando el puerto asignado por Render.

El health check está configurado en `/_stcore/health`.

## Persistencia

El contenedor no almacena datos importantes. CV procesado, perfil, ofertas, estados y cartas se guardan en Supabase y están aislados por usuario mediante Row Level Security (RLS).
