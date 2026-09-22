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

Guardá esa cadena: la vas a pegar dos veces (paso 3 y paso 5).

---

## 2. Subir el código

```bash
git push origin main
```

Render despliega desde `main`, así que lo que no esté ahí no se publica.

---

## 3. El servicio web en Render

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

4. **Apply**. El primer deploy tarda unos minutos: instala las dependencias y
   corre `alembic upgrade head` contra Supabase.

Cuando termine, arriba tenés la URL: `https://atletismo.onrender.com` (o con un
sufijo si el nombre estaba tomado).

---

## 4. Revisar que el esquema se haya creado

En Supabase: **Table Editor**. Tienen que estar las tablas `users`,
`partes_semanales`, `marcas`, `asistencias`, `pagos` y `alembic_version`.

Si no están, mirá **Logs** en Render: el error de `alembic` sale en el log del
build, no en el de la app.

---

## 5. Apuntar tu máquina a Supabase

Para crear el profesor necesitás correr un script contra la base de producción
desde tu máquina. En el `.env` local, **comentá** tu `DATABASE_URL` de
desarrollo y poné la de Supabase:

```bash
# DATABASE_URL=postgresql://atletismo:...@127.0.0.1:5432/atletismo   # local
DATABASE_URL=postgresql://postgres.abcdefghijklm:LA_PASSWORD@aws-1-us-east-1.pooler.supabase.com:5432/postgres?sslmode=require
```

---

## 6. Crear el profesor

```bash
.venv/bin/python scripts/crear_profesor.py
```

Te pide nombre, usuario y contraseña. Usá una contraseña de verdad: con esa
cuenta se ven los datos de todos los atletas.

**Cuando termine, volvé a dejar tu `DATABASE_URL` local en el `.env`.** Si te
la olvidás apuntando a Supabase, el próximo `scripts/seed.py --borrar` que
corras para probar algo vacía la base del club.

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

```bash
git push origin main
```

Nada más. Render detecta el push, instala, corre `alembic upgrade head` y
reemplaza la versión anterior. Si el build falla, la versión vieja sigue
sirviendo: no se cae la app.

---

## Backups

Supabase hace backups diarios automáticos (**Database → Backups**). En el plan
free se retienen pocos días y **no se pueden restaurar desde el panel**, así que
una vez por mes, o antes de cualquier cambio grande, bajate una copia vos:

```bash
pg_dump "$DATABASE_URL" -Fc -f atletismo_$(date +%Y%m%d).dump
```

Guardala fuera de la máquina (los `.dump` están en `.gitignore`: son datos de
menores de edad y no van al repo).

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
- [ ] `DATABASE_URL` es la del **Session pooler**, con `?sslmode=require`
- [ ] Supabase y Render en la misma región (`us-east` / Virginia)
- [ ] Blueprint aplicado en Render y build en verde
- [ ] Las tablas aparecen en el Table Editor de Supabase
- [ ] Profesor creado y login OK en `https://…onrender.com`
- [ ] `.env` local **devuelto** a la base de desarrollo
- [ ] Datos del club cargados en las variables `CLUB_*`
- [ ] VPS dado de baja (paso 8) y dump final descargado
