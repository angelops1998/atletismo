# Preparación de despliegue y recuperación McLean

Este procedimiento requiere responsables y autorización expresa antes de acceder a producción. No ejecutar desde una copia de trabajo sin verificar el destino. El blueprint de esta rama no ejecuta migraciones: esto no cambia automáticamente un servicio de Render ya configurado.

## Antes de incorporar a main

1. Identificar el servicio, proyecto Supabase, base y revisión Alembic actuales mediante controles de solo lectura. Confirmar la rama efectiva de despliegue y desactivar o coordinar el despliegue automático antes del merge. Confirmar en Render el **build command efectivo** sin Alembic y que no haya comandos de predeploy, inicio ni otros procesos que migren automáticamente; revisar también sincronización del Blueprint y ajustes del dashboard. El servicio ya desplegado puede seguir usando el comando anterior hasta actualizar su configuración. No hacer merge ni desplegar hasta verificarlo.
2. Confirmar `DATABASE_URL` del proyecto correcto, conexión compatible y cifrada, `SECRET_KEY` persistente, `HTTPS_ONLY=true`, variables del club y `FORMULARIO_MCLEAN_HABILITADO=false` en todos los procesos. No imprimir ni almacenar secretos en el repositorio. El Blueprint declara `false`, pero una sincronización puede modificar un valor existente; evaluar su impacto antes de aplicarla y comprobar el valor efectivo después. La declaración no demuestra el estado del servicio ya desplegado.
3. Registrar primero la revisión **inicial observada** y compararla con la **objetivo `a82d51f4c930`**. `d61e48816ec5` es la primera revisión de la cadena del repositorio, no necesariamente la revisión de la base real. Comprobar permisos, ventana operativa y compatibilidad de la aplicación anterior con el esquema ampliado. El build ahora solo instala dependencias: actualizar el esquema requiere una operación separada, verificada y expresamente autorizada. Si el esquema aún no está actualizado, no desplegar el código que depende de él.
4. Preparar un respaldo consistente y demostrar su restauración aislada como se indica abajo. Definir responsables, tiempo máximo de recuperación, control de escrituras, monitorización y criterio de aceptación. Solo después solicitar la autorización de migración para el destino identificado; supervisar la revisión aplicada y las comprobaciones antes de autorizar el despliegue. La activación del formulario requiere una decisión posterior separada.

## Verificación de solo lectura

**Intervención del responsable:** identificar y abrir las cuentas y los recursos correctos; no enviar contraseñas, cadenas de conexión, tokens ni capturas con secretos. No guardar, aplicar, sincronizar ni lanzar despliegues durante esta revisión.

1. En Render, consultar el servicio y entorno, repositorio, rama, commit desplegado, despliegue automático, sincronización del Blueprint y comandos efectivos de build, predeploy y arranque. Comprobar que no haya otra tarea configurada que migre. Revisar `FORMULARIO_MCLEAN_HABILITADO` y `HTTPS_ONLY` en el servicio y grupos de entorno, y comprobar la identidad del destino de `DATABASE_URL` sin revelar su valor. Registrar solo coincidencias, discrepancias y configuración no sensible. Confirmar el valor utilizado por la versión realmente desplegada; una edición pendiente o un Blueprint en Git no demuestra que esté activo.
2. En Supabase, comprobar organización, proyecto y región con el responsable y confirmar que coinciden con el destino configurado. Usar un usuario con permisos de lectura y conexión cifrada previamente verificados, sin poner la URL en el historial o argumentos visibles. En una sesión de solo lectura consultar:

   ```sql
   BEGIN READ ONLY;
   SELECT current_database(), current_user, current_setting('server_version');
   SELECT to_regclass('public.alembic_version');
   -- Solo si la consulta anterior devuelve public.alembic_version:
   SELECT version_num FROM public.alembic_version ORDER BY version_num;
   ROLLBACK;
   ```

   Registrar la revisión inicial observada o la ausencia de tabla. Cero o múltiples revisiones, permisos insuficientes o identidad dudosa son motivo para detenerse y resolverlo; no crear ni modificar la tabla. Comparar con `a82d51f4c930` y consultar restricciones y tablas pertinentes antes de afirmar compatibilidad. El nombre de base por sí solo no identifica inequívocamente un proyecto Supabase: corroborar el proyecto también desde el panel o metadatos independientes.
3. La revisión se ha preparado, no se ha ejecutado sobre el servicio real. Cualquier discrepancia o cambio necesario requiere una decisión separada; no aplicar automáticamente ajustes ni migraciones.

