# Entorno de demostración local — Atletismo Web

Guía para levantar una demostración aislada y repetible con un solo comando de PowerShell, sin tocar datos de producción ni Supabase.

---

## Requisitos

- **Python 3.9+** (en este repositorio se usa el entorno virtual `.venv`, ya creado).
- **PostgreSQL** (la app usa SQLAlchemy + Alembic sobre PostgreSQL). Opciones en orden de preferencia:
  1. Una instalación local de PostgreSQL.
  2. Docker con el motor en ejecución (el script levanta un contenedor PostgreSQL aislado en `localhost`).
- **Docker Desktop** (solo si se usa la opción 2).

> **Importante:** XAMPP trae MariaDB/MySQL. Esta aplicación **no** usa MySQL ni MariaDB: su motor es PostgreSQL. No intentes apuntar la app a XAMPP.

---

## Un comando de arranque

Desde la raíz del repositorio:

```powershell
.\scripts\iniciar_demo.ps1
```

Qué hace el script, en orden:

1. Verifica que esté en la raíz del repositorio.
2. Comprueba la instalación de Python.
3. Localiza (o crea) el entorno virtual `.venv`, siguiendo la convención del repo.
4. Verifica e instala las dependencias del proyecto solo si faltan (`pip install -r requirements.txt`).
5. Detecta PostgreSQL usable: instalación local o motor de Docker.
6. Inicializa o reutiliza la base de datos dedicada `atletismo_demo`.
7. Configura la conexión **sin tocar `.env`** (variables de entorno solo del proceso actual).
8. Genera una `SECRET_KEY` de desarrollo solo en memoria del proceso.
9. Ejecuta `alembic upgrade head` (migraciones hasta el encabezado).
10. Ejecuta el inicializador idempotente de datos de demostración (`scripts/seed_demo.py`).
11. Levanta la aplicación FastAPI en `http://127.0.0.1:8002`.
12. Imprime las credenciales de demostración y las URL útiles.

> Presiona `Ctrl+C` para detener la aplicación.

---

## Docker (base de datos aislada)

Si no hay PostgreSQL local, el script usa Docker:

- Nombre de contenedor estable: `atletismo-demo-db`.
- Volumen dedicado: `atletismo-demo-pgdata`.
- PostgreSQL vinculado solo a `localhost` (`127.0.0.1:5433`), no expuesto a interfaces externas.
- Reutiliza un contenedor/demo existente si ya está creado (detenido o en ejecución). Nunca elimina contenedores o volúmenes ajenos.
- Nunca destruye automáticamente los datos de la demostración.

Si el motor de Docker no está en ejecución, el script avisa con el requisito faltante y una recomendación de configuración (ver "Limitaciones").

---

## Cuentas de demostración

Todas son **local-only**, creadas con el mecanismo real de hash de contraseñas de la aplicación (bcrypt, `app.auth.hash_password`). No se fuerza el cambio de contraseña al entrar (`debe_cambiar_password = false`); se usan las contraseñas reales de demo directamente.

| Rol | Usuario | Contraseña |
|-----|---------|------------|
| Profesor | `demo_profesor` | `DemoProfe2026!` |
| Atleta | `demo_atleta1` | `DemoAtleta2026!` |
| Atleta | `demo_atleta2` | `DemoAtleta2026!` |
| Atleta | `demo_atleta3` | `DemoAtleta2026!` |

Titularidad demo: las cuentas usan el email de dominio dedicado `@atletismo.demo.local` (marcador explícito de titularidad, campo soportado y único), además de los nombres de usuario estables. Nunca se asume titularidad solo por el nombre de usuario.

Las credenciales se imprimen al arrancar. La contraseña de la base de datos y la `SECRET_KEY` nunca se imprimen ni se persisten.

---

## URLs de la aplicación

Con la app en ejecución:

- `http://127.0.0.1:8002/` — raíz (redirige al panel o al login según la sesión).
- `http://127.0.0.1:8002/auth/login` — inicio de sesión.
- `http://127.0.0.1:8002/panel` — panel del profesor (alertas, padrón, finanzas).
- `http://127.0.0.1:8002/inicio` — pantalla del atleta.
- `http://127.0.0.1:8002/parte` — parte diario del atleta (solo atletas).
- `http://127.0.0.1:8002/atletas` — padrón de atletas (solo profesor).
- `http://127.0.0.1:8002/club` — página pública del club.
- `http://127.0.0.1:8002/cuenta` — cambio de contraseña (requiere sesión).

Rutas clave para la demostración:

- **Profesor:** `/panel`, `/atletas`, `/atletas/<id>`, `/estadisticas`, `/pagos`, `/asistencia`.
- **Atleta:** `/inicio`, `/parte`, `/mis-datos`, `/cuenta`.
- **Público:** `/`, `/club`.

---

## Cómo detener y reiniciar

