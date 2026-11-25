# Correcciones de auditoría de estadísticas

- Base: `2e3ed9b`, rama `preparacion/entorno-general`.
- Se cortan los gráficos cuando faltan fechas y se cuentan por separado las sesiones realizadas y las estructuras planificadas históricas.
- Se ampliaron las pruebas de vistas, cortes y agregados mixtos en PostgreSQL aislado, verificando también las cargas almacenadas.
- Suite completa: 657 pruebas aprobadas y cinco avisos de obsolescencia. La base desechable quedó sin registros de prueba ni esquemas temporales.
- El esquema permanente de la base de pruebas aún tiene la restricción anterior de tipos; el agregado PostgreSQL usa un tipo compatible y las cuatro modalidades se comprueban en SQLite. No se alteró el esquema permanente.
- McLean sigue desactivado por defecto; no se usó producción.
