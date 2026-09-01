# Sistema del club de atletismo

Gestión de los afiliados de un club de atletismo: padrón, cuotas, asistencia,
marcas y —lo que le da sentido a todo lo demás— un **parte semanal** que cada
atleta carga desde el celular con cómo durmió, cómo comió y cómo entrenó. El
sistema convierte esos partes en alertas concretas para el profesor y en
estadísticas que permiten decidir a quién bajarle la carga y a quién subírsela.

Incluye además la **página pública** de promoción del club, que es lo único que
se ve sin cuenta.

## Cómo está hecho

FastAPI + Jinja2 renderizado en el servidor, SQLAlchemy 2.0 con Alembic sobre
PostgreSQL, sesión JWT en cookie httpOnly con renovación deslizante y protección
CSRF propia. El CSS está escrito a mano y es **mobile first**: los atletas cargan
el parte desde el teléfono. No hay frameworks de frontend ni librerías de
gráficos — los SVG se generan en el servidor (`app/services/grafico.py`), así la
página abre rápido con datos móviles. Por el mismo motivo **no se carga nada de
otro origen**: las tipografías se sirven desde `app/static/fonts`
(`scripts/bajar_fuentes.py` las rearma) y la CSP no habilita ningún externo.

Mismo stack y mismas convenciones que el proyecto `pami`.

```
app/
├── main.py              middlewares (CSRF, sesión deslizante) y manejadores de error
├── auth.py              login, roles y control de la contraseña provisoria
├── tiempo.py            hora local del club y el lunes de cada semana
├── models/              users · partes_semanales · marcas · asistencias · pagos
├── routers/             una pantalla por archivo
├── services/
│   ├── bienestar.py     cálculos sobre los partes y las series semanales
│   ├── alertas.py       las reglas que convierten los datos en avisos accionables
│   ├── cobranza.py      estado de cuenta, deuda y cobranza del mes
│   ├── pruebas.py       catálogo de pruebas de atletismo
│   └── grafico.py       geometría de los gráficos SVG
├── templates/
└── static/css/main.css  mobile first: las media queries son todas min-width
```

## Instalación

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
createdb atletismo
cp .env.example .env      # completar DATABASE_URL, SECRET_KEY y los datos del club
.venv/bin/alembic upgrade head
.venv/bin/python scripts/crear_profesor.py
```

La `SECRET_KEY` de producción se genera con:

```bash
python -c "import secrets; print(secrets.token_hex(64))"
```

Para levantarlo en desarrollo (puerto 8002):

```bash
.venv/bin/python run.py
```

En producción va detrás de nginx con HTTPS, y en el `.env` **tiene que quedar**
`HTTPS_ONLY=true` para que las cookies de sesión no viajen por HTTP.

## Datos de ejemplo

```bash
.venv/bin/python scripts/seed.py
```

Carga un profesor, doce atletas y dieciséis semanas de partes, marcas,
asistencias y pagos. Están armados para que se vea cada situación que el sistema
detecta: alguien que no carga el parte, alguien que sube la carga de golpe, una
molestia arrastrada y tres atletas con deuda.

- Profesor: usuario `profe`, contraseña `profesor123`
- Atleta: usuario `lfernandez`, contraseña `atletismo123`

`scripts/seed.py --borrar` vacía la base y la vuelve a cargar. **No usarlo en
producción.**

## Tests

```bash
.venv/bin/pytest
```

Corren sobre SQLite en memoria: no hace falta Postgres ni el `.env`, y no hay
forma de que toquen los datos del club. Cubren los cálculos que no se guardan en
ninguna columna —bienestar, carga, ACWR, deuda— porque si uno se corre de lugar
no hay nada que lo delate: la pantalla muestra un número plausible y equivocado.
El resto son regresiones de cosas que estuvieron mal alguna vez y conviene que
fallen ruidosamente: el control CSRF, la separación de roles, los destinos de
redirección y los rangos de lo que se carga a mano.

## Cómo se usa

**El atleta** entra una vez por semana y completa el parte: cinco preguntas de
bienestar de 1 a 5, horas de sueño, alimentación, peso, carga de entrenamiento y
molestias. Le lleva dos minutos. Después ve su propia evolución y sus marcas —
si no ve para qué sirve lo que carga, deja de cargarlo.

**El profesor** abre el panel y lo primero que ve son las alertas: quién no
cargó, quién viene con el bienestar bajo, quién reportó dolor, quién subió la
carga demasiado rápido y quién debe cuotas. Después están las tendencias del
grupo, el padrón, la lista de asistencia, las marcas y las estadísticas.

### Las alertas

Los umbrales están todos juntos y comentados en `app/services/alertas.py`, para
poder ajustarlos después de usar el sistema unos meses:

| Alerta | Cuándo salta |
|---|---|
| No cargó el parte | No completó la semana en curso |
| Bienestar bajo | 12 o menos sobre 25, o un 1 en cualquier pregunta |
| Cayó su bienestar | 20% por debajo de **su propio** promedio de 4 semanas |
| Reportó una molestia | Dolor 5/10 o más |
| Duerme poco | Dos semanas seguidas por debajo de 7 h |
| Subió mucho la carga | Ratio agudo:crónico mayor a 1.5 — riesgo de lesión |
| Cambio de peso | Más de 3% contra su promedio del último mes |
| Cuota vencida | Debe uno o más meses |

Cada atleta se compara **consigo mismo** y no con el promedio del club: hay
chicos que siempre puntúan 3 y otros que siempre puntúan 5, y contra el grupo el
primero se vería siempre en rojo aunque no haya cambiado nada.

## Decisiones que conviene conocer antes de tocar el código

- **Un parte por semana, identificado por el lunes.** La clave es
  `(atleta_id, semana)` con `semana` = lunes de esa semana. El atleta que entra
  el jueves y el que entra el domingo escriben la misma fila, y si vuelve a
  entrar edita en vez de duplicar. Se puede completar hacia atrás una sola
  semana: más que eso ya no es un recuerdo, es una invención.
- **Nada calculado se guarda.** El bienestar total, la carga y la deuda se
  calculan al vuelo. Con 30 atletas no cuesta nada, y una columna calculada que
  se desincroniza miente peor que no tenerla.
- **La deuda sale de comparar meses.** `users.cobro_desde` contra los `periodo`
  de la tabla `pagos`. Por eso `periodo` (el mes que cubre el pago) es distinto
  de `fecha_pago`: en marzo se cobra marzo y también el febrero que quedó
  debiendo.
- **A los atletas no se los borra**, se los da de baja. Sus partes, marcas y
  pagos son el historial del club, y el que se va suele volver al año siguiente.
- **Las contraseñas las da el profesor en mano** y la app obliga a cambiarlas al
  entrar. No hay registro público ni recuperación por correo: son 30 personas y
  varias no tienen mail propio.

## Qué falta / qué habría que cambiar al ponerlo en producción

- La zona horaria está fijada en `app/tiempo.py` (`America/La_Paz`).
  Si el club no está en Bolivia, es lo único que hay que tocar.
- El staff y los atletas destacados de la página pública están escritos en
  `app/templates/publico/landing.html` — hay que reemplazarlos por los del club
  de verdad, con sus fotos.
- El resto de los datos del club (nombre, teléfono, WhatsApp, dirección, redes)
  salen del `.env`.
