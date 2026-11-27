# Secuencia de Render y credenciales administrativas

- Base: `077a9a9`, rama `preparacion/entorno-general`. Se conservó el trabajo preexistente.
- Se documentó la secuencia para detener sincronización, despliegue y otros disparadores, controlar el posible despliegue por cambio de configuración y retirar Alembic del build efectivo antes del merge autorizado.
- Se sustituyó el intercambio de destinos en `.env` por una sesión administrativa separada, con comprobación de identidad y advertencia de que el script no la verifica de forma atómica.
- Validación: cuatro pruebas focalizadas aprobadas, un aviso de obsolescencia; comprobaciones de coherencia documental y Blueprint aprobadas.
- No se accedió a producción, no se sincronizó Render ni se ejecutaron migraciones. La revisión efectiva del servicio y las autorizaciones, el respaldo real y su restauración siguen pendientes.
