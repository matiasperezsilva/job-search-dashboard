# Despliegue en Render

El proyecto utiliza un único Web Service Docker para mantener el costo inicial en $0.

El contenedor inicia:

1. FastAPI en `127.0.0.1:8000`.
2. Next.js en el puerto público entregado por Render.
3. Next.js redirige `/api/backend/*` hacia FastAPI internamente.
4. Render comprueba `/api/health`; ese endpoint solo responde `200` cuando Next.js **y** FastAPI están disponibles.

## Variables requeridas

- `SUPABASE_URL`
- `SUPABASE_PUBLISHABLE_KEY`
- `ENABLE_LINKEDIN=false`

Opcionales para cartas inteligentes:

- `GEMINI_API_KEY`
- `GEMINI_MODEL=gemini-3.5-flash-lite`

## Supabase Auth

En **Authentication → URL Configuration**:

- `Site URL`: URL raíz de producción en Render.
- Redirect URL permitida: `https://TU-SERVICIO.onrender.com/account/update-password`.

Nunca agregues `service_role`, contraseñas ni API keys privadas al repositorio.

## Base de datos

El esquema reproducible está versionado en:

```text
supabase/migrations/001_initial_schema.sql
```

Incluye tablas, claves foráneas, índices y políticas RLS.
