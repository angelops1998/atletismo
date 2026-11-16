# Corrección del segundo arranque de la demo (puerto 8002)

**Fecha local:** 15 de noviembre de 2026  
**Proyecto:** `C:\Archivos.Diego\atletismoWeb\atletismo`  
**Tipo:** registro de petición y acciones Kilo/Codex

---

## Reporte recibido

El usuario volvió a ejecutar `scripts/iniciar_demo.ps1` mientras Uvicorn ya ocupaba `127.0.0.1:8002`. La migración y el seed terminaron bien; Uvicorn falló al enlazar con Windows `10048` (dirección/puerto ya en uso).

## Diagnóstico

Se identificó el listener PID 14896 como `python.exe`, ejecutando `-m uvicorn app.main:app --host 127.0.0.1 --port 8002`. `http://127.0.0.1:8002/auth/login` respondió HTTP 200. Era una instancia activa de la aplicación, no un puerto huérfano.

## Cambio

- `scripts/iniciar_demo.ps1`: antes de iniciar Uvicorn, consulta `/auth/login`. Si la página esperada responde HTTP 200, informa que reutiliza la aplicación y termina correctamente sin crear un segundo servidor.
- Si el puerto tiene listener pero la ruta no responde con la página de login esperada, falla con un mensaje que identifica el PID y solicita liberar el puerto manualmente; no mata procesos.
- Se guardó el script con BOM UTF-8 para que Windows PowerShell 5.1 lea correctamente los literales con acentos. Se mantiene configuración de salida Python UTF-8.

## Validación ejecutada

- **PASS:** Parser de PowerShell sobre `scripts/iniciar_demo.ps1`, sin errores.
- **PASS:** Ejecución completa del script. Verificó Docker/PostgreSQL, identidad `atletismo_demo`, migración head y seed; detectó la aplicación ya activa y finalizó con código 0 sin intentar enlazar Uvicorn otra vez.
- **PASS:** `/auth/login` retornó HTTP 200.
- **PASS:** `git diff --check`.

La ejecución volvió a correr el seed idempotente sobre la base local dedicada `atletismo_demo`; la preparación del seed pertenece a los efectos ya documentados del script. No se afectaron bases ajenas.

## Git

Rama `Baruc+Kilo`. Sin commits ni pushes. Permanecen cambios locales de esta serie de trabajo: modelo de sesión, script demo y los informes sin rastrear en `.kilo/codexSesions`.
