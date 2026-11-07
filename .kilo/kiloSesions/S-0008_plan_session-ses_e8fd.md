# Auditoría módulo reportes atletismo

**Session ID:** ses_e8fde395efferAynmjQo7G63tf
**Created:** 10/24/2026, 6:57:04 PM
**Updated:** 11/7/2026, 3:59:55 PM

---

## User

# READ-ONLY AUDIT — ATHLETICS REPORTING MODULE

## Objective

Investigate the current weekly athlete-reporting module in the local repository `C:\Archivos.Diego\atletismoWeb\atletismo` and determine the minimum changes needed to support independent daily reports while preserving historical weekly records.

Reference repository: `https://github.com/angelops1998/atletismo`

Reference deployment: `https://atletismo.onrender.com/parte?semana=2026-10-12`

Treat the local workspace as the source of truth. Do not assume it matches GitHub or production. The deployed page may require authentication.

## Kilo Mode and Session

- Mode: Ask
- New Kilo Session: YES
- Scope: Read-only investigation and technical diagnosis.

## Mandatory Constraints

- Do not modify source files, templates, tests, configuration, dependencies, documentation, or migrations.
- Do not modify the database or application state.
- Do not create files, including audit reports or plans, inside the repository.
- Do not run migrations, seed operations, application workflows, or commands that may alter data.
- Do not commit, push, merge, create PRs, or deploy.
- Do not expose credentials, tokens, personal information, or secrets.
- Do not perform a general dependency audit.
- Preserve all pre-existing user changes and Git state.
- Do not claim that tests passed unless they were actually executed. Prefer reviewing existing tests without running them unless execution is demonstrably safe and read-only.

## Investigation

### 1. Establish the baseline

1. Verify the workspace root and repository identity.
2. Inspect the current branch, Git status, and relevant recent history without changing anything.
3. Inspect available Kilo session records and identify relevant prior findings, but do not reuse a session as the active working session.
4. Identify the project's framework, routing conventions, database layer, migration system, and test framework from actual files.
5. Verify relevant local paths before relying on them.

### 2. Trace the current reporting workflow

Locate and inspect the actual endpoints, HTTP methods, templates, form components, schemas, models, services, and queries involved.

Document:
- Current questions, fields, choices, required/optional status, defaults, and validation rules.
- Which values appear in the UI versus which are actually persisted.
- How the athlete identity and reporting week are determined.
- Create, read, update, resubmission, and duplicate-submission behavior.
- Authorization rules for athletes, coaches, and administrators.
- Week boundaries, date handling, timezone assumptions, and relevant calculations.

Trace the complete data flow from request to validation, persistence, and subsequent reads. Cite repository-relative file paths and relevant functions or classes.

### 3. Inspect persistence and historical compatibility

Inspect SQLAlchemy models, relationships, constraints, services, queries, and Alembic migrations.

Determine:
- The entity or entities that store reports and their relationships to athletes.
- Persisted versus calculated fields.
- Existing uniqueness constraints and whether they enforce one report per athlete per week.
- Handling of optional, empty, and missing answers.
- Existing history or audit behavior.
- Other modules that read or aggregate report data.

Distinguish what source code proves from what would require authorized access to the deployed database. Do not infer the production schema solely from local configuration or migration files.

### 4. Map functional dependencies

Search for report references across:
- Wellness and training load.
- Alerts and risk indicators.
- Statistics, charts, and dashboards.
- Athlete and coach views.
- Attendance and related modules.
- Automated tests and scheduled jobs.

Identify assumptions tied to weekly reporting, including queries, date filters, aggregation windows, uniqueness checks, and calculations. Explain which could break or change meaning with daily records.

Do not invent new wellness, workload, or risk formulas.

### 5. Assess daily-report design options

Compare at least these options:

A. Adapt the existing report model to support one report per athlete per date while preserving weekly historical records.

B. Introduce a complementary daily-report entity and retain the existing weekly model.

For each option, assess:
- Data integrity and uniqueness.
- Schema and migration complexity.
- Historical-data preservation.
- Compatibility with current consumers and dashboards.
- Query and aggregation changes.
- Authorization and validation.
- Rollback and deployment risks.

Recommend the least disruptive viable design based on verified evidence. If neither option can be recommended confidently, explain the missing information.

Evaluate the requirements for:
- Creating, viewing, and editing a report for a specific athlete and date.
- Preventing duplicate reports for the same athlete and date.
- Browsing daily history.
- Preserving access to existing weekly records.
- Maintaining consistent downstream statistics and alerts.

Do not implement anything.

### 6. Review tests and future acceptance criteria

Inspect existing relevant tests and map their coverage.

Propose future tests for:
- Daily report creation and editing.
- Uniqueness per athlete and date, including concurrent submissions where relevant.
- Authorization and cross-athlete data isolation.
- Date boundaries and timezone behavior.
- Optional fields, validation, and empty answers.
- Preservation and retrieval of historical weekly records.
- Statistics, alerts, dashboards, and other affected consumers.

Identify which existing tests may require adaptation. Do not claim execution or success without evidence.

## Required Final Report

Deliver a concise Spanish-language technical diagnosis with these sections:

1. **Resumen ejecutivo:** current behavior and main obstacle to daily reporting.
2. **Flujo actual comprobado:** endpoint to validation, persistence, and subsequent reads.
3. **Campos reales:** questions and options shown in the UI, required status, validation, and actual persisted fields.
4. **Archivos relevantes:** verified repository-relative paths and their roles.
5. **Dependencias funcionales:** consumers of reports and weekly assumptions that could conflict with daily reporting.
6. **Diseño recomendado:** comparison of alternatives and evidence-based recommendation.
7. **Datos históricos:** preservation strategy, migration implications, and risks.
8. **Decisiones pendientes:** questions, fields, and behavior that require product-owner input. Do not decide which questions to add, remove, or modify.
9. **Implementation outline:** minimum anticipated changes, possible migration, and acceptance tests. Planning only; no implementation.
10. **Limitations:** inaccessible files, unavailable production information, authentication barriers, and unresolved uncertainties.
11. **Verification log:** files inspected, read-only commands used, tests reviewed or run, results, and pending checks.

Clearly label statements as VERIFIED, INFERRED, or PROPOSED when their evidence status could otherwise be ambiguous.

## Final Safety Confirmation

Explicitly confirm whether any files, database records, application state, or Git history were changed. The expected result is no changes.

