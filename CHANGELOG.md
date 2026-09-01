## 5.7.3 — Release CI
- GitHub Actions ahora ejecuta realmente toda la suite con `pytest`.
- Se agregó `requirements-dev.txt` para dependencias de validación.
- Render queda configurado para desplegar solo después de que los checks de CI pasen.
- No cambia la lógica funcional de la aplicación.

## 5.7.2 — Password verification
- El cambio de contraseña ahora valida realmente la contraseña actual usando `current_password`.
- Requiere `supabase-js` 2.102.0+; el proyecto usa 2.112.4.

## 5.7.1 — Release docs
- Se actualizó el README para reflejar el motor multiprofesional actual.
- Se eliminó la referencia obsoleta a `ENABLE_LINKEDIN`.
- No cambia lógica de aplicación ni base de datos.

## 5.7.0 — Hardening de oportunidades
- Deduplicación conservadora de la misma vacante publicada en varios portales.
- Una oportunidad duplicada muestra cuántas fuentes la detectaron.
- Solo se fusionan cargo + empresa claramente coincidentes y publicaciones temporalmente cercanas.
- Las ofertas sin empresa identificable no se fusionan para evitar falsos positivos.
- Las oportunidades antiguas (más de 30 días) quedan fuera de la vista principal por defecto.
- Favoritos y ofertas con seguimiento nunca se ocultan automáticamente por antigüedad.
- Se añadió el control “Incluir antiguas”.
- El detalle de una oferta duplicada muestra todas las fuentes en las que fue detectada.
- La generación de cartas puede seguir accediendo a oportunidades ocultas/antiguas.
- 50 pruebas automatizadas aprobadas.

## 5.6.0 — Curación y frescura de oportunidades
- Favoritos independientes del estado de postulación.
- Ocultar/restaurar ofertas sin confundirlas con rechazos de procesos.
- Las ofertas ocultas permanecen ocultas aunque vuelvan a aparecer en búsquedas futuras.
- Fechas de publicación cuando el portal entrega `datePosted`; fallback visual a fecha encontrada.
- Orden por mejor calce, publicación reciente o fecha encontrada.
- Vista separada de Oportunidades, Favoritas y Ocultas.
- Identidad de vacantes basada preferentemente en el enlace individual, evitando fusionar publicaciones distintas del mismo cargo/empresa.
- Persistencia de `favorite`, `hidden`, `hidden_at` y `published_at` en Supabase.
- Nueva migración `003_job_curation_and_dates.sql`.
- 45 pruebas automatizadas aprobadas.

## 5.5.0 — Preferencias laborales en el match
- El perfil permite configurar modalidades aceptadas: remoto, híbrido y presencial.
- Se pueden definir ubicaciones preferidas sin convertirlas en filtros destructivos.
- Se puede indicar una renta mínima mensual en CLP.
- Modalidad, ubicación y renta se incorporan al match explicable.
- Las ofertas sin modalidad, ubicación o renta publicada permanecen neutrales en esa señal.
- Las ofertas remotas no se penalizan por ubicación.
- Las preferencias se conservan al reemplazar o volver a analizar el currículum.
- Las oportunidades antiguas pueden recalcularse mediante “Reevaluar base”.
- 41 pruebas automatizadas aprobadas.

## 5.4.0 — Match explicable
- Cada oferta conserva un desglose estructurado de cómo se construyó su puntaje.
- El detalle muestra cargo/rol, competencias, afinidad de área, experiencia, seniority y requisitos adicionales.
- Las bonificaciones y penalizaciones se muestran con valores positivos o negativos.
- Se muestran roles y competencias concretas que coincidieron con la oferta.
- Las ofertas antiguas pueden generar su desglose usando “Reevaluar base”.
- Supabase incorpora `jobs.match_breakdown` como JSONB protegido por las políticas RLS existentes.
- 33 pruebas automatizadas aprobadas.

## 5.3.0 — LinkedIn + experiencia
- LinkedIn habilitado como fuente pública sin solicitar credenciales ni cookies.
- LinkedIn falla de forma aislada si activa authwall/rate limit.
- El perfil incorpora años de experiencia profesional cuando pueden determinarse con seguridad.
- Gemini estima experiencia laboral evitando sumar estudios o períodos superpuestos.
- El scoring detecta requisitos explícitos de años y penaliza brechas relevantes.
- La pantalla de perfil muestra la experiencia usada por el motor de matching.
- 30 pruebas automatizadas aprobadas.

## 5.2.0 — Perfil multiprofesional

- Generaliza el análisis de CV y matching para múltiples áreas profesionales.
- Gemini Structured Output amplía la cobertura de profesiones con fallback local.
- Elimina exclusiones globales que confundían QA de software con calidad industrial.
- Scoring guiado por el perfil individual: cargo + competencias + seniority.
- Portales generalistas pasan a ser las fuentes recomendadas; GetOnBoard queda identificado como tecnología.
- Agrega pruebas de enfermería, contabilidad y QA/QC industrial.

# Changelog

## 5.0.0

- Migra la interfaz a Next.js 16 + React 19.
- Mantiene el motor Python detrás de FastAPI.
- Agrega búsquedas en segundo plano con progreso persistente en Supabase.
- Guarda resultados por fuente para no perder avances si una corrida se interrumpe.
- Convierte GetOnBoard, Computrabajo, ChileTrabajos y Trabajando.com a consultas HTTP públicas.
- Reduce el costo de BNE y Laborum en modo rápido.
- Endurece el filtro para páginas SEO, QA/QC industrial y roles generalistas sin coincidencia de cargo.
- Agrega `Ver oferta / Postular` en el detalle de cada oportunidad.
- Agrega recuperación y cambio de contraseña.
- Corrige el arranque Docker y el health check de Render.
- Versiona el esquema Supabase con RLS en `supabase/migrations`.
- Mejora mensajes de error y recuperación de búsquedas activas.

### Cartas inteligentes
- Integración nativa con Gemini Developer API.
- Modelo predeterminado `gemini-3.5-flash-lite`.
- Sanitización de correo, teléfono y URLs del CV antes de enviarlo al proveedor.
- Estado de configuración visible en la interfaz.
- El modo local sigue funcionando sin API.
