# Validación de migración McLean

- Se ampliaron pruebas para todas las respuestas históricas y McLean, tokens de edición y descarte y tipo de duración. Una reconstrucción SQLite en memoria de todos los modelos anteriores verifica conservación de datos representativos, índices, restricciones y referencias; no sustituye PostgreSQL.
- Se preparó una prueba PostgreSQL de la cadena de migraciones real, datos históricos y flujo existente. Solo actúa tras la validación independiente del destino Docker/PostgreSQL y opera en un esquema único dentro de una transacción revertida.
- Docker no tiene motor disponible y no se identificó servicio PostgreSQL local seguro. La prueba PostgreSQL quedó omitida; no se conectó ni escribió en otra base para suplirla.
- Suite: 561 aprobadas, 6 omitidas, una advertencia de dependencia. La comprobación adicional del esquema reconstruido pasó por separado. No se detectaron defectos confirmados en la migración.
- Se agregó una guía de recuperación; downgrade sigue bloqueado. Pendiente verificar la cadena real y el flujo en PostgreSQL aislado antes de activar McLean.