Do not implement the proposed design. Wait for the user to review the diagnosis and define the new questions before any implementation is authorized.

---

## Assistant

**Tool: skill**

---

## Assistant

**Tool: bash**

---

## Assistant

**Tool: bash**

---

## Assistant

**Tool: bash**

---

## Assistant

**Tool: bash**

---

## Assistant

**Tool: bash**

---

## Assistant

I'll start by exploring the repository structure to understand the project layout, framework, and locate the reporting/athlete functionality.


**Tool: read**

---

## Assistant

**Tool: read**

---

## Assistant

**Tool: bash**

---

## Assistant

**Tool: bash**

---

## Assistant

**Tool: grep**

---

## Assistant

**Tool: read**

---

## Assistant

**Tool: read**

**Tool: read**

---

## Assistant

**Tool: read**

---

## Assistant

**Tool: grep**

---

## Assistant

**Tool: read**

---

## Assistant

**Tool: read**

---

## Assistant

**Tool: read**

---

## Assistant

**Tool: read**

---

## Assistant

**Tool: read**

---

## Assistant

**Tool: read**

---

## Assistant

**Tool: read**

---

## Assistant

**Tool: read**

---

## Assistant

**Tool: read**

---

## Assistant

**Tool: read**

---

## Assistant

**Tool: read**

---

## Assistant

**Tool: read**

---

## Assistant

**Tool: read**

---

## Assistant

Let us look at tiempo utilities and conftest.


**Tool: read**

---

## Assistant

# AUDITORÍA READ-ONLY - MÓDULO DE REPORTE DE ATLETAS (PARTE SEMANAL)

## 1. RESUMEN EJECUTIVO

**Comportamiento actual (VERIFICADO):** El sistema maneja un "parte semanal" (`app/routers/parte.py`, modelo `app/models/parte.py`). Los atletas cargan su parte **una vez por semana**; la clave es `(atleta_id, semana)` donde `semana` es siempre el lunes de esa semana (calculado con `lunes_de()` en `app/tiempo.py`). El formulario se muestra en `/parte` (solo rol `atleta`), con validación estricta. Si ya existe un registro para (atleta, semana), se **edita** en lugar de crear uno nuevo (lógica en `parte.guardar`). 

**Obstáculo principal para reportes diarios (VERIFICADO):** 
- **Restricción de unicidad a nivel BD**: `UniqueConstraint("atleta_id", "semana", name="uq_parte_atleta_semana")` en `app/models/parte.py:25`. Esto impide múltiples registros para el mismo atleta en la "misma semana" tal como está definida.
- **La "semana" es el eje del dominio**: todo el sistema (servicios `bienestar`, alertas, paneles, gráficas, cruces con marcas/asistencias) filtra/agrega por `ParteSemanal.semana` (lunes). Cambiar a diario requiere repensar llaves, ventanas de agregación, umbrales, y consultas.
- **Ventana de edición limitada**: solo se permite completar/editar la semana actual o la semana inmediatamente anterior (`SEMANAS_EDITABLES = 1` en `app/routers/parte.py:17-20`). Esto es intencional para evitar "inventar" datos pasados.
- **Campos derivados vs persistidos**: muchos indicadores (bienestar total, semáforos, carga UA/sRPE) se calculan al vuelo en `app/services/bienestar.py` - esto es flexible, pero las consultas que asumen granularidad semanal sí son las que romperían.

## 2. FLUJO ACTUAL COMPROBADO

### Endpoints (VERIFICADO - `app/routers/parte.py`)
- `GET /parte?semana=YYYY-MM-DD` (opcional). 
  - Requiere usuario autenticado via `get_current_user` (`app/auth.py`). 
  - Solo `user.role == "atleta"` (403 si no lo es).
  - `objetivo = _semana_pedida(semana)`: si no se pasa, usa `lunes_actual()`; si fecha inválida → actual; si futuro → actual; si > 1 semana atrás → 403 "Esa semana ya está cerrada. Avisale al profesor." (`SEMANA_EDITABLES=1`).
  - Obtiene `parte = bienestar.parte_de_semana(db, user.id, objetivo)`. 
  - Renderiza `templates/atleta/parte.html` con contexto: `user`, `semana` (lunes), `parte`, `items`/`etiquetas`/`rpe_escala`/`rpe_franjas`, `es_semana_actual`, `parte_pendiente` (bool si no hay parte para semana actual), `falta_anterior` (si semana actual y falta semana anterior), `semana_anterior`.
- `POST /parte` (form `application/x-www-form-urlencoded`, con CSRF). 
  - Mismos chequeos de rol/usuario.
  - Valida semana con `_semana_pedida`. 
  - Convierte bienestar 1-5 vía `_entero` para `sueno_calidad, dolor_muscular, estres, animo` (todos obligatorios; si falta alguno → error "Faltan responder: ..." y status 422, re-renderiza formulario con `form`).
  - RPE: obligatorio salvo `sesiones == 0` (ver `TestRPE.test_si_no_entreno_no_se_le_pide`). Si requerido y ausente/ inválido → 422 con mención a RPE. Rango 1-10.
  - Molestias: si `molestias == "si"`, requiere `molestia_zona` (no vacío tras strip) y `molestia_dolor` 0-10; si falla → 422.
  - Si hay errores → re-render con template, `errores[]`, `form`, status 422 (no guarda).
  - Busca parte existente con `bienestar.parte_de_semana(db, user.id, objetivo)`. Si no existe, crea `ParteSemanal(atleta_id=user.id, semana=objetivo)` y lo agrega a sesión. Si existe → edita esa instancia.
  - Asigna campos (ver sección 3). 
  - `db.commit()` → `RedirectResponse("/inicio?parte=1", 302)`.

### Validación (VERIFICADO)
- Enteros 1-5 para ítems bienestar (4 ítems). `_entero` retorna None si fuera de rango/tipo inválido.
- RPE 1-10 vía `_entero(rpe,1,10)`, obligatorio salvo `sesiones==0`.
- `sesiones` 0-21, `minutos_totales` 0-3000 (opcionales pero validados si presentes con esos rangos? El código guarda directamente tras obtener `_entero` - si devuelve None, se guarda None).
- Decimales con coma: `_decimal` normaliza `,`→`.` con `Decimal`. Rangos: `horas_sueno` 0-24, `hidratacion_litros` 0-15, `peso_kg` 20-250.
- Molestias condicionales validadas.
- Semana futura → redirige a actual. >1 semana atrás → 403.

