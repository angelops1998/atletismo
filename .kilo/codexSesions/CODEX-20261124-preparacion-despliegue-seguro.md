# Preparación segura del despliegue McLean

- Base: `1de488a`, rama `preparacion/entorno-general`. No se accedió a producción ni se activó McLean.
- El build del Blueprint ya no ejecuta Alembic. Se documentaron controles del servicio efectivo, respaldo y recuperación, migración autorizada y condiciones previas al merge.
- Pruebas HTTP focalizadas: 30 aprobadas, un aviso de obsolescencia. Se verificó la desactivación de McLean con registros existentes, 503 para el atleta, acceso docente y recuperación al reactivar la opción en pruebas.
- Ensayo sintético limitado: PostgreSQL 16 sin red, datos temporales; `pg_dump` y `pg_restore` conservaron versión, respuestas de ambas escalas, cargas, índice y relación. El contenedor creado para el ensayo se eliminó.
- Pendiente: ensayar la copia real y recursos Supabase en destino aislado, verificar configuración efectiva de Render, autorizar respaldo/migración/despliegue y decidir la activación posteriormente. No se ensayó Supabase CLI ni una copia de producción.
