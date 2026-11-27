# Clasificación diaria de entrenamiento

- El formulario McLean registra un único tipo diario sin crear sesiones ni duración, RPE o carga. Las sesiones y planes anteriores se preservan al editar, incluso si se marca descanso.
- Se añadió la migración aditiva `b395c7281e4a` y el tipo se incluye en la huella de concurrencia. El panel y las estadísticas separan la clasificación diaria de las sesiones históricas.
- Suite local: 652 pruebas aprobadas, 16 PostgreSQL omitidas y un aviso de dependencia. Ensayo focalizado de migración en PostgreSQL aislado: cinco pruebas aprobadas.
- En navegador se guardó un parte diario con tipo Fuerza y se comprobó su visualización docente. No se accedió a producción.