### Persistencia y lecturas subsiguientes (VERIFICADO)
- Modelo `ParteSemanal` (SQLAlchemy) tabla `partes_semanales`. Unicidad `(atleta_id, semana)`. Índices en `atleta_id` y `semana`.
- Creación/edición en misma ruta POST; `db.commit()`.
- Lecturas vía `app/services/bienestar.py`: `parte_de_semana`, `partes_de` (últimas N semanas), `serie_individual`, `series_de` (varios atletas en 1 consulta), `serie_grupo` (promedios club por semana), `promedio_items_grupo`, `cruce_con_marcas`.
- Timestamps: `enviado = DateTime(timezone=True), server_default=func.now()`, `actualizado = DateTime(timezone=True), onupdate=func.now()`.

## 3. CAMPOS REALES

### Preguntas/ítems mostrados en UI (VERIFICADO - `app/templates/atleta/parte.html`, `app/services/bienestar.py`)
**Sección "¿Cómo estuviste esta semana?"** (4 ítems obligatorios, escala 1-5 con etiquetas):
1. Sueño - "¿Cómo dormiste esta semana?" (`sueno_calidad`) etiquetas: Muy mal..Muy bien
2. Dolor muscular - "¿Cómo estuvieron tus músculos?" (`dolor_muscular`) etiquetas: Muy dolorido..Sin dolor  
3. Estrés - "¿Qué tan tranquilo estuviste?" (`estres`) etiquetas: Muy estresado..Muy tranquilo
4. Ánimo - "¿Cómo estuvo tu ánimo?" (`animo`) etiquetas: Muy bajo..Muy bien

**Sección "Sueño y alimentación"**:
- Horas de sueño por noche (`horas_sueno`, numérico decimal step 0.5, 0-24, opcional)
- Litros de agua por día (`hidratacion_litros`, decimal 0-15, opcional)
- "¿Cómo comiste esta semana?" (`alimentacion_calidad`, escala 1-5 opcional en UI - pero ver validación abajo)
- Comidas por día (`comidas_dia`, entero 0-10, opcional)
- Peso (kg) (`peso_kg`, decimal 0.1 step 20-250, opcional)
- "¿Comiste algo antes de entrenar?" (`come_antes_entrenar`, binario si/no, opcional)
- Suplementos o vitaminas (texto, opcional, maxlength 200)

**Sección "Entrenamiento"**:
- Entrenamientos que hiciste (`sesiones`, 0-21, opcional)
- Minutos en total (`minutos_totales`, 0-3000, opcional)  
- RPE - "¿qué tan duro te resultó entrenar esta semana?" (`rpe`, 1-10 con descriptores/franjas, **obligatorio salvo sesiones==0**)

**Sección "Molestias"**:
- "¿Tenés alguna molestia o dolor?" (`molestias`, binario) - si "si" requiere zona y dolor
- Zona (`molestia_zona`, texto 80 chars)
- Dolor 0-10 escala numérica

**Sección "Algo más que el profesor deba saber"**:
- Comentarios (`comentarios`, textarea 1000 chars, opcional)

### Requeridos/validación (VERIFICADO)
- **Obligatorios (hard fail 422 si faltan):** `sueno_calidad, dolor_muscular, estres, animo` (los 4 de ITEMS). `rpe` obligatorio si `sesiones != 0` (o si sesiones no indica 0). Si molestias="si": `molestia_zona` no vacío y `molestia_dolor` 0-10.
- **Condicionales**: RPE según sesiones.
- **Opcionales con validación de rango**: todos los demás numéricos/decimales; si fuera de rango → `_entero`/`_decimal` devuelve None y se guarda None (ver `test_los_valores_imposibles_se_descartan`).
- **Default en modelo**: `molestias` tiene `default=False, server_default="false"`, `enviado` con `server_default=func.now()`. Otros opcionales nullable.

### Persistidos vs UI (VERIFICADO)
**Persistidos en `partes_semanales`:** `id, atleta_id, semana, sueno_calidad, fatiga(nullable tras migración), dolor_muscular, estres, animo, horas_sueno, comidas_dia, alimentacion_calidad, hidratacion_litros, come_antes_entrenar, suplementos, peso_kg, sesiones, minutos_totales, rpe, molestias, molestia_zona, molestia_dolor, comentarios, enviado, actualizado`. 
**Notas:**
- `fatiga` (energía) existía originalmente (NOT NULL) pero migración `a3f1c9e27b04` lo hizo nullable; ya no se pregunta en UI y no se suma a bienestar (ver comentarios en modelo/servicio). Se conserva por datos históricos.
- UI muestra `alimentacion_calidad` con escala opcional (label dice "¿Cómo comiste esta semana?") pero **no está en ITEMS obligatorios** - código solo valida/guarda; no hay validación obligatoria en POST para él (a diferencia de los 4 ITEMS). Tests no muestran obligatoriedad.
- `rpe` sí se guarda (nullable) cuando no aplica por sesiones==0.
- Todo lo mostrado arriba se persiste según asignación en POST.

## 4. ARCHIVOS RELEVANTES

| Archivo | Rol (VERIFICADO) |
|---------|-------------------|
| `app/routers/parte.py` | Rutas GET/POST `/parte`, validación, creación/edición por (atleta, semana), ventana de edición (SEMANAS_EDITABLES=1) |
| `app/models/parte.py` | Modelo `ParteSemanal`, unicidad `(atleta_id, semana)`, esquema columnas |
| `app/services/bienestar.py` | Cálculos (bienestar_total/pct, carga_ua/sRPE, semáforo), consultas (`parte_de_semana`, `partes_de`, series), agregados grupo/cruce con marcas |
| `app/services/alertas.py` | Genera alertas desde partes semanales (sin_parte, bienestar, molestias). Usa `ultima["parte"]` |
| `app/services/grafico.py` | Gráficas que asumen series semanales (comentarios sobre huecos por semanas sin parte) |
| `app/templates/atleta/parte.html` | Formulario semanal completo |
| `app/templates/_tabbar.html`, `app/templates/_nav.html`, `app/templates/_iconos.html` | Navegación/marcado UI |
| `app/tiempo.py` | `lunes_de`, `lunes_actual`, zona horaria Bolivia (America/La_Paz) |
| `app/models/__init__.py` | Registra `ParteSemanal` |
| `alembic/versions/d61e48816ec5_esquema_inicial_usuarios_partes_.py` | Creación tabla con unicidad inicial |
| `alembic/versions/a3f1c9e27b04_fatiga_opcional_rpe_reemplaza_energia.py` | Hace `fatiga` nullable |
| `tests/test_parte.py` | Tests de flujo, validación, RPE, permisos |
| `app/main.py` | Monta router `parte` |
| `app/routers/atletas.py` | Usa series de partes para semáforos/panel |

