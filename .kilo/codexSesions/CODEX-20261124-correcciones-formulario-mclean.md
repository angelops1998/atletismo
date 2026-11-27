# Correcciones del formulario McLean

- Los conflictos mantienen el borrador y el token original. La confirmación explícita utiliza un token de revisión firmado, distinto al token de edición, vinculado al atleta, registro, fecha y estado actual; si el estado vuelve a cambiar, se devuelve otro 409.
- El servidor rechaza más de tres sesiones nuevas por guardado sin limitar la cantidad de sesiones existentes; en 422 conserva los tokens originales.
- Sin JavaScript, los campos condicionales permanecen visibles y pueden completarse. Se verificó en navegador móvil con JavaScript desactivado sobre SQLite en memoria, guardando entrenamiento, molestias y síntomas.
- Suite general: 635 aprobadas y 12 omitidas sin PostgreSQL, con una advertencia de dependencia. Las 12 pruebas PostgreSQL se ejecutaron después en un contenedor desechable verificado y pasaron; cinco advertencias de dependencias. Pruebas finales del formulario: 19 aprobadas.
- La instancia temporal se detuvo, así como el contenedor PostgreSQL; no se encontraron esquemas temporales ni filas de prueba en las tablas revisadas. El formulario permanece desactivado por defecto y las estadísticas no se modificaron.