# Fase de esquema McLean

- Migración aditiva f2a7c94b1d30 desde e8a4f670c11d: versión explícita, cinco campos McLean, restricciones mutuamente excluyentes y campos históricos preservados. La reversión se bloquea para evitar pérdida de información.
- Duraciones existentes y las creadas por el flujo actual quedan como no especificadas; se admite explícitamente trabajo principal. No se recalculan cargas históricas.
- Las huellas de concurrencia incluyen la nueva versión, respuestas y semántica de duración. No se modificaron interfaz ni estadísticas.
- Suite SQLite aislada: 524 aprobadas, 5 omitidas y una advertencia de dependencia. La primera ejecución focalizada detectó un error de importación en la prueba de migración, corregido antes de pasar la suite completa.
- PostgreSQL no se validó: motor Docker inaccesible y sin instancia local aislada comprobada. No se ejecutaron migraciones sobre bases existentes.
- Pendiente: antes de habilitar captura McLean o trabajo principal, adaptar la interfaz, el servicio y las estadísticas por versión y validar la migración en PostgreSQL aislado.