## 5. DEPENDENCIAS FUNCIONALES

**Consumidores directos (VERIFICADO):**
- `app/services/alertas.py`: construye alertas desde última parte por atleta. `_sin_parte` revisa si hay parte; `_bienestar` usa `bienestar.bienestar_total(parte)`, revisa ítems en 1; `_molestia` lee `parte.molestias`, `molestia_dolor`, `molestia_zona`. Asume estructura semanal.
- `app/services/bienestar.py`: casi todo el módulo opera sobre `ParteSemanal` por semana (series, promedios, cruces).
- `app/routers/atletas.py`: panel de padrón usa `bienestar.series_de`, muestra semáforo/bienestar desde serie; lógica comenta "parte de la semana en curso es la última fila de la serie" (`line ~168-181`).
- `app/services/grafico.py`: trabaja con series semanales, comenta huecos (semanas sin parte).
- Cruce con marcas (`cruce_con_marcas`): une por `(atleta_id, lunes_de(fecha_marca))` - asume parte semanal corresponde a semana de la marca.

**Supuestos semanales que podrían romperse con diario (VERIFICADO/INFERIDO):**
- **Clave única** `(atleta_id, semana)` → diario necesitaría `(atleta_id, fecha)` o entidad separada.
- **Agregación**: "parte de la semana", promedios semanales, conteo "partes cargados", semáforos por semana - todo asume 1 registro/semana.
- **Ventana editable** `SEMANAS_EDITABLES=1` - con diario la semántica cambia (¿editar último X días? ¿historial completo editable?).
- **Cruce marca-semana** (`lunes_de(m.fecha)`) - si hay parte diario, ¿qué parte usar para cruzar con marcas de esa semana? ¿promedio diario? ¿último? ¿suma? Esto **no está decidido**.
- **Alertas** "sin_parte" esta semana - con diario podría ser "sin parte hoy/últimos días".
- **sRPE/carga**: `carga_ua = rpe * minutos_totales` se calcula por registro; con diario el significado de "carga semanal" cambia (suma vs promedio vs último).
- **"Una vez por semana"** es regla de negocio explícita - pasar a diario cambia completamente el producto.

## 6. DISEÑO RECOMENDADO (comparación)

### Opción A: Adaptar modelo existente `ParteSemanal` a reporte diario
**Cambios necesarios (INFERIDO):**
- Cambiar clave única de `(atleta_id, semana)` a `(atleta_id, fecha)` (o añadir `fecha` nullable + migración compleja). Renombrar semánticamente `semana` → `fecha` o añadir `fecha_reporte`.
- Eliminar/ajustar lógica que asume lunes como llave. 
- Actualizar todos los servicios (`bienestar`, `alertas`) que filtran por `semana`/lunes.
- Migrar datos existentes: cada `ParteSemanal` actual tendría que mapearse a alguna fecha? **No hay fecha diaria guardada** - solo `semana` (lunes). No es obvio cómo convertir histórico semanal a "diario" sin inventar datos.
- Ajustar ventana editable, validaciones.
- Actualizar templates/rutas.

**Pros:** Menor número de tablas. **Contras:** **Alto riesgo de ruptura histórica**. Imposible reconstruir "día exacto" desde solo `semana` (lunes). Cambiar PK/constraint es disruptivo. Muchos consumidores fuertemente acoplados al concepto "semana/lunes". Difícil mantener retrocompatibilidad con vistas "semanales".

### Opción B: Introducir entidad complementaria diaria + conservar `ParteSemanal` histórico
**Cambios necesarios (INFERIDO):**
- Crear nuevo modelo `ParteDiario` (o `ReporteDiario`) con `atleta_id`, `fecha` (date), campos relevantes (posiblemente subset), unicidad `(atleta_id, fecha)`. 
- Mantener `partes_semanales` intacta para histórico - sin migración destructiva de datos existentes.
- Nuevas rutas `/parte/diario` o extender `/parte` con selector fecha/diario/semanal. 
- Nuevos servicios para agregación diaria/semanal (agregar partes diarios a semana si se desea mantener vistas semanales). 
- Actualizar validaciones/autorización.
- Decidir qué campos van a diario vs semanal (el formulario actual es bastante completo para diario? Podría ser muy largo).

**Pros:** **Preserva histórico intacto**. Menor riesgo. Permite coexistencia (transición gradual). Fácil rollback. **Contras:** Dos modelos que pueden solaparse conceptualmente. Necesita lógica para agregar datos si se quiere mantener estadísticas semanales. Posible duplicación si mal diseñado.

**Recomendación (basada en evidencia):** **Opción B (entidad complementaria)** es **mucho menos disruptiva**. Razones:
1. **Preservación histórica garantizada** - no toca `partes_semanales` existente, unicidad, ni datos. Crítico dado que otros módulos (cruce con marcas históricas, series largas) dependen de ellos.
2. **Acoplamiento fuerte al "lunes/semana"** demostrado en `bienestar.py`, `alertas.py`, `atletas.py`, `graficos` - cambiar todo esto es alto riesgo/error-prone.
3. **Migración de datos** en Opción A es inviable sin información de fechas diarias (solo existe `semana=lunes`).
4. **Coexistencia** permite mantener reportes semanales para análisis históricos y añadir diarios para seguimiento más granular sin romper producción.

Si el producto **requiere reemplazar completamente** el flujo semanal por diario, Opción A podría considerarse, pero con evidencia disponible **B es claramente preferible**.

## 7. DATOS HISTÓRICOS - PRESERVACIÓN, MIGRACIÓN, RIESGOS

**Estado actual (VERIFICADO):**
- Datos en `partes_semanales` con clave `(atleta_id, semana)`. Sin columna `fecha` diaria.
- Migraciones existentes no alteran estructura histórica destructivamente (solo `fatiga` nullable).
- Historial usado por `cruce_con_marcas` (toma todo historial de marcas para mejores RP), `series_*`, `serie_grupo`.

