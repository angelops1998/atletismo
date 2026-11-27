# Despliegue de Atletismo en Render + Supabase

La app corre en **Render** (plan free) y la base de datos vive en **Supabase**
(Postgres administrado). No hay servidor que mantener: ni systemd, ni nginx, ni
certbot, ni cron de backups.

Antes esto estaba en un VPS con systemd y nginx. Si todavía está corriendo ahí,
el paso 8 lo da de baja — **hacelo último**, recién cuando Render responda.

---

## 0. Lo que tenés que tener a mano

- La cuenta de GitHub con el repo `angelops1998/atletismo`.
- Una cuenta en [supabase.com](https://supabase.com) y otra en
  [render.com](https://render.com) (las dos entran con GitHub).
- El repo clonado en tu máquina con el `.venv` armado: hace falta para crear el
  profesor (paso 6), porque el plan free de Render no tiene consola.

---

## 1. La base en Supabase

1. **New project**. Nombre `atletismo`.
2. **Database password**: generala con el botón y **guardala en tu gestor de
   contraseñas ahora mismo**. Supabase no la vuelve a mostrar, y recuperarla
   después es resetearla y reconfigurar Render.
3. **Region**: `East US (North Virginia)`. Tiene que ser la misma región que el
   servicio de Render (paso 3): cada pantalla hace varias consultas y si la app
   y la base están en continentes distintos el ida y vuelta se nota en el
   celular.
4. Esperá a que termine de crearse (un par de minutos).

### La cadena de conexión: tiene que ser la del *Session pooler*

En el proyecto: **Connect** (arriba) → pestaña **Connection string** → **URI**.
Ahí hay tres opciones y la que sirve es una sola:

| Opción | ¿Sirve? |
|---|---|
| **Direct connection** (`db.xxxx.supabase.co:5432`) | **No.** Es solo IPv6 y Render no tiene salida IPv6: el deploy arranca y muere con "Network is unreachable". |
| **Transaction pooler** (`:6543`) | No. No mantiene el estado de la sesión, y la app fija la zona horaria por sesión. |
| **Session pooler** (`aws-1-us-east-1.pooler.supabase.com:5432`) | **Sí.** Es IPv4 y se comporta como una conexión normal. |

Copiá la del **Session pooler**, reemplazá `[YOUR-PASSWORD]` por la del paso 2 y
agregale `?sslmode=require` al final. Te queda así:

```
postgresql://postgres.abcdefghijklm:LA_PASSWORD@aws-1-us-east-1.pooler.supabase.com:5432/postgres?sslmode=require
```

> Si la contraseña tiene `@`, `/`, `:` o `#`, hay que escaparla
> (`@` → `%40`, etc.). Lo más simple es generar una sin símbolos raros.

Guardar la cadena en un gestor de secretos; no copiarla al `.env` de desarrollo.

---

## 2. Subir el código

**Antes del primer arranque, del merge o de activar el despliegue:**

1. Verificar mediante [controles de solo lectura](docs/DESPLIEGUE_SEGURO_MCLEAN.md#verificación-de-solo-lectura) el servicio real, su rama y comandos efectivos, la identidad de Supabase y la revisión Alembic **inicial observada**. No asumir que el Blueprint de esta rama ya está aplicado.
2. Obtener autorización para el respaldo y ensayar su restauración en un destino aislado, siguiendo el [procedimiento](docs/DESPLIEGUE_SEGURO_MCLEAN.md#respaldo-y-restauración-a-ensayar). Confirmar el inventario y las diferencias antes de continuar.
3. Comparar la revisión inicial observada con la **revisión objetivo `b395c7281e4a`**. Si no coincide, detenerse: una migración es una operación separada que requiere destino identificado y autorización expresa. La primera revisión de la cadena del repositorio, `d61e48816ec5`, no demuestra cuál es la revisión inicial de la base real; una base nueva puede no tener aún `alembic_version`.
4. Solo tras la migración autorizada, si fuera necesaria, verificar por separado que el destino tenga la revisión objetivo y que el esquema sea compatible. Obtener autorización para incorporar a `main` y desplegar. Render está configurado para desplegar desde `main`; coordinar antes cualquier despliegue automático.

No aplicar el Blueprint ni iniciar esta versión mientras el esquema compatible y
las autorizaciones anteriores no estén verificados.

---

## 3. El servicio web en Render

### Actualización de un servicio existente

No crear otro Blueprint ni otro servicio. Antes de cualquier cambio, seguir la
[secuencia para retirar la migración automática](docs/DESPLIEGUE_SEGURO_MCLEAN.md#secuencia-para-retirar-la-migración-automática),
verificar el servicio y su configuración efectiva y obtener las autorizaciones
indicadas. El Blueprint de `main` puede conservar el build anterior; no
sincronizarlo sin revisar. Mantener el despliegue automático controlado hasta
completar el respaldo restaurable y verificar el esquema objetivo.

### Creación inicial de un Blueprint

Esta sección se aplica solo a una instalación nueva y autorizada. Completar
primero los controles del paso 2; crear o aplicar el Blueprint puede iniciar un
despliegue y no sustituye la migración autorizada ni su verificación previa.

1. En Render: **New → Blueprint**.
2. Elegí el repo `angelops1998/atletismo`. Render lee
   [`render.yaml`](render.yaml) y arma el servicio solo (plan, región, comandos
   de build y arranque, health check).
3. Te va a pedir las variables marcadas como `sync: false`:
   - **`DATABASE_URL`** → la cadena del paso 1.
   - **`CLUB_NOMBRE`**, **`CLUB_TELEFONO`**, **`CLUB_WHATSAPP`**,
     **`CLUB_EMAIL`**, **`CLUB_DIRECCION`**, **`CLUB_INSTAGRAM`**,
     **`CLUB_FACEBOOK`** → los datos reales del club. Los que no tengas,
     dejalos vacíos: la página pública los oculta.

   `SECRET_KEY` **no te la pide**: la genera Render sola y no la ve nadie.

4. **Solo después de completar el paso 2**, y con autorización para desplegar,
   **Apply**. Puede iniciar el primer deploy inmediatamente.

El build instala dependencias; **no ejecuta migraciones**. El esquema objetivo
debe estar verificado antes de pulsar Apply o permitir el primer arranque.

Cuando termine, arriba tenés la URL: `https://atletismo.onrender.com` (o con un
sufijo si el nombre estaba tomado).

---

## 4. Confirmar el esquema después del arranque

En Supabase: **Table Editor**. Tienen que estar las tablas `users`,
`partes_semanales`, `marcas`, `asistencias`, `pagos` y `alembic_version`.

Esta comprobación complementa la verificación anterior; ver tablas no demuestra
por sí solo la revisión ni las restricciones. Si hay discrepancias, detenerse.

---

## 5. Preparar una sesión administrativa separada

No intercambiar credenciales en el `.env` de desarrollo. Antes de cualquier
operación real, obtener autorización expresa y abrir un proceso administrativo
aislado, desde un directorio sin `.env` y con entorno de corta duración. Cargar
`DATABASE_URL` y `SECRET_KEY` desde un gestor de secretos por un canal protegido,
sin imprimirlos ni pasarlos en argumentos o historial; las variables de entorno
tienen prioridad sobre `.env` en la configuración de la aplicación.

En ese mismo entorno, realizar primero los [controles de identidad y revisión de
solo lectura](docs/DESPLIEGUE_SEGURO_MCLEAN.md#verificación-de-solo-lectura),
comparando además el proyecto Supabase mediante evidencia independiente. Si hay
cualquier discrepancia, ausencia de permisos o duda sobre el destino, detenerse.
No dejar accesible ese entorno para tareas de desarrollo; al terminar, cerrar el
proceso y eliminar sus credenciales temporales de forma segura.

---

## 6. Crear el profesor

El alta escribe en la base y requiere autorización específica, posterior a la
verificación del paso 5 y al esquema compatible. Ejecutar `scripts/crear_profesor.py`
con el intérprete del proyecto desde la sesión administrativa aislada, sin cambiar
su entorno ni el destino entre la verificación y el alta. El script **no verifica
por sí mismo la identidad del destino**: la comprobación previa no es una garantía
atómica; si no se puede mantener el destino verificado, no ejecutarlo. La cuenta
accede a datos de los atletas y debe usar una contraseña segura.

---

## 7. Probar

Entrá a `https://atletismo.onrender.com`:

- La página pública abre sin cuenta.
- `/auth/login` con el usuario del paso 6 te deja entrar al panel.
- Desde el panel, dar de alta un atleta y cargarle un parte.

Con el plan free, **la primera visita después de 15 minutos sin tráfico tarda
unos 50 segundos**: Render apaga el servicio y lo tiene que despertar. Las
siguientes son instantáneas. Si al club le molesta, en el panel de Render el
servicio se pasa a **Starter (US$7/mes)** con un clic y deja de dormirse.

---

## 8. Dar de baja el VPS

Recién cuando Render esté andando. En el VPS, como root:

```bash
# 1. Copia de seguridad por las dudas (queda en tu carpeta personal)
sudo -u postgres pg_dump atletismo -Fc -f /root/atletismo_final.dump

# 2. Apagar el servicio
sudo systemctl disable --now atletismo
sudo rm /etc/systemd/system/atletismo.service
sudo systemctl daemon-reload

# 3. Cerrar el puerto
sudo ufw delete allow 8003/tcp

# 4. Borrar la base y su usuario
sudo -u postgres psql -c 'DROP DATABASE atletismo;'
sudo -u postgres psql -c 'DROP USER atletismo;'

# 5. Borrar el código y el usuario del sistema
sudo rm -rf /opt/atletismo
sudo deluser --system atletismo

# 6. El cron de backups (borrá la línea de atletismo y guardá)
sudo crontab -u atletismo -l          # si tira "no crontab", ya no hay nada
```

**Ojo con el paso 5**: `pami` vive en el mismo VPS y comparte el Postgres. Los
comandos de arriba tocan solo la base `atletismo`, el usuario `atletismo` y
`/opt/atletismo` — no toques `/opt/pami` ni desinstales Postgres.

Bajate el dump del paso 1 antes de que se te olvide:

```bash
scp root@IP_DEL_VPS:/root/atletismo_final.dump .
```

---

## Actualizar la app a futuro

Antes de incorporar cambios a `main`, seguir [el procedimiento de preparación](docs/DESPLIEGUE_SEGURO_MCLEAN.md).
La migración es independiente del build y requiere verificación y autorización
expresas. Confirmar primero que el servicio efectivo de Render tiene el build
actualizado y no tiene comandos de predeploy o inicio que migren la base; el
archivo de la rama por sí solo no cambia la configuración ya desplegada.

---

## Backups

El alcance y la disponibilidad de las copias dependen del plan y de la
configuración de Supabase. Seguir [el procedimiento de respaldo y ensayo](docs/DESPLIEGUE_SEGURO_MCLEAN.md): incluye roles, esquema, datos y recursos externos, y exige comprobar la restauración aislada. No guardar copias ni credenciales en el repositorio.

> **La otra siesta:** en el plan free de Supabase, un proyecto **sin ninguna
> consulta durante 7 días se pausa** y hay que despertarlo a mano desde el
> panel. Mientras el club use la app no pasa; si el equipo para en vacaciones,
> entrá una vez por semana.

---

## Cuando consigas un dominio para el club

En Render: **Settings → Custom Domains → Add**. Te da los registros DNS
(un `CNAME`) para cargar donde compraste el dominio. El certificado HTTPS lo
emite y lo renueva Render solo — no hay certbot que configurar. `HTTPS_ONLY`
ya está en `true`, así que no hay nada más que tocar.

---

## Si algo no anda

| Síntoma | Causa casi siempre |
|---|---|
| El deploy muere con `Network is unreachable` | Usaste la **Direct connection** de Supabase (IPv6). Cambiá `DATABASE_URL` por la del **Session pooler**. |
| `Can't load plugin: sqlalchemy.dialects:postgres` | La URL empieza con `postgres://`. La app ya lo corrige sola; si aparece igual, poné `postgresql://` a mano. |
| `password authentication failed` | La contraseña tiene un símbolo sin escapar (`@`, `/`, `:`, `#`), o quedó el `[YOUR-PASSWORD]` del ejemplo. |
| `ZoneInfoNotFoundError` | Falta `tzdata` en `requirements-prod.txt`. |
| La app tarda ~50 s en abrir la primera vez | Es el plan free durmiéndose. Pasá a Starter. |
| `FATAL: Tenant or user not found` | En la URL del pooler el usuario es `postgres.<ref-del-proyecto>`, no `postgres` a secas. |

---

## Checklist final

- [ ] Proyecto de Supabase creado, password guardada en el gestor
- [ ] Identidad de servicio y base verificadas sin exponer credenciales
- [ ] Revisión inicial observada registrada y comparada con `b395c7281e4a`
- [ ] Respaldo real consistente, protegido y restaurado con éxito en entorno aislado
- [ ] Autorización expresa para respaldo, eventual migración, merge y despliegue; activación McLean por decisión separada
- [ ] Revisión objetivo y compatibilidad del esquema confirmadas **antes del primer arranque**
- [ ] Comandos efectivos de Render revisados sin migración automática y `FORMULARIO_MCLEAN_HABILITADO=false` efectivo
- [ ] `DATABASE_URL` es la del **Session pooler**, con `?sslmode=require`
- [ ] Supabase y Render en la misma región (`us-east` / Virginia)
- [ ] Blueprint aplicado en Render y build en verde
- [ ] Las tablas aparecen en el Table Editor de Supabase
- [ ] Profesor creado y login OK en `https://…onrender.com`
- [ ] Credenciales administrativas aisladas y retiradas; `.env` de desarrollo sin modificar
- [ ] Datos del club cargados en las variables `CLUB_*`
- [ ] VPS dado de baja (paso 8) y dump final descargado
