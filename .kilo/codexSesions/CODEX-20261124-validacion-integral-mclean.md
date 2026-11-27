# Validación previa de McLean

- Base: `32a3668`, rama `preparacion/entorno-general`. McLean permanece desactivado por defecto; no se accedió a producción.
- Se incorporó una prueba HTTP integral de atleta a profesor con ambas escalas, sesiones múltiples, errores 422/409 y conservación de cargas.
- Suite completa: 659 aprobadas y seis avisos de obsolescencia; la nueva prueba integral se ejecutó por separado y aprobó. PostgreSQL 16 pasó los controles independientes existentes; Alembic se ensayó en esquemas transaccionales revertidos.
- Limpieza comprobada: cero esquemas temporales y cero registros en las cuatro tablas de prueba inspeccionadas. No se ha probado una restauración de copia real ni el entorno de producción.
- Antes del despliegue: confirmar destino y revisión, copia consistente y restauración ensayada, compatibilidad operativa y aprobación. Render ejecuta Alembic en el build. `f2a7c94b1d30` bloquea downgrade; aplicar la guía de recuperación y conservar escrituras posteriores. Activación del formulario requiere decisión expresa posterior.