**Estrategia de preservación (RECOMENDADA):**
- **NO tocar tabla `partes_semanales`**. Mantenerla como fuente histórica "reporte semanal".
- Si se introduce diario, crear tabla nueva `partes_diarias` (o similar) sin FK/relaciones que fuerce migración de datos.
- Para vistas semanales históricas: seguir usando `partes_semanales`. Para vistas con datos nuevos diarios: agregar lógica de agregación (ej. promedio/suma por semana de registros diarios) - **pero esto cambia semántica**.
- **Nunca** intentar inferir fechas diarias desde `semana` (lunes) - sería inventar datos, lo cual va en contra de la filosofía del proyecto ("datos inventados son peores que datos faltantes" según comentario en `parte.py:18-19`).

**Implicaciones de migración (INFERIDO):**
- Opción B: **mínima** - solo `CREATE TABLE`, índices, posiblemente constraints. Sin `ALTER` destructivo en tabla existente. Riesgo bajo.
- Opción A: **alta** - requiere cambiar constraint única, posiblemente añadir columna fecha, migrar datos (imposible correctamente), actualizar todas las FKs/consultas. Alto riesgo de corrupción/loss de compatibilidad.

**Riesgos (INFERIDO):**
- **Romper agregados históricos** si lógica de agregación cambia.
- **Duplicidad/confusión** si atletas pueden cargar ambos semanal y diario para misma semana.
- **Rendimiento** si agregaciones no optimizadas.
- **Autorización** debe mantenerse (solo atleta crea su propio reporte).
- **Zona horaria**: ya se maneja con `America/La_Paz` en `tiempo.py` - crítico para determinar "día" correcto.

## 8. DECISIONES PENDIENTES (requieren input Product Owner)

**NO DECIDIR - listar preguntas (VERIFICADO necesidad):**
1. **Alcance**: ¿Reemplazar completamente reporte semanal por diario, o agregar diario como opción complementaria?
2. **Campos diarios**: ¿Mismos 4 ítems obligatorios + RPE/molestias? ¿Formulario más corto para diario? ¿Qué campos son obligatorios diario vs semanal?
3. **Granularidad/obligatoriedad**: ¿Un reporte por día? ¿Todos los días o solo días de entrenamiento? ¿Qué pasa si no entrena?
4. **Edición**: ¿Permitir editar reportes diarios pasados? ¿Ventana igual (1 día/semana)? ¿Diferente?
5. **Histórico y visualización**: ¿Deben las pantallas de profesor/panel mostrar vista diaria, semanal agregada, o ambas? ¿Cómo se agregan datos diarios para mantener semáforos/históricos consistentes?
6. **Cruce con marcas**: Si hay parte diario, ¿cómo cruzar con marcas? ¿Usar parte del día/misma semana/promedio?
7. **Alertas**: ¿Cambiar "sin_parte" por "sin_parte_hoy"/"sin_reporte_últimos_N_días"?
8. **Coexistencia**: Si ambos existen, ¿puede atleta tener semanal y diario misma semana? ¿Cuál prevalece?
9. **Migración UX**: ¿Mostrar ambos flujos? ¿Migrar atletas gradualmente?
10. **Unicidad**: ¿Un reporte por (atleta, fecha) exactamente? ¿Manejar zonas horarias/fechas límite?

## 9. OUTLINE DE IMPLEMENTACIÓN MÍNIMA (solo planificación, SIN IMPLEMENTAR)

### Si se elige Opción B (recomendada)

**Schema (INFERIDO):**
- Nueva tabla `partes_diarias` con: `id`, `atleta_id` (FK users), `fecha` (Date, NOT NULL), campos similares a semanales pero adaptados, `enviado`, `actualizado`. 
- `UniqueConstraint("atleta_id", "fecha", name="uq_parte_diario_atleta_fecha")`. Índices en `atleta_id, fecha`.
- **Sin modificar** `partes_semanales`.

**Backend (INFERIDO):**
- Nuevo modelo `app/models/parte_diario.py` (o añadir a `parte.py`).
- Nuevas rutas en `app/routers/parte.py` o nuevo router `parte_diario.py` (ej. `/parte/diario`, `/parte/diario?fecha=...`).
- Nuevos helpers: validación por fecha, determinar "hoy" con `tiempo.hoy()`, ventana editable configurable.
- Servicios: agregar funciones para leer/agregar por día, y posiblemente `agregar_diarios_a_semana()` para mantener compatibilidad con `bienestar.*` existentes.
- Actualizar `alertas.py` para considerar reportes diarios si aplica.

**Frontend (INFERIDO):**
- Nuevo template o extender `atleta/parte.html` con selector diario/semanal/fecha.
- Navegación para acceder a diario.

**Migración Alembic (INFERIDO):**
- Nueva migración solo `CREATE TABLE partes_diarias` + índices/constraints. Downgrade `DROP TABLE`.

**Riesgos mitigados:** Histórico intacto, rollback simple.

### Si se elige Opción A (NO recomendado con evidencia actual)

Requeriría: cambiar constraint, migración de datos (imposible sin inventar fechas), refactor masivo de servicios/consultas/agregados, alto riesgo. **No se detalla en profundidad por ser poco viable**.

### Tests futuros propuestos (INFERIDO)

**Diarios - creación/edición:**
- Crear reporte diario para fecha específica
- Editar reporte diario existente (mismo atleta/fecha) actualiza, no duplica
- Unicidad `(atleta_id, fecha)` enforced
- Ventana editable para diarios

**Autorización/aislamiento:**
- Solo atleta puede crear/editar sus propios reportes diarios
- Profesor no puede crear como atleta
- Atleta no puede escribir reporte de otro atleta

**Fechas/zonas horarias:**
- Usar `hoy()` zona Bolivia correctamente
- Fechas futuras manejadas según regla definida
- Fechas muy pasadas bloqueadas según ventana

**Validación/campos opcionales:**
- Mismos casos que semanal (molestias condicionales, RPE condicional, valores imposibles → None)
- Campos obligatorios según definición PO

**Preservación histórico:**
- Reportes semanales existentes siguen accesibles sin cambios
- Consultas históricas semanales retornan mismos resultados
- Cruce marcas con histórico semanal sigue funcionando

