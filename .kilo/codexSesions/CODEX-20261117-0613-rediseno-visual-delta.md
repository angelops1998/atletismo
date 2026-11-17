# Rediseño visual DELTA Club de Atletismo

**Fecha:** 2026-11-17 06:13 (America/La_Paz)  
**Repositorio:** `C:\Archivos.Diego\atletismoWeb\atletismo`  
**Rama:** `Baruc+Kilo`  
**HEAD inicial y final:** `c2dfe59342332120d3d7a4c98cb9e809c1402595` — `codex commit 11, visuales de profesores`

## Diseño aplicado

Se sustituyó el tema naranja por un sistema oscuro centralizado inspirado en la camiseta: negro deportivo y grafito para fondos y superficies, rojo/carmesí para acciones y estados activos, vino para degradados y blanco cálido para texto. Se conservó la tipografía local Hanken Grotesk y Barlow Condensed.

La camiseta aportó el criterio de composición: centro visual limpio y red geométrica angular hacia extremos y zonas inferiores. Se creó un patrón SVG liviano de líneas y polígonos rojos translúcidos. El logo blanco PNG transparente del club se usa sin reconstruir ni deformar su composición.

## Archivos modificados y creados

- `app/static/css/main.css`: sistema de variables de marca y tema oscuro compartido. Adaptó superficies, textos, navegación, tarjetas, tablas, formularios, focos, estados semánticos, gráficos, botones y vistas públicas. Incorporó detalles geométricos en barras y portada/login, hover de tablas, estados de teclado y reducción de movimiento. Las escalas de bienestar y las franjas RPE conservan sus diferencias semánticas.
- `app/static/favicon.svg`: reemplazó el favicon naranja anterior por un símbolo geométrico rojo sobre negro, dibujado como recurso independiente.
- `app/static/img/delta-geometria.svg` (nuevo): patrón geométrico del tema; fondo decorativo y no interactivo.
- `app/static/img/delta-logo-blanco.png` (nuevo): copia del recurso transparente `LogoPNG (Sin Fondo).png`, sin transformación.
- `app/templates/base.html`: actualizó el color de tema del navegador a negro deportivo.
- `app/templates/_nav.html`: integró el logotipo oficial en la navegación lateral de escritorio.
- `app/templates/auth/login.html`: integró el logotipo en acceso y cambió el texto visible para referirse al parte diario.
- `app/templates/publico/landing.html`: integró el logo en la navegación y el pie; aplicó texto diario coherente con el flujo actual.
- `app/templates/_campos.html`: corrigió un comentario de mantenimiento que describía erróneamente los controles como semanales.

Las plantillas de atleta, profesor, gestión, cuenta y errores que consumen `base.html` o los componentes comunes reciben el sistema visual compartido sin cambios a sus rutas, formularios ni lógica de negocio. El patrón de la camiseta se recreó como un SVG pequeño; no se usó la foto de la prenda como fondo.

## Comportamiento que permanece intacto

No se cambiaron modelos, tablas, migraciones, rutas, permisos, autenticación, validaciones, consultas, persistencia ni operaciones de datos. Los formularios, reportes diarios, sesiones, controles de acceso y opciones de navegación conservan su comportamiento. Solo cambiaron estilos compartidos y textos de marca/ayuda en login y portada.

## Validación ejecutada

| Estado | Comando / procedimiento | Resultado |
|---|---|---|
| PASS | `\.venv\Scripts\python.exe -m pytest -q` | 514 aprobadas, 5 omitidas, 1 advertencia Starlette/httpx; 87.93 s. La salida compacta no identificó los motivos de las omisiones. |
| PASS | `\.venv\Scripts\python.exe -m pytest tests\test_landing.py tests\test_seguridad.py -q` | 53 aprobadas, 1 advertencia Starlette/httpx; 18.41 s. |
| PASS | `\.venv\Scripts\python.exe -m compileall -q app` | Compilación Python correcta. |
| PASS | `git diff --check` | Sin errores de whitespace. Git avisó que normalizará LF a CRLF para `app/static/favicon.svg`; el comando terminó correctamente. |
| PASS | Búsqueda de `#C2410C`, `#EA580C`, `#FDEBE0` y `rgba(234,88,12)` bajo `app` | Sin coincidencias de la identidad naranja anterior. |
| PASS | Prueba aislada de `Starlette StaticFiles` para `delta-logo-blanco.png`, `delta-geometria.svg`, `main.css` y `favicon.svg` | Los cuatro recursos respondieron 200 con tipo MIME esperado. Esta fue una comprobación del servidor estático aislado, no una navegación completa a la aplicación. |
| NOT TESTED | Inspección visual manual en navegador y tamaños móvil/escritorio | El puerto local 8002 no estaba escuchando. La importación directa de la aplicación indicó que falta configuración local requerida (`database_url`, `secret_key`). No modifiqué configuración ni inicié un servidor que pudiera conectarse a una base no verificada. |

La prueba de importación de la aplicación terminó con el mensaje de variables faltantes; no se inició FastAPI ni se realizaron conexiones o cambios en bases de datos. La hoja CSS se entregó con HTTP 200 en el montaje estático aislado, pero el aspecto completo de las páginas debe revisarse cuando se pueda iniciar el entorno local seguro.

## Pendientes

- Revisar visualmente portada, login, panel de atleta, parte diario, panel docente, estadísticas y ficha de atleta en escritorio y teléfono con la aplicación local correctamente configurada.
- Comprobar contraste percibido en los estados de bienestar, tablas extensas y mensajes de validación durante esa revisión visual.
- Considerar en una iteración posterior una marca compacta dedicada para iconos de navegador si el símbolo actual se desea aún más cercano al logotipo original.

## Git y datos

- Estado inicial: rama `Baruc+Kilo`, HEAD `c2dfe59342332120d3d7a4c98cb9e809c1402595`, árbol limpio.
- Estado final: siete archivos rastreados modificados y dos recursos gráficos nuevos sin seguimiento, además de este informe.
- Sin commits, pushes, merges ni despliegues.
- Sin conexiones a PostgreSQL/Supabase ni cambios en bases de datos.
