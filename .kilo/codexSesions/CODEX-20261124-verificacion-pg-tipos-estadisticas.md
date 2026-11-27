# Verificación PostgreSQL de estadísticas

- Base: `c0aeffc`, rama `preparacion/entorno-general`.
- Se añadió una prueba con PostgreSQL 16 y Alembic real hasta `a82d51f4c930` dentro de un esquema temporal y una transacción revertida; el acceso pasó el control independiente de aislamiento existente.
- El caso guarda los cuatro tipos nuevos y una sesión histórica, junto a una planificación histórica. Comprueba recuentos independientes, promedios de ambas escalas, cortes de gráficos y conservación de cargas por duración.
- Se agregó una comprobación de la página con planificación y sesiones realizadas coexistentes.
- Resultado: 30 pruebas pertinentes aprobadas, seis avisos de obsolescencia; tras las pruebas, cero esquemas temporales y cero registros en las cuatro tablas de prueba inspeccionadas.
- No se modificó código de aplicación ni se operó sobre producción. El esquema permanente del contenedor no se migró; la cadena completa se ejecutó únicamente en el esquema transaccional de prueba.
