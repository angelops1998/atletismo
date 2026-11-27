# Controles previos al despliegue

- Base: `0c94bf7`, rama `preparacion/entorno-general`. Se conservan los cambios locales preexistentes; no se accedió a producción.
- La guía exige revisión objetivo y esquema compatible antes de Apply o del primer arranque; distingue la revisión inicial observada de la primera revisión del repositorio y de `a82d51f4c930`.
- El Blueprint declara McLean desactivado y mantiene las migraciones fuera del build. Se documenta que sincronizarlo puede modificar una variable existente y exige comprobar el servicio efectivo.
- Se prepararon controles de solo lectura de Render/Supabase y una secuencia de respaldo y restauración aislada con intervenciones y autorizaciones explícitas.
- Validación: cuatro pruebas focalizadas aprobadas y comprobaciones locales del Blueprint y el orden documental; un aviso de obsolescencia de dependencia. No se ejecutaron migraciones, respaldos ni restauraciones reales.
- Pendiente: comprobación real de identidades y ajustes, respaldo real y restauración aislada, autorizaciones y despliegue o activación posteriores.
