# Diagnóstico del cierre de sesión local

Fecha: 2026-11-15 (hora local de La Paz)

## Estado observado

- Repositorio local en `C:\Archivos.Diego\atletismoWeb\atletismo`, rama `Baruc+Kilo`, HEAD `d37fcaa` (`codex commit 10`).
- El árbol estaba limpio antes de crear este informe.
- En el código actual, `app/routers/auth.py` define `POST /auth/logout`. Los formularios de navegación en `_nav.html`, `_menu_movil.html` y `cuenta.html` usan POST e incluyen el campo CSRF.
- La aplicación atendía en `127.0.0.1:8002`, con procesos Python activos desde el 15/11/2026 a las 20:22 aproximadamente.
- Una solicitud HTTP GET de diagnóstico a `/auth/logout` respondió 302 y emitió encabezados de borrado de cookie; el código fuente actual no define esa ruta GET. Esto confirma una discrepancia entre la aplicación cargada en memoria y el código actual, compatible con un proceso Uvicorn antiguo o lanzado desde otro estado/copia.
- Un POST de diagnóstico sin token CSRF respondió 403, como corresponde a la protección CSRF. No se envió ningún POST con credenciales ni se alteraron cookies del navegador.
- La pestaña de Edge seguía autenticada en la aplicación. No se completó ninguna acción de cierre desde el navegador.

## Diagnóstico

Cerrar las ventanas del navegador no detiene ni recarga el proceso Uvicorn. La sesión de la aplicación está en una cookie, y el proceso del servidor conserva en memoria las rutas y plantillas que cargó al iniciar. Por eso reabrir `http://127.0.0.1:8002` no garantiza que se esté usando el código actual.

La pantalla 405 al abrir `/auth/logout` directamente es esperable cuando logout solo admite POST. El enlace correcto es el formulario “Cerrar sesión”; escribir esa ruta en la barra del navegador hace una solicitud GET y no equivale a enviar el formulario.

## Cambios y operaciones

- No se modificó código de aplicación.
- No se ejecutaron migraciones ni el inicializador de datos.
- No se modificó la base de datos, usuarios ni registros.
- No se crearon commits ni se hicieron pushes.
- Se creó únicamente este informe de sesión.

## Cómo cambiar de cuenta ahora

Para mantener abierta la sesión actual y probar otra cuenta en paralelo, abrir una ventana InPrivate de Edge (`Ctrl+Shift+N`), visitar `http://127.0.0.1:8002` e iniciar sesión con la otra cuenta. La ventana InPrivate mantiene cookies separadas.

Para cerrar la sesión en la ventana normal, detener el servidor Uvicorn desde la consola donde fue iniciado (`Ctrl+C`) y volver a arrancar el entorno demo desde la raíz del repositorio con:

```powershell
.\scripts\iniciar_demo.ps1
```

Esperar el mensaje de inicio de Uvicorn, recargar la página (`Ctrl+F5`) y usar “Cerrar sesión” dentro de la aplicación. El script de demo verifica la identidad local de PostgreSQL, aplica Alembic y ejecuta el seed idempotente; no usarlo si se desea evitar incluso las actualizaciones de datos demo que el seed administra.

## Validación pendiente

No se confirmó visualmente el resultado final del logout en el navegador. Tras reiniciar con la versión actual, el comportamiento esperado es: el formulario POST con token válido redirige a `/auth/login`; GET a `/auth/logout` no debe cerrar sesión.