- **Detener:** `Ctrl+C` en la terminal donde corre `.\scripts\iniciar_demo.ps1`.
- **Reiniciar:** ejecuta de nuevo `.\scripts\iniciar_demo.ps1`. Es idempotente: no duplica cuentas, atletas, pagos, asistencias, marcas, partes ni registros diarios. Vuelve a dejar los datos de demostración en el estado conocido.

---

## Cómo restablecer los datos de demostración

Si necesitas dejar los datos de demostración en cero y volver a cargarlos:

```powershell
.venv\Scripts\python.exe scripts/seed_demo.py --borrar-demo --confirmar-borrar-demo
```

- Requiere el argumento explícito `--confirmar-borrar-demo`.
- Valida que la base de destino sea `atletismo_demo` en `localhost` antes de borrar.
- Borra **solo** registros con titularidad demostración (dominio de email `@atletismo.demo.local`). Nunca toca registros ajenos ni elimina la base de datos.
- No se ejecuta automáticamente durante el arranque.

Si no se puede garantizar un restablecimiento seguro, no se implementa; en ese caso, volver a ejecutar `.\scripts\iniciar_demo.ps1` restaura los datos demo al estado conocido (idempotente).

---

## Aislamiento de la base de datos

- Base de datos dedicada: `atletismo_demo`.
- URL de conexión dedicada, inyectada solo como variable de entorno del proceso (`DATABASE_URL`), nunca escrita en `.env` ni en `.env.example`.
- La app lee `DATABASE_URL` del entorno (sobrescribe cualquier valor de `.env` si existiera), así que el `.env` del usuario queda intacto.
- Los registros de demostración se identifican por el dominio de email dedicado `@atletismo.demo.local` más los nombres de usuario estables. El inicializador solo crea/actualiza/borra esos registros; los registros ajenos se preservan.
- Nunca se conecta a Supabase ni a producción. Nunca se reutiliza una base de datos no identificada.

---

## Datos de la demostración

Cubre las pantallas del profesor y del atleta:

- Padrón de atletas y ficha del atleta (profesor).
- Partes diarios de hoy:
  1. `demo_atleta1`: parte completo, entrenó, **múltiples sesiones** y una **molestia** (rodillas, dolor 6/10).
  2. `demo_atleta2`: parte sin entrenamiento (`entreno_hoy = false`).
  3. `demo_atleta3`: **sin parte hoy** (falta de reporte); reportó **síntomas** (fiebre y tos) ayer.
- Asistencia, marcas, pagos y estado de cuenta (demo_atleta2 debe el mes en curso, para mostrar deuda).
- Múltiples semanas de partes semanales para tendencias y alertas del grupo.

---

## Errores comunes y resolución

| Error | Causa probable | Resolución |
|-------|----------------|------------|
| No se encontró Python | Python no está en el PATH | Instala Python 3.9+ y reinicia la terminal |
| No se puede crear el entorno virtual | Falta permiso o `venv` | Ejecuta desde una terminal con permisos sobre la carpeta del repo |
| No se encontró PostgreSQL ni Docker | Falta el motor de base de datos | Instala PostgreSQL localmente o inicia Docker Desktop y vuelve a ejecutar |
| Docker: el motor no responde | Docker Desktop aún no terminó de iniciarse | Espera a que el ícono de Docker Desktop se estabilice y ejecuta de nuevo |
| `alembic upgrade head` falla | `DATABASE_URL` no apunta a `atletismo_demo` en localhost | El script valida esto; si falla, revisa que no haya un `.env` con otra base y ejecuta de nuevo |
| No se puede entrar con las cuentas demo | La base no tiene los datos demo | Ejecuta `.\scripts\iniciar_demo.ps1` de nuevo (idempotente) |

---

## Limitaciones

- En esta sesión no estaba disponible ni una instalación local de PostgreSQL ni el motor de Docker en ejecución (Docker Desktop se lanzó pero su API de daemon no respondió, probablemente en configuración de primera ejecución de WSL2). Por tanto, las verificaciones contra PostgreSQL real (conexión, identidad de la base, `alembic upgrade head` sobre `atletismo_demo`, creación de cuentas y datos demo) **no se pudieron ejecutar** en esta sesión y quedan pendientes hasta que PostgreSQL o Docker estén disponibles. El script está preparado para usarlos en cuanto estén presentes.
- La app escucha en `127.0.0.1:8002` (solo loopback) para no exponerla en la red local.
- Las cuentas de demostración no fuerzan cambio de contraseña (`debe_cambiar_password = false`) porque ya traen contraseñas reales de demo; esto es una simplificación del entorno demo y no se debe replicar en producción.
- No se implementó un restablecimiento destructivo automático; el restablecimiento es explícito (`--borrar-demo --confirmar-borrar-demo`) y afecta solo registros demo.

---

## Verificación de pruebas automatizadas

La suite de pruebas del repositorio corre sobre SQLite en memoria y no toca PostgreSQL:

```powershell
.venv\Scripts\python.exe -m pytest
```

Véase la sección de resultados del informe de implementación.
