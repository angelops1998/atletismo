# Recuperación de la migración McLean f2a7c94b1d30

La migración no admite `downgrade`: eliminar sus columnas descartaría respuestas McLean o la semántica registrada para una duración. No modificar esa protección ni marcar manualmente una revisión para sortearla. La validación de la migración completa en PostgreSQL continúa pendiente mientras no exista un destino aislado verificado.

Si fuera necesario recuperar el servicio, el responsable de la base debe evaluar y autorizar un procedimiento específico:

1. Detener escrituras y verificar explícitamente la identidad del destino y la revisión aplicada. Tomar una copia consistente y verificable, incluida la estructura, todos los registros y las revisiones Alembic; guardarla sin alterar el original.
2. Restaurar la copia en un PostgreSQL aislado y comprobar que se puede leer. Inventariar por separado las respuestas 1–10 y McLean, sesiones, cargas y tipos de duración, además de los demás datos y cambios posteriores a cualquier copia anterior.
3. Preferir una corrección hacia adelante compatible con el esquema actual. Volver a desplegar código anterior solo después de comprobar en la copia que puede leer todos los registros existentes: el código histórico no interpreta las respuestas McLean y sus campos 1–10 pueden ser nulos.
4. Si es imprescindible volver a un esquema anterior, diseñar y revisar una migración de recuperación específica que conserve íntegramente los datos y su significado en un destino de archivo verificable, sin convertir ni sobrescribir respuestas. La copia anterior por sí sola no recupera los datos escritos después de ella.
5. Ensayar el procedimiento completo en la copia aislada: recuentos, contenido, relaciones, restricciones, lectura por la aplicación, permisos y recuperación desde el respaldo. Documentar las diferencias y obtener autorización explícita antes de cualquier acción sobre la base real.

No se proporciona un comando de reversión universal: la recuperación segura depende de los datos presentes y del destino. Esta guía no sustituye la validación PostgreSQL pendiente ni autoriza cambios en producción.