**Consumidores/estadísticas:**
- Alertas funcionan con diario (o nuevo comportamiento definido)
- Agregados semanales desde diarios correctos si aplica
- Paneles no rompen con coexistencia

## 10. LIMITACIONES

**VERIFICADO/INFERIDO:**
- **Sin acceso a BD producción**: No se puede inspeccionar esquema real en producción vs local. Solo se revisaron migraciones y modelos locales.
- **Sin acceso a despliegue autenticado**: `https://atletismo.onrender.com/parte?semana=2026-10-12` puede requerir auth - no se accedió, se basa en código local.
- **Datos históricos de fechas diarias**: **NO EXISTEN**. Solo `semana` (lunes). Imposible mapear semanal→diario sin inventar.
- **"Producto" decisiones faltantes**: Muchos aspectos requieren PO (campos, coexistencia, agregación) - no se asumieron.
- **Tests no ejecutados**: Se revisaron tests existentes sin correrlos (cumple restricción read-only).
- **Sin ver configuración completa**: Revisados archivos clave; podría haber lógica en otros lugares no detectada en grep limitado.
- **Alcance formulario**: Muy extenso para uso diario móvil - podría necesitar simplificación (decisión PO).

## 11. LOG DE VERIFICACIÓN

**Archivos inspeccionados (VERIFICADO):**
- `app/routers/parte.py` (completo)
- `app/models/parte.py` (completo)  
- `app/services/bienestar.py` (completo)
- `app/services/alertas.py` (parcial vía grep)
- `app/templates/atleta/parte.html` (completo)
- `app/tiempo.py` (completo)
- `alembic/versions/d61e48816ec5_esquema_inicial_usuarios_partes_.py` (completo)
- `alembic/versions/a3f1c9e27b04_fatiga_opcional_rpe_reemplaza_energia.py` (completo)
- `tests/test_parte.py` (completo)
- `app/main.py` (referencias), `app/models/__init__.py`, navegación templates

**Comandos read-only usados (VERIFICADO):**
- `functions.read` múltiples archivos
- `functions.grep` con patrones `parte|parte_atleta|reporte|seman.*parte`

**Git/estado (VERIFICADO):**
- Repositorio en `C:\Archivos.Diego\atletismoWeb\atletismo` confirmado como git repo (presente `.git/`). 
- No se ejecutaron comandos git mutantes. Se intentó revisar branch/status pero herramientas con restricciones de permisos bloquearon algunos comandos git específicos - sin embargo se confirmó estructura git.

**Tests:** Revisados `tests/test_parte.py` completamente. **NO ejecutados** (no se corrieron pytest). No se afirma éxito.

**Cambios realizados:** **NINGUNO**. Solo lectura/inspección. Sin modificaciones a archivos, BD, estado app, o git.

**Etiquetado:** Se usaron `VERIFICADO`, `INFERIDO`, `RECOMENDADO` según evidencia disponible.

---

## User

# TASK: Replace Weekly Athlete Reports with a Daily Tracking System

## KILO CONFIGURATION

- Mode: Plan
- Session: EXISTING if session `ses_e8fd` is available and contains the previous audit context; otherwise NEW.
- Repository: `atletismoWeb/atletismo`
- Expected branch: `Baruc+Kilo`

## OBJECTIVE

Prepare a complete, technically grounded implementation plan to replace the existing weekly athlete reporting system with a daily tracking system.

The new system must support:

1. One daily wellness record per athlete and local date.
2. Multiple training sessions associated with that daily record.
3. Daily training-load calculations.
4. Updated statistics, charts, alerts, athlete dashboards and related services.
5. Complete removal of functional dependencies on the old weekly reporting model.

This is a cross-cutting architectural change. Do not implement anything during this task.

## 1. INITIAL INSPECTION

Before investigating:

1. Verify the repository root, current branch, HEAD and Git working-tree status.
2. Preserve all existing local changes.
3. Check whether the previous Kilo session `ses_e8fd` is available.
4. If available, inspect `.kilo/kiloSesions/S-0006_ask_session-ses_e8fd.md` and reuse its findings.
5. Identify which previous findings remain valid against the current repository.
6. If the session is unavailable, use the specified audit report if it exists locally; otherwise perform the necessary investigation independently.

Do not assume that previous reports accurately represent the current repository.

## 2. TARGET DATA MODEL

Design a daily tracking model using SQLAlchemy 2 and PostgreSQL.

### Daily record

One record per athlete and local date, protected by a database-level unique constraint.

The server determines the date using `America/La_Paz`.

Wellness fields:

- `sueno_calidad`: integer, 1–10.
- `horas_sueno`: decimal, 0–24.
- `fatiga`: integer, 1–10.
- `dolor_muscular`: integer, 1–10.
- `estres`: integer, 1–10.
- `animo`: integer, 1–10.
- `hay_molestia`: boolean.
- `molestia_zona`: multiple selectable body regions.
- `molestia_dolor`: integer, 1–10.
- `afecta_entrenamiento`: integer, 0–3.
- `sintomas_enfermedad`: boolean.
- `detalle_sintomas`: optional text.
- `comentarios`: optional text.
- `entreno_hoy`: boolean.

Body regions:

Cuello, hombros, espalda, cadera, glúteos, muslos, rodillas, pantorrillas, tobillos, pies, brazos and other.

### Training sessions

One daily record can contain multiple sessions.

Each session must include:

- `tipo_entrenamiento`: speed/sprint, endurance, strength, technique and coordination, mobility and recovery, competition, mixed training or other.
- `duracion_min`: positive integer.
- `rpe`: integer, 1–10.
- `carga_sesion`: duration multiplied by RPE, calculated authoritatively by the backend.
- `comentarios_entrenamiento`: optional text.

The daily training load is the sum of individual session loads.

Example:

- Session 1: 60 × 8 = 480 AU.
- Session 2: 45 × 6 = 270 AU.
- Daily load: 750 AU.

Fatigue and session RPE must remain independent variables.

## 3. BUSINESS RULES

Evaluate how to implement and enforce these rules across frontend, backend and database:

- Only one daily record per athlete and date.
- Athletes can create or update their current day's record.
- Athletes cannot choose another date to create or modify records.
- Updating today's record must not create duplicates.
- `entreno_hoy = false` means no training sessions should be displayed or persisted.
- `entreno_hoy = true` allows multiple sessions.
- Changing from Yes to No when sessions already exist requires explicit confirmation before discarding them.
- Never delete existing sessions silently.
- If confirmation is cancelled, preserve the existing sessions.
- Conditional wellness fields must be consistently validated and cleaned or ignored when their parent condition is false.
- Backend validation must remain authoritative regardless of browser-side validation.
- Daily record and session changes must be transactional.
- Concurrent submissions must not violate record uniqueness.

