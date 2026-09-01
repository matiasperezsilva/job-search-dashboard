# Despliegue en Render

El proyecto utiliza un único Web Service Docker para mantener el costo inicial en $0.

El contenedor inicia:

1. FastAPI en `127.0.0.1:8000`.
2. Next.js en el puerto público entregado por Render.
3. Next.js redirige `/api/backend/*` hacia FastAPI internamente.

## Variables requeridas

- `SUPABASE_URL`
- `SUPABASE_PUBLISHABLE_KEY`
- `ENABLE_LINKEDIN=false`

Opcionales para cartas inteligentes:

- `LETTER_API_BASE_URL`
- `LETTER_API_KEY`
- `LETTER_API_MODEL`

El endpoint `/_stcore/health` se conserva como health check por compatibilidad con el servicio de Render ya creado, aunque la aplicación ya no utiliza Streamlit.
