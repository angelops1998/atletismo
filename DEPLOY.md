# Despliegue de Atletismo en producción (VPS)

Guía paso a paso para poner la app en el VPS **sin dominio propio todavía**,
conviviendo con los otros sitios que ya tenés alojados ahí (comparten IP y
nginx; esta app por ahora no usa nginx, se accede directo por IP:puerto).

Reemplazá en todos lados:
- `IP_DEL_VPS` → la IP pública del VPS

Todo lo que empieza con `sudo` lo corrés vos en la terminal del VPS.

Mismo stack y mismas convenciones que el proyecto `pami` que ya tenés
desplegado ahí — si algo no está detallado acá, es porque es igual a como lo
hiciste con pami.

---

## 0. Antes de empezar

Conectate por SSH y confirmá que el puerto 8002 está libre (pami usa el 8001):

```bash
ssh root@IP_DEL_VPS
sudo ss -tlnp | grep -E ':8001|:8002'
```

Si el 8002 ya lo usa otra cosa, cambialo en `deploy/atletismo.service`,
`run.py` y esta guía antes de seguir.

---

## 1. PostgreSQL en el VPS

Reutilizá el Postgres que ya tenés instalado para pami; solo hace falta un
usuario y una base nuevos:

```bash
sudo -u postgres psql <<'SQL'
CREATE USER atletismo WITH PASSWORD 'PONE_UNA_PASSWORD_FUERTE';
CREATE DATABASE atletismo OWNER atletismo;
SQL
```

---

## 2. Usuario del sistema y código

```bash
sudo adduser --system --group --home /opt/atletismo atletismo
sudo -u atletismo git clone https://github.com/angelops1998/atletismo.git /opt/atletismo
cd /opt/atletismo
```

---

## 3. Entorno Python y dependencias

```bash
# python3-venv, build-essential y libpq-dev ya deberían estar del deploy de pami
sudo -u atletismo python3 -m venv /opt/atletismo/.venv
sudo -u atletismo /opt/atletismo/.venv/bin/pip install --upgrade pip
sudo -u atletismo /opt/atletismo/.venv/bin/pip install -r /opt/atletismo/requirements-prod.txt
```

---

## 4. Configuración (.env) y migraciones

```bash
sudo -u atletismo cp /opt/atletismo/.env.example /opt/atletismo/.env

# Generar una SECRET_KEY nueva
/opt/atletismo/.venv/bin/python -c "import secrets; print(secrets.token_hex(64))"

# Editar: DATABASE_URL (con la password del paso 1), SECRET_KEY, y los datos
# del club (CLUB_NOMBRE, CLUB_TELEFONO, etc.). HTTPS_ONLY se queda en false
# por ahora: no hay HTTPS hasta que haya dominio + certbot.
sudo -u atletismo nano /opt/atletismo/.env

cd /opt/atletismo
sudo -u atletismo /opt/atletismo/.venv/bin/alembic upgrade head
```

---

## 5. Servicio systemd

```bash
sudo cp /opt/atletismo/deploy/atletismo.service /etc/systemd/system/atletismo.service
sudo systemctl daemon-reload
sudo systemctl enable --now atletismo
sudo systemctl status atletismo          # debe decir "active (running)"
curl -I http://127.0.0.1:8002/            # debe dar 200 o 303 (redirect a login)
```

---

## 6. Firewall: abrir el puerto 8002

Como todavía no hay nginx delante, el puerto se expone directo:

```bash
sudo ufw allow 8002/tcp
sudo ufw status
```

Postgres (5432) sigue sin exponerse: la app lo usa por `127.0.0.1`.

---

## 7. Cargar el profesor

```bash
cd /opt/atletismo
sudo -u atletismo /opt/atletismo/.venv/bin/python scripts/crear_profesor.py
```

Después entrás a `http://IP_DEL_VPS:8002`, iniciás sesión como profesor y das
de alta a los atletas desde el panel.

---

## 8. Backups automáticos

```bash
sudo chmod +x /opt/atletismo/deploy/backup.sh
sudo crontab -u atletismo -e
# agregá esta línea (backup diario 3:20 AM, retiene 14 días):
20 3 * * * /opt/atletismo/deploy/backup.sh >> /opt/atletismo/backups/backup.log 2>&1
```

---

## Cuando consigas un dominio para el club

1. Apuntá el dominio (registro A) a `IP_DEL_VPS`.
2. En `/etc/systemd/system/atletismo.service` cambiá `--bind 0.0.0.0:8002` por
   `--bind 127.0.0.1:8002` y `sudo systemctl restart atletismo`.
3. Seguí los pasos que ya están comentados arriba de
   [`deploy/nginx-atletismo.conf`](deploy/nginx-atletismo.conf): copiar el
   server block, `certbot --nginx`, y poner `HTTPS_ONLY=true` en el `.env`.
4. `sudo ufw delete allow 8002` — ya no hace falta exponer el puerto directo,
   nginx pasa a ser la única puerta de entrada (80/443).

---

## Actualizar la app a futuro (nuevo deploy)

```bash
cd /opt/atletismo
sudo -u atletismo git pull
sudo -u atletismo /opt/atletismo/.venv/bin/pip install -r requirements-prod.txt
sudo -u atletismo /opt/atletismo/.venv/bin/alembic upgrade head
sudo systemctl restart atletismo
```

---

## Checklist final

- [ ] Postgres con usuario/password (no `trust`), base `atletismo` creada
- [ ] `.env` con SECRET_KEY nueva, DATABASE_URL correcta, datos del club
- [ ] `alembic upgrade head` corrido sin errores
- [ ] `systemctl status atletismo` = running
- [ ] ufw permite 8002/tcp
- [ ] `http://IP_DEL_VPS:8002` responde y el login funciona
- [ ] profesor creado, login OK
- [ ] cron de backups configurado
- [ ] (más adelante) dominio + nginx + certbot + `HTTPS_ONLY=true`