Investigate how to implement the confirmation requirement securely. Do not rely exclusively on hiding fields or JavaScript confirmation dialogs.

## 4. FRONTEND REQUIREMENTS

Plan a responsive redesign for desktop and mobile.

The form must contain five distinct wellness categories:

A. Rest and sleep.
B. Fatigue and physical recovery.
C. Psychological well-being.
D. Physical condition and discomfort.
E. General health and observations.

Plan:

- Visual 1–10 scales with descriptive labels and guidance.
- Conditional fields for discomfort and illness symptoms.
- `entreno_hoy` question after wellness.
- Completely hidden training section when the answer is No.
- Dynamic session list when the answer is Yes.
- Add, edit and remove individual sessions.
- Individual and total daily training-load previews.
- Preserve submitted values after validation errors.
- Update existing daily records without duplication.

Reuse existing project components and visual conventions.

Do not introduce unnecessary frontend dependencies.

## 5. DATABASE AND MIGRATION STRATEGY

Investigate the existing database conventions and recommend:

1. Daily record table structure.
2. Training session table structure.
3. Relationships, foreign keys and cascade behavior.
4. Appropriate PostgreSQL types and database constraints.
5. Representation of multiple body regions.
6. Whether session and daily training loads should be persisted or derived.
7. Required indexes and uniqueness constraints.

Compare viable alternatives when a decision has meaningful architectural consequences.

### Migration requirements

The migration strategy must:

- Create the new structures.
- Replace dependencies on the weekly model.
- Remove the old weekly table only after all functional references have been replaced.
- Never fabricate daily records from historical weekly data.
- Preserve unrelated data, including users, athletes, brands, payments and other modules.
- Never execute production database migrations or destructive operations.
- Include a strategy for validating migrations against a disposable test database.

Explicitly identify which historical weekly data will become unavailable after removal and the consequences of that decision.

## 6. COMPLETE DEPENDENCY AUDIT

Search the entire repository for references to the existing weekly model, fields and reporting workflows.

Inspect, where applicable:

- SQLAlchemy models and relationships.
- Alembic migration history.
- Pydantic schemas and validation.
- Routes and controllers.
- Services and business logic.
- HTML/Jinja templates.
- JavaScript and frontend components.
- Athlete and club statistics.
- Training-load calculations.
- Individual athlete performance series.
- Charts and visualizations.
- Alerts and thresholds.
- Athlete profiles and dashboards.
- Pending-report indicators.
- Navigation and template inheritance.
- Automated tests and fixtures.
- Documentation and configuration.

Identify indirect dependencies, not just direct imports.

For each dependency, explain:
- Current behavior.
- Why it depends on weekly data.
- Required change.
- Other components affected.
- Implementation order and risk.

### Statistics and alerts

Statistics must operate on daily records.

Weekly summaries, when needed, must be derived from existing daily records rather than maintaining another weekly reporting model.

Review alert thresholds independently.

Do not automatically transfer weekly thresholds to daily measurements without evaluating their temporal meaning.

Treat wellness and training-load indicators as monitoring tools, not medical diagnoses or definitive injury predictions.

## 7. SECURITY AND DATA INTEGRITY

Verify how the existing application implements:

- Authentication and role-based authorization.
- Athlete ownership restrictions.
- CSRF protection.
- Server-side date determination.
- Conditional field validation.
- Concurrent record creation.
- Transaction boundaries.
- Session deletion confirmation.

Identify any existing mechanisms that should be reused.

Athletes must never access or modify another athlete's records.

## 8. TESTING STRATEGY

Prepare a test plan covering:

1. Create a daily record.
2. Update without duplication.
3. Enforce one record per athlete and date.
4. Correct `America/La_Paz` date determination.
5. Save wellness without training sessions.
6. Save one training session.
7. Save multiple training sessions.
8. Calculate individual and daily training loads.
9. Reject invalid RPE and duration.
10. Validate conditional fields.
11. Preserve sessions when discarding confirmation is cancelled.
12. Delete sessions only after valid explicit confirmation.
13. Prevent cross-athlete modifications.
14. Verify daily statistics and alerts.
15. Test migrations using a disposable PostgreSQL database.
16. Execute the complete regression suite.

Identify existing tests that must be modified, removed or replaced.

## 9. IMPLEMENTATION PLAN DELIVERABLE

Produce an implementation plan organized into logical phases.

For each phase include:

- Objective.
- Exact repository-relative files involved.
- Current responsibility of each file.
- Expected modification.
- Dependencies and prerequisites.
- Potential regressions.
- Validation criteria.

Use actual discovered paths and identifiers. Never invent filenames, classes, functions or APIs.

Prioritize dependency order and avoid unnecessary refactoring.

Explicitly distinguish:

- Decisions already established by the requirements.
- Technical decisions recommended by the investigation.
- Decisions that still require approval.

Include a dependency map showing how models, migrations, services, routes, templates, statistics and tests relate to one another.

Identify the safest migration and deployment sequence without executing it.

## 10. STRICT CONSTRAINTS

- READ ONLY.
- Do not modify source code.
- Do not create or edit migration files.
- Do not modify dependencies.
- Do not alter database contents.
- Do not execute migrations.
- Do not delete or overwrite files.
- Do not commit, push, merge or deploy.
- Do not discard existing Git changes.
- Do not modify production data.
- Do not start implementation without explicit approval.

If the working tree contains changes, identify them and account for their potential impact.

## 11. FINAL REPORT

Deliver:

1. Verified repository state.
2. Previous audit findings reused or superseded.
3. Current weekly architecture.
4. Complete dependency inventory.
5. Proposed daily data architecture.
6. Migration and historical-data removal strategy.
7. Frontend and backend implementation plan.
8. Statistics and alerts adaptation plan.
9. Security and integrity considerations.
10. Testing and acceptance criteria.
11. Risks, unresolved decisions and assumptions.
12. Recommended implementation order.

Use PASS, FAIL, BLOCKED or NOT RUN for applicable verification results.

Conclude with a clear recommendation on whether the proposed implementation is ready for approval.

