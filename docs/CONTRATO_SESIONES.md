# Contratos de duración de sesiones

`save_daily_record` admite `contrato_sesiones` como argumento del servicio. Si se omite o se indica `historico`, las sesiones nuevas conservan `tipo_duracion=no_especificada`; el contrato antiguo no permite afirmar que sus minutos correspondan al trabajo principal. Si el llamador ha recogido explícitamente esos minutos, debe indicar `contrato_sesiones="trabajo_principal"`; las sesiones nuevas reciben ese tipo de duración y el servidor calcula la carga como minutos por RPE.

El contrato no reinterpreta sesiones ya guardadas. Las sesiones con duración no especificada conservan duración, RPE y carga; no se admite modificar duración o RPE sin una política de migración acordada. El contrato histórico tampoco modifica esos valores en sesiones de trabajo principal. Los identificadores existentes deben pertenecer al parte y las operaciones requieren los tokens vigentes.

El formulario histórico sigue usando el contrato histórico. El formulario McLean usa el contrato `tipo_diario`, que guarda una clasificación diaria independiente y conserva todas las sesiones existentes incluso al marcar descanso. Las vistas docentes agrupan las duraciones y cargas históricas por semántica. Las etiquetas ya almacenadas no se corrigen automáticamente.

La migración `a82d51f4c930` amplía el CHECK de tipos sin convertir filas. Su downgrade se bloquea mientras existan sesiones con tipos que el esquema anterior no admite; no elimina datos.

La migración `b395c7281e4a` añade una columna nullable para el tipo diario sin inferirlo desde sesiones o planes anteriores. Su downgrade está bloqueado para preservar las clasificaciones.

El formulario McLean está desactivado por defecto (`FORMULARIO_MCLEAN_HABILITADO=false`). Las vistas docentes distinguen las versiones de bienestar y las semánticas de duración; su activación sigue reservada a entornos de prueba aislados hasta una decisión expresa de puesta en producción. Con la opción desactivada, los partes McLean existentes no se editan con el formulario histórico.
