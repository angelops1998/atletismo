# McLean como alta única

- Base de trabajo: main local sincronizada con f6ca451. /parte usa McLean para nuevas altas y conserva el cuestionario de los partes históricos.
- PostgreSQL comprueba la revisión Alembic b395c7281e4a antes de servir la aplicación. Las migraciones quedan fuera del build.
- Validación local: formulario y flujos HTTP, migración y panel en PostgreSQL 16 desechable, y arranque rechazado en la revisión anterior y aceptado en la objetivo.
- Pendiente del responsable: confirmar destino, respaldo restaurable, revisión y control del despliegue automático antes de publicar. Sin acceso a producción.