Do not implement anything. Wait for explicit authorization before switching to Code mode.

---

## Assistant

**Tool: bash**

**Tool: bash**

**Tool: bash**

**Tool: read**

**Tool: grep**

---

## Assistant

**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

---

## Assistant

**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

---

## Assistant

**Tool: bash**

**Tool: bash**

**Tool: read**

**Tool: read**

**Tool: read**

---

## Assistant

**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

---

## Assistant

**Tool: bash**

**Tool: bash**

**Tool: bash**

---

## Assistant

**Tool: write**

---

## Assistant

**Tool: open_plan**

**Tool: plan_exit**

---

## User

# TASK: Finalize and Correct the Daily Tracking Implementation Plan

## KILO CONFIGURATION

- Mode: Plan
- New Kilo Session: NO
- Existing session: ses_e8fd
- Repository: atletismoWeb/atletismo
- Branch: Baruc+Kilo

## OBJECTIVE

Review and update the existing implementation plan:

`.kilo/plans/1792882624161-daily-tracking-replacement.md`

The previous audit and planning investigation are already available in the current session.

Preserve the existing technical investigation, dependency inventory, verified file paths, architecture and implementation phases.

Do not repeat the complete audit or redesign the system from scratch.

The objective is to resolve remaining inconsistencies and produce a sufficiently precise plan for implementation approval.

## 1. INITIAL VERIFICATION

1. Verify the repository root, branch, HEAD and Git status.
2. Confirm that session `ses_e8fd` and its previous investigation remain available.
3. Read the existing plan before editing it.
4. Preserve all existing user changes.
5. Do not assume the previous Git state is still current.

## 2. RESOLVE THE FOLLOWING ISSUES

### A. Session deletion confirmation

Correct the contradictory rules concerning `entreno_hoy=false`.

Required behavior:

- Existing persisted sessions must never be deleted silently.
- Changing Yes to No must require explicit confirmation.
- Cancelling confirmation must preserve all existing sessions.
- Backend enforcement must be authoritative.
- Do not rely on a freely editable boolean hidden field as the sole confirmation mechanism.

Design a secure two-step confirmation flow tied to the daily record and the sessions being discarded.

Explain how to prevent stale confirmations from deleting sessions that changed after the confirmation was initiated.

All record and session changes must remain transactional.

### B. Training declared without sessions

Recommend and specify one consistent rule for:

`entreno_hoy=true` with zero sessions.

Preferred behavior: require at least one valid session.

Ensure that frontend and backend validation agree.

### C. Statistics and training load

Specify the calculation contracts:

- Individual session load = duration × RPE.
- Daily load = sum of session loads.
- Weekly load = sum of daily loads.
- Fatigue and session RPE remain independent.
- Missing daily reports must not be interpreted as zero training load.

Review the existing ACWR implementation and determine which windows and aggregation semantics must change.

Do not invent formulas or claim physiological validity without evidence.

### D. Wellness aggregation

Define how daily 1–10 wellness measurements contribute to weekly summaries.

Distinguish:
- Daily values.
- Weekly averages.
- Missing observations.
- Counts of reported days.

Preserve the distinction between missing information and a genuinely low or zero value.

### E. Alerts

Propose concrete daily alert semantics.

Distinguish:
- Missing wellness report.
- No training today.
- High or unusual daily load.
- Low wellness indicators.
- Reported discomfort or illness symptoms.

Reassess existing weekly thresholds rather than mechanically transferring them.

Provide recommended initial rules and identify any thresholds that require product-owner approval.

### F. Other body region

Specify conditional behavior for the `otro` body region.

Recommended approach:

- Add an optional text field `molestia_zona_otra`.
- Require it when `otro` is selected.
- Ignore or clear it when `otro` is not selected.
- Validate it on the backend.

### G. Historical weekly data

The original requirements already establish:

- Weekly records will not be converted into daily records.
- The weekly model will be completely replaced.
- The old table and its data will be removed after all functional references have been replaced.
- Unrelated data must remain intact.

Remove this as an unresolved product decision.

Keep the destructive migration explicitly controlled and require a verified backup before any production execution.

Do not execute the migration.

## 3. REVIEW TECHNICAL CONSISTENCY

Check the complete existing plan for contradictions involving:

- Database cascade behavior.
- Session replacement and deletion.
- Concurrent submissions.
- Conditional wellness fields.
- Server-side date authority.
- Athlete ownership.
- Transaction boundaries.
- Session load persistence.
- Daily and weekly aggregation.
- Alert thresholds.
- Migration ordering.
- Removal of weekly dependencies.

Correct any inconsistencies discovered.

Preserve SQLAlchemy 2, PostgreSQL, Alembic and existing project conventions.

## 4. IMPLEMENTATION PHASES

Retain the existing phases but refine their dependencies and acceptance criteria.

In particular:

- Do not drop `partes_semanales` before all functional references are removed.
- Do not modify historical Alembic migrations.
- Keep schema creation and weekly-table removal in separate forward migrations.
- Validate migrations on a disposable PostgreSQL database.
- Keep unrelated modules and data intact.
- Ensure all weekly consumers have been adapted before the final migration.

## 5. STRICT CONSTRAINTS

- Plan mode only.
- No source-code modifications.
- No database modifications.
- No migration execution.
- No dependency changes.
- No tests that modify persistent data.
- No commits, pushes, merges or deployments.
- Preserve the existing investigation and plan structure.
- Do not create a second competing implementation plan.

You are authorized to update only the existing planning document.

## 6. FINAL REPORT

Update:

`.kilo/plans/1792882624161-daily-tracking-replacement.md`

Then report:

1. Changes made to the plan.
2. Technical decisions resolved.
3. Remaining decisions requiring user approval.
4. Updated implementation phases and dependencies.
5. Migration safety conditions.
6. Risks that remain.
7. Whether the plan is ready for Code mode.

Do not implement the application.

Wait for explicit authorization before switching to Code mode.

---

## Assistant

**Tool: bash**

**Tool: bash**

**Tool: bash**

**Tool: read**

---

## Assistant

**Tool: read**

**Tool: read**

**Tool: read**

**Tool: bash**

**Tool: read**

---

## Assistant

**Tool: edit**

---

## Assistant

**Tool: edit**

---

## Assistant

**Tool: edit**

---

## Assistant

**Tool: open_plan**

**Tool: plan_exit**

---

