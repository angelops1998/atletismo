# Contratos de duración de sesiones

`save_daily_record` admite `contrato_sesiones` como argumento del servicio. Si se omite o se indica `historico`, las sesiones nuevas conservan `tipo_duracion=no_especificada`; el contrato antiguo no permite afirmar que sus minutos correspondan al trabajo principal. Si el llamador ha recogido explícitamente esos minutos, debe indicar `contrato_sesiones="trabajo_principal"`; las sesiones nuevas reciben ese tipo de duración y el servidor calcula la carga como minutos por RPE.

El contrato no reinterpreta sesiones ya guardadas. Las sesiones con duración no especificada conservan duración, RPE y carga; no se admite modificar duración o RPE sin una política de migración acordada. El contrato histórico tampoco modifica esos valores en sesiones de trabajo principal. Los identificadores existentes deben pertenecer al parte y las operaciones requieren los tokens vigentes.

El formulario actual sigue usando el contrato histórico. La posterior interfaz deberá seleccionar explícitamente el contrato nuevo, validar sus campos y actualizar las vistas que agrupan duraciones. Las etiquetas ya almacenadas antes de este cambio no se corrigen automáticamente: debe verificarse su procedencia antes de cualquier reclasificación.

La migración `a82d51f4c930` amplía el CHECK de tipos sin convertir filas. Su downgrade se bloquea mientras existan sesiones con tipos que el esquema anterior no admite; no elimina datos.
