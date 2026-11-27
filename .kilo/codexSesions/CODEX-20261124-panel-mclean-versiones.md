# Panel del profesor: versiones de bienestar y duración

- Base: `97d20e4`, rama `preparacion/entorno-general`.
- Se separaron los indicadores y gráficos históricos 1–10 de McLean 1–5; McLean muestra respuestas, suma y promedio sin guardar valores redundantes.
- Las sesiones se agrupan por significado de duración y conservan las cargas almacenadas. El bienestar semanal independiente no se modificó.
- Se añadieron pruebas de períodos mixtos, acceso, conservación y agregaciones en PostgreSQL aislado.
- Validación: 655 pruebas aprobadas con PostgreSQL desechable verificado; cinco avisos de obsolescencia de dependencias. Tras las pruebas, no quedaron registros de prueba ni esquemas temporales en esa base.
- McLean permanece desactivado por defecto; no se operó sobre producción.