## Respaldo y restauración a ensayar

**Intervención y autorización del usuario:** confirmar el origen y el destino aislado, aprobar el acceso al respaldo y coordinar la pausa de escrituras o la instantánea consistente. Autorizar la migración, el merge, el despliegue y la activación por separado; este procedimiento no los autoriza.

1. Inventariar base, revisión, extensiones, roles, permisos, RLS, esquema, datos y secuencias; identificar también Storage, Auth, funciones, secretos y configuración externa realmente utilizados. Verificar disponibilidad y alcance de backup/PITR según el plan. Las copias de base no incluyen objetos de Storage, y contraseñas de roles personalizados pueden requerir recuperación separada. Mantener credenciales fuera de comandos visibles, logs y repositorios; cifrar las copias y limitar su acceso.
2. Para una copia lógica de Supabase, seguir su [guía oficial](https://supabase.com/docs/guides/self-hosting/restore-from-platform): exportar por separado roles, esquema y datos mediante Supabase CLI y conservar también los recursos externos y configuración que el inventario requiera. La CLI filtra componentes internos específicos de Supabase; un `pg_dump` genérico no sustituye automáticamente ese procedimiento. Como las tres exportaciones se realizan por separado, coordinar una pausa de escrituras durante todo el proceso o disponer de un mecanismo de instantánea consistente verificado. Registrar fecha, destino, versión de herramientas, alcance, integridad y cifrado sin datos sensibles.
3. Restaurar primero en un entorno **aislado y desechable**, sin acceso a servicios externos ni producción y con versiones y extensiones compatibles. Verificar de forma independiente identidad, red, permisos y destino antes de escribir. Seguir el orden y las indicaciones oficiales para roles, esquema y datos; no ejecutar una restauración sobre el origen. Tratar funciones, triggers, webhooks y tareas programadas como potenciales efectos externos y mantenerlos aislados durante el ensayo.
4. Comparar inventarios y recuentos por versión, las cinco respuestas, molestias, síntomas, comentarios, relaciones, índices y restricciones; verificar `alembic_version`, sesiones, tipo de duración y cargas almacenadas, secuencias y lectura con una aplicación de prueba. Verificar por separado restauración de archivos y recursos fuera de la base. Documentar éxito, diferencias y tiempo, y conservar la copia original sin cambios.
5. Una restauración validada de datos sintéticos comprueba solo el mecanismo ensayado. La copia real y sus componentes Supabase deben verificarse por separado antes de cualquier operación real; no asumir que una copia anterior recupera escrituras posteriores. En una incidencia, parar escrituras y seguir [RECUPERACION_MCLEAN.md](RECUPERACION_MCLEAN.md); preferir una corrección hacia adelante y nunca eludir el bloqueo de downgrade.

En la preparación se ensayó una copia lógica genérica `pg_dump`/`pg_restore` de un esquema sintético mínimo en PostgreSQL 16 sin red y con almacenamiento temporal. Se verificaron revisión, dos versiones de respuesta, cargas 999 y 150, una relación y un índice. **No** se ensayaron la CLI de Supabase, roles, todos los campos y tablas reales ni una restauración de una copia del proyecto: esos puntos siguen pendientes y el ejercicio no prueba que un respaldo real sea recuperable.

## Si se desactiva McLean después de guardar respuestas

Con el código actual y la opción en `false`, un atleta cuyo parte de hoy ya sea McLean recibe 503 en GET y POST de `/parte`: no puede consultarlo ni editarlo allí mientras esté desactivado. Los registros conservados siguen disponibles en las vistas docentes compatibles. En fechas sin parte, el formulario vuelve al contrato histórico 1–10, por lo que se pueden generar nuevas filas históricas; no se convierten los registros McLean. Estas consecuencias deben comunicarse antes de cambiar la opción.

Para recuperar la edición sin perder datos, diagnosticar y corregir el problema, mantener el esquema y desplegar código compatible; solo con autorización volver a habilitar McLean, verificando el valor en todos los procesos y el acceso a los partes existentes. Si no es seguro habilitarlo, mantener el bloqueo y preservar los registros para tratamiento posterior: no convertir respuestas, no volver a código que no entienda McLean y no usar downgrade como atajo. Ensayar cualquier recuperación sobre una copia aislada; antes de un cambio real inventariar y preservar también los datos posteriores al respaldo.

Referencias: [Backups de Supabase](https://supabase.com/docs/guides/platform/backups), [Blueprints de Render](https://render.com/docs/blueprint-spec) y [despliegues de Render](https://render.com/docs/deploys).
