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

Opcionales para cartas inteligentes:

- `GEMINI_API_KEY`
- `GEMINI_MODEL=gemini-3.5-flash-lite`

## Supabase Auth

En **Authentication → URL Configuration**:

- `Site URL`: URL raíz de producción en Render.
- Redirect URL permitida: `https://TU-SERVICIO.onrender.com/account/update-password`.

Nunca agregues `service_role`, contraseñas ni API keys privadas al repositorio.

## Base de datos

Aplica los archivos de `supabase/migrations/` en orden, primero en una base de ensayo. La migración `004` conserva las corridas históricas y cierra las duplicadas que aún figuren activas antes de crear el índice único.

Incluye tablas, claves foráneas, índices y políticas RLS.


## Verificación previa a publicar

1. Confirma el SHA que Render muestra para el despliegue activo. La versión nueva también incluye el SHA abreviado en `/api/health` cuando Render proporciona `RENDER_GIT_COMMIT`.
2. Con un Supabase de ensayo, prueba la búsqueda con un CV ficticio y confirma que `POST /api/backend/search` devuelve un identificador y que su progreso llega a un estado final.
3. Prueba con dos cuentas la separación de perfil, ofertas, postulaciones, cartas y búsquedas. Confirma recuperación de contraseña con la URL de ensayo.
4. Ante un error al iniciar, revisa en Render las entradas `Supabase error` del momento de la solicitud. El recurso, estado HTTP y código permiten diferenciar problemas de sesión, esquema, permisos y conectividad.

`GET /api/health` verifica ambos procesos. La búsqueda autenticada comprueba además Supabase y el acceso a las fuentes. Render Free suspende el servicio por inactividad y puede interrumpir procesos en segundo plano durante reinicios.
