# Estabilización de Rolvora

La base recuperada es `main` en `54fb6517aabd1446ba26ca5bd436cc7563cdc7ce`. Se verificaron los 76 archivos y el árbol de Git. `package.json` declara v5.7.11. La descarga del ZIP histórico falló y el SHA del contenedor público sigue por confirmar. La ejecución histórica de GitHub Actions corresponde al commit de base.

Pasaron 47 pruebas de lógica ejecutables con la biblioteca estándar de Python y el análisis sintáctico de 9 archivos TypeScript/TSX. En PostgreSQL 17 local se aplicaron las cuatro migraciones con cuentas de ensayo y se comprobó el aislamiento por RLS y la unicidad de una corrida activa. La suite completa de pytest, la compilación de Next.js, las auditorías del grafo de dependencias y las capturas de la nueva rama quedan pendientes de un entorno con acceso a los registros de paquetes.

## Búsqueda

`/api/health` en Render devolvió frontend y backend operativos. La interfaz pública mostró el acceso a Rolvora. Esas comprobaciones no prueban el acceso a Supabase, la ejecución autenticada ni la disponibilidad de los portales.

El inicio consultaba tres operaciones de Supabase sin traducir los errores de la dependencia. El proceso en segundo plano podía abandonar la corrida si fallaba la lectura del perfil o el inicio de Chromium. El código ahora registra estado y código de Supabase, aísla errores de las fuentes y diferencia fallos de guardado de fallos del portal. La causa del HTTP 500 histórico queda pendiente del registro de Render y una ejecución autenticada.

| Portal | Acceso en la rama de trabajo | Evidencia y límite |
| --- | --- | --- |
| Get on Board | Feed público con atribución y enlace original | La fuente documenta su feed y se verificó el listado público. El parser tiene una prueba con datos de ejemplo. Queda pendiente validar la respuesta en vivo del feed desde Render y confirmar que entrega ofertas relevantes. |
| LinkedIn | Enlace de búsqueda manual | Sus condiciones prohíben la extracción automatizada sin permiso. |
| Computrabajo | Fichas públicas de su dominio en Chile | La comprobación externa encontró una verificación de acceso. El adaptador se detiene ante un bloqueo. Se debe confirmar el acceso permitido desde Render. |
| ChileTrabajos | Búsqueda y fichas públicas | La portada pública fue accesible. Se debe validar el flujo de extracción desde Render. |
| Trabajando.com | Enlace de búsqueda manual | Sus condiciones restringen el uso de herramientas de búsqueda automatizadas. |
| Laborum | Enlace de búsqueda manual | El listado público fue accesible en navegador. Se requiere confirmar autorización para el endpoint histórico de su frontend antes de reactivar ese adaptador. |
| BNE | Búsqueda pública con enlace manual de respaldo | La ruta histórica mostró respuestas inconsistentes. Se debe confirmar desde Render la obtención de fichas y enlaces oficiales. |

[Documentación de Get on Board](https://www.getonbrd.com/api-doc) · [Condiciones de LinkedIn](https://www.linkedin.com/legal/user-agreement) · [Condiciones de Trabajando.com](https://www.trabajando.cl/terminos-y-condiciones-de-servicio) · [Información de BNE en ChileAtiende](https://www.chileatiende.gob.cl/fichas/5072)

## Seguridad y operación

- El esquema declara RLS por `user_id` para perfiles, ofertas, postulaciones, cartas y búsquedas. Las claves foráneas compuestas aíslan las referencias a ofertas. Queda por comparar las políticas y los permisos de la instancia real, y probarlos con dos cuentas de ensayo.
- FastAPI utiliza el token del usuario y la clave pública de Supabase. El frontend valida que la clave sea publicable. La configuración del proveedor de cartas solo viene del servidor. De forma predeterminada, Gemini recibe una instrucción de cierre genérica y el CV se incorpora al borrador localmente. El análisis ampliado requiere que el operador habilite el envío y que el usuario lo seleccione. [Condiciones de Gemini](https://ai.google.dev/gemini-api/terms)
- El CI de esta rama incluye comprobación de tipos y auditorías de dependencias. Se actualizaron versiones de Next.js, React, FastAPI, python-multipart y pypdf. El árbol original no incluía `package-lock.json`. La resolución y auditoría de dependencias transitivas requieren acceso a los registros de paquetes.
- Una corrida activa utiliza el token de la sesión que la inició. Un reinicio puede interrumpirla y el sistema cierra corridas sin actividad después de 30 minutos. Una cola duradera y un ejecutor separado son la evolución prevista si el volumen lo justifica.

[Notas de seguridad de Next.js](https://nextjs.org/blog/november-2026-security-release) · [Políticas de RLS de Supabase](https://supabase.com/docs/guides/database/postgres/row-level-security)

## Infraestructura y costo

Render Free permite mantener el Docker actual sin cambiar la plataforma. Su arranque en frío fue observable y su documentación confirma la suspensión por inactividad. Para el portafolio conviene documentar esa espera y validar la búsqueda con la instancia caliente. [Límites de Render Free](https://render.com/docs/free)

Una evolución en AWS puede separar Next.js en Amplify Hosting, la API en API Gateway y Lambda, y las corridas en SQS con una Lambda de ejecución. Supabase seguiría encargado de autenticación y persistencia. La ejecución de Chromium requeriría validar memoria, duración y compatibilidad del contenedor. Los créditos del plan gratuito de AWS son temporales y dependen de la elegibilidad de la cuenta. [AWS Free Tier](https://aws.amazon.com/free/free-tier-faqs/)
