"""Phase 3 router integration for daily tracking (Phase 3 only).

Replaces the weekly /parte workflow with the approved daily, today-only
workflow over the existing Phase 2 domain services. Policy A and the signed
discard-confirmation protocol are preserved exactly; the router is a thin
HTTP/controller layer and does not duplicate domain validation, locking or
concurrency handling.
"""
from datetime import date, timedelta
import re

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..config import get_settings
from ..auth import get_current_user
from ..database import get_db
from ..services import bienestar, parte_diaria as pd
from ..templates_config import templates
from ..tiempo import hoy, lunes_actual, lunes_de

router = APIRouter(prefix="/parte", tags=["parte"])


# Ítems de bienestar diario (escala 1-10). Reemplazan, solo para esta plantilla,
# los ítems semanales 1-5 de services/bienestar.py (que se conservan intactos para
# los consumidores semanales). Cada ítem trae su campo, su etiqueta y su pregunta.
DAILY_ITEMS = [
    ("sueno_calidad",  "Calidad del sueño",  "¿Cómo dormiste la noche pasada?"),
    ("fatiga",         "Fatiga",             "¿Qué tan cansado/a te sentís hoy?"),
    ("dolor_muscular", "Dolor muscular",     "¿Cómo están tus músculos?"),
    ("estres",         "Estrés",             "¿Qué tan estresado/a te sentís?"),
    ("animo",          "Ánimo",              "¿Cómo estuvo tu ánimo hoy?"),
]

# Descriptores por número (1-10) para cada escala de bienestar diario. Sirven de
# guía en el formulario; la validación de rango sigue siendo del servicio (1-10).
DAILY_DESCRIPTORES = {
    "sueno_calidad": {
        1: "Muy mala", 2: "Muy mala", 3: "Muy mala",
        4: "Regular", 5: "Regular", 6: "Regular",
        7: "Buena", 8: "Buena", 9: "Muy buena", 10: "Excelente",
    },
    "fatiga": {
        1: "Ninguna", 2: "Ninguna", 3: "Baja",
        4: "Moderada", 5: "Moderada", 6: "Moderada",
        7: "Elevada", 8: "Elevada", 9: "Extrema", 10: "Extrema",
    },
    "dolor_muscular": {
        1: "Ninguno", 2: "Ninguno", 3: "Leve",
        4: "Moderado", 5: "Moderado", 6: "Moderado",
        7: "Fuerte", 8: "Fuerte", 9: "Muy fuerte", 10: "Extremo",
    },
    "estres": {
        1: "Ninguno", 2: "Ninguno", 3: "Leve",
        4: "Moderado", 5: "Moderado", 6: "Moderado",
        7: "Elevado", 8: "Elevado", 9: "Muy elevado", 10: "Extremo",
    },
    "animo": {
        1: "Muy bajo", 2: "Muy bajo", 3: "Bajo",
        4: "Bajo", 5: "Regular", 6: "Regular",
        7: "Bueno", 8: "Bueno", 9: "Excelente", 10: "Excelente",
    },
}


# Descriptores de la tabla McLean (página 175 del PDF facilitado).
MCLEAN_ITEMS = [
    ("mclean_fatiga", "Fatiga", {1: "Muy cansado", 2: "Más cansado de lo normal", 3: "Normal", 4: "Recuperado", 5: "Muy recuperado"}),
    ("mclean_sueno", "Calidad del sueño", {1: "Insomnio", 2: "Sueño inquieto", 3: "Dificultad para conciliar el sueño", 4: "Bueno", 5: "Muy reparador"}),
    ("mclean_dolor_muscular", "Dolor muscular", {1: "Mucho dolor", 2: "Dolor y rigidez muscular", 3: "Normal", 4: "Bien", 5: "En perfecto estado"}),
    ("mclean_estres", "Estrés", {1: "Altamente estresado", 2: "Estresado", 3: "Normal", 4: "Relajado", 5: "Muy relajado"}),
    ("mclean_animo", "Humor", {1: "Muy enfadado, irritado. Desanimado", 2: "Enfadado o irritado", 3: "Menos interés en otros y/o en otras actividades de lo normal", 4: "Bien en general", 5: "Muy positivo"}),
]
MCLEAN_TYPES = (("aerobico", "Aeróbico"), ("lactico", "Láctico"), ("velocidad", "Velocidad"), ("fuerza", "Fuerza"))


def _athlete_required(user) -> None:
    if user.role != "atleta":
        raise HTTPException(status_code=403,
                            detail="El parte diario lo carga cada atleta.")


def _parse_zonas(value: str):
    if not value:
        return []
    return [z.strip() for z in value.split(",") if z.strip()]


def _parse_bool(value: str) -> bool:
    """binario() emits si/no; service accepts si/no as well."""
    return (value or "").strip().lower() == "si"


class FormParseError(ValueError):
    """Controlled input parsing error; never passed to the service layer."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _mmss_seconds(raw: str, *, name: str) -> int:
    match = re.fullmatch(r"(\d{2,3}):(\d{2})", (raw or "").strip())
    if not match or int(match.group(2)) > 59:
        raise FormParseError(f"{name}: ingresá minutos y segundos como MM:SS (ejemplo 01:30).")
    return int(match.group(1)) * 60 + int(match.group(2))


def _parse_positive_int(raw: str, *, name: str) -> int:
    text = (raw or "").strip()
    if not text:
        raise FormParseError(f"{name} inválido.")
    try:
        value = int(text)
    except ValueError as exc:
        raise FormParseError(f"{name} inválido.") from exc
    if value < 1:
        raise FormParseError(f"{name} debe ser un entero positivo.")
    return value


def _parse_session_item(text: str, *, index: int) -> dict:
    """Parse one session line: id|orden|tipo|duracion|rpe|comentarios.

    Missing optional values keep their defaults; malformed submitted values are
    rejected explicitly so they cannot become new sessions or silently change
    values. Parsing errors must be handled before calling the Phase 2 service.
    """
    parts = text.split("|")
    label = f"Sesión {index}"
    item = {"orden": 1, "tipo_entrenamiento": "resistencia",
            "duracion_min": 45, "rpe": 6, "comentarios_entrenamiento": None}
    if len(parts) >= 1 and parts[0].strip():
        item["id"] = _parse_positive_int(parts[0], name=f"{label}: id")
    else:
        item["id"] = None
    if len(parts) >= 2 and parts[1].strip():
        item["orden"] = _parse_positive_int(parts[1], name=f"{label}: orden")
    if len(parts) >= 3 and parts[2].strip():
        item["tipo_entrenamiento"] = parts[2].strip()
    if len(parts) >= 4 and parts[3].strip():
        item["duracion_min"] = _parse_positive_int(parts[3], name=f"{label}: duración")
    if len(parts) >= 5 and parts[4].strip():
        item["rpe"] = _parse_positive_int(parts[4], name=f"{label}: RPE")
    if len(parts) >= 6:
        item["comentarios_entrenamiento"] = parts[5].strip() or None
    return item


def _serialize_sessions(sessions) -> str:
    """Serialize existing sessions into the pipe-delimited form."""
    lines = []
    for s in sessions or []:
        lines.append(
            f"{s.id}|{s.orden}|{s.tipo_entrenamiento}|{s.duracion_min}"
            f"|{s.rpe}|{s.comentarios_entrenamiento or ''}"
        )
    return "\n".join(lines)


def _serialize_delete_ids(sessions) -> str:
    return ",".join(str(s.id) for s in sessions or [] if s.id is not None)


def _session_payload(form) -> tuple:
    """Build the service payload from the submitted form.

    Returns (payload, delete_ids, allow_replace, errors). Malformed submitted
    values are rejected explicitly and never passed partially to the Phase 2
    service.
    """
    errors = []
    # Handle both newline-separated textarea and repeated form fields
    sessions_raw = []
    if hasattr(form, "getlist"):
        sessions_list = form.getlist("sessions")
    else:
        sessions_list = [form.get("sessions", "")]

    for item in sessions_list:
        item = item.strip()
        if not item:
            continue
        # Split by newlines for textarea content
        for line in item.split("\n"):
            line = line.strip()
            if line:
                sessions_raw.append(line)

    raw = []
    for idx, item in enumerate(sessions_raw, start=1):
        try:
            raw.append(_parse_session_item(item, index=idx))
        except FormParseError as exc:
            errors.append(exc.message)

    # Handle comma-separated delete_session_ids
    explicit_raw = []
    if hasattr(form, "getlist"):
        explicit_list = form.getlist("delete_session_ids")
    else:
        explicit_list = [form.get("delete_session_ids", "")]

    for item in explicit_list:
        item = item.strip()
        if not item:
            continue
        # Split by commas for comma-separated values
        for part in item.split(","):
            part = part.strip()
            if part:
                explicit_raw.append(part)

    delete_ids = []
    seen_delete = set()
    for item in explicit_raw:
        try:
            value = _parse_positive_int(item, name="ID de sesión a eliminar")
        except FormParseError as exc:
            errors.append(exc.message)
            continue
        if value in seen_delete:
            errors.append(f"ID de sesión a eliminar duplicado: {value}.")
            continue
        seen_delete.add(value)
        delete_ids.append(value)

    allow_replace = form.get("allow_full_session_replacement") == "1"
    payload = {
        "sueno_calidad": form.get("sueno_calidad", ""),
        "horas_sueno": form.get("horas_sueno", ""),
        "fatiga": form.get("fatiga", ""),
        "dolor_muscular": form.get("dolor_muscular", ""),
        "estres": form.get("estres", ""),
        "animo": form.get("animo", ""),
        "hay_molestia": _parse_bool(form.get("hay_molestia")),
        "molestia_zona": _parse_zonas(form.get("molestia_zona", "")),
        "molestia_zona_otra": form.get("molestia_zona_otra", ""),
        "molestia_dolor": form.get("molestia_dolor", ""),
        "afecta_entrenamiento": form.get("afecta_entrenamiento", ""),
        "sintomas_enfermedad": _parse_bool(form.get("sintomas_enfermedad")),
        "detalle_sintomas": form.get("detalle_sintomas", ""),
        "comentarios": form.get("comentarios", ""),
        "entreno_hoy": _parse_bool(form.get("entreno_hoy")),
        "sessions": raw,
    }
    if payload["entreno_hoy"]:
        principal = {"estructura_tipo": form.get("estructura_tipo", "")}
        for field in ("series", "repeticiones_por_serie", "distancia_m"):
            try:
                principal[field] = _parse_positive_int(form.get(field, ""), name=field)
            except FormParseError as exc:
                errors.append(exc.message)
        for field in ("descanso_micro_min", "descanso_micro_max", "descanso_macro_min",
                      "descanso_macro_max", "tiempo_rep_min", "tiempo_rep_max"):
            try:
                principal[field] = _mmss_seconds(form.get(field, ""), name=field)
            except FormParseError as exc:
                errors.append(exc.message)
        for low, high in (("descanso_micro_min", "descanso_micro_max"),
                          ("descanso_macro_min", "descanso_macro_max"),
                          ("tiempo_rep_min", "tiempo_rep_max")):
            if low in principal and high in principal and principal[low] > principal[high]:
                errors.append(f"{low}: el mínimo no puede superar el máximo.")
        payload["entrenamiento_principal"] = {
            "estructura_tipo": principal.get("estructura_tipo"),
            "series": principal.get("series"),
            "repeticiones_por_serie": principal.get("repeticiones_por_serie"),
            "distancia_m": principal.get("distancia_m"),
            **{f"{field}_s": value for field, value in principal.items() if field.endswith(("_min", "_max"))},
        }
    else:
        payload["entrenamiento_principal"] = None
    return payload, delete_ids, allow_replace, errors


def _base_context(user, *, parte=None, form=None, errors=None, message=None,
                  conflict=False, stale=False, created=False,
                  edit_state_token=None, discard_token=None):
    """Stable template context for Phase 3/4 transition."""
    return {
        "user": user,
        "fecha": hoy(),
        "parte": parte,
        "form": form,
        "errores": errors or [],
        "message": message,
        "conflict": conflict,
        "stale": stale,
        "created": created,
        "edit_state_token": edit_state_token,
        "discard_token": discard_token,
        "molestia_zonas": pd.MOLESTIA_ZONAS,
        "tipos_entrenamiento": pd.TIPOS_SET,
        "items_diarias": DAILY_ITEMS,
        "descriptores_diarias": DAILY_DESCRIPTORES,
    }


def _render_form(request, user, db, *, parte=None, form=None, errors=None,
                 message=None, conflict=False, stale=False, created=False,
                 edit_state_token=None, discard_token=None, status_code=200):
    # Use submitted form data for sessions/delete_ids on validation/conflict errors
    # to preserve user input; fall back to persisted parte data otherwise.
    # Multi-value retrieval preserves repeated form fields without discarding
    # newline-separated textarea input or changing single-value behavior.
    if form is not None and (status_code in (422, 409) or errors):
        if hasattr(form, "getlist"):
            sessions_items = [str(item) for item in form.getlist("sessions") if str(item).strip()]
            delete_items = [str(item) for item in form.getlist("delete_session_ids") if str(item).strip()]
            sessions_form = "\n".join(sessions_items)
            delete_form = ",".join(delete_items)
        else:
            sessions_form = form.get("sessions", "") or ""
            delete_form = form.get("delete_session_ids", "") or ""
    else:
        sessions_form = ""
        delete_form = ""
        if parte:
            sessions_form = _serialize_sessions(parte.sesiones)
            delete_form = _serialize_delete_ids(parte.sesiones)
    return templates.TemplateResponse(request, "atleta/parte.html", {
        **_base_context(
            user, parte=parte, form=form, errors=errors, message=message,
            conflict=conflict, stale=stale, created=created,
            edit_state_token=edit_state_token, discard_token=discard_token,
        ),
        "rpe_escala": bienestar.RPE_ESCALA,
        "rpe_franjas": bienestar.RPE_FRANJAS,
        "sessions_form": sessions_form,
        "delete_form": delete_form,
    }, status_code=status_code)


def _mclean_rows(form, parte):
    if form is not None:
        fields = [form.getlist(name) for name in ("sesion_id", "sesion_tipo", "sesion_minutos", "sesion_rpe")]
        count = max((len(items) for items in fields), default=0)
        return [dict(zip(("id", "tipo", "minutos", "rpe"),
                         (items[i] if i < len(items) else "" for items in fields)))
                for i in range(count)]
    rows = [{"id": str(s.id), "tipo": s.tipo_entrenamiento, "minutos": str(s.duracion_min), "rpe": str(s.rpe)}
            for s in (parte.sesiones if parte else []) if s.tipo_duracion == "trabajo_principal"]
    return rows + [{"id": "", "tipo": "", "minutos": "", "rpe": ""} for _ in range(3)]


def _render_mclean(request, user, parte, *, form=None, errors=None, message=None,
                   conflict=False, edit_state_token=None, discard_token=None, status_code=200):
    return templates.TemplateResponse(request, "atleta/parte_mclean.html", {
        **_base_context(user, parte=parte, form=form, errors=errors, message=message,
                        conflict=conflict, edit_state_token=edit_state_token, discard_token=discard_token),
        "mclean_items": MCLEAN_ITEMS, "session_types": MCLEAN_TYPES,
        "rows": _mclean_rows(form, parte),
        "historical_sessions": [s for s in (parte.sesiones if parte else []) if s.tipo_duracion == "no_especificada"],
    }, status_code=status_code)


def _parse_mclean_form(form, parte):
    errors = []
    payload = {name: form.get(name, "") for name, _, _ in MCLEAN_ITEMS}
    payload.update({name: form.get(name, "") for name in (
        "horas_sueno", "molestia_zona_otra", "molestia_dolor", "afecta_entrenamiento", "detalle_sintomas", "comentarios")})
    payload.update(version_cuestionario="mclean_1_5", molestia_zona=_parse_zonas(form.get("molestia_zona", "")))
    for name in ("hay_molestia", "sintomas_enfermedad", "entreno_hoy"):
        payload[name] = _parse_bool(form.get(name))
    delete_ids = []
    for raw in form.getlist("delete_session_ids"):
        try:
            value = _parse_positive_int(raw, name="ID de sesión a eliminar")
            if value in delete_ids:
                raise FormParseError("ID de sesión a eliminar duplicado.")
            delete_ids.append(value)
        except FormParseError as exc:
            errors.append(exc.message)
    fields = [form.getlist(name) for name in ("sesion_id", "sesion_tipo", "sesion_minutos", "sesion_rpe")]
    if len({len(items) for items in fields}) != 1 or len(fields[0]) > 100:
        errors.append("Las sesiones enviadas son inválidas.")
        payload["sessions"] = []
        return payload, delete_ids, errors
    sessions = []
    seen = set()
    existing = {s.id: s for s in (parte.sesiones if parte else [])}
    for index, (sid, tipo, minutos, rpe) in enumerate(zip(*fields), 1):
        if not any((sid, tipo, minutos, rpe)):
            continue
        try:
            sid = _parse_positive_int(sid, name="ID de sesión") if sid else None
            if sid and sid in seen:
                raise FormParseError("ID de sesión duplicado.")
            if sid:
                seen.add(sid)
            if sid in delete_ids:
                continue
            if tipo not in dict(MCLEAN_TYPES) and not (sid in existing and existing[sid].tipo_entrenamiento == tipo):
                raise FormParseError(f"Sesión {index}: tipo inválido.")
            sessions.append({"id": sid, "orden": index, "tipo_entrenamiento": tipo,
                "duracion_min": _parse_positive_int(minutos, name=f"Sesión {index}: minutos"),
                "rpe": _parse_positive_int(rpe, name=f"Sesión {index}: RPE"),
                "comentarios_entrenamiento": existing[sid].comentarios_entrenamiento if sid in existing else None})
        except FormParseError as exc:
            errors.append(exc.message)
    payload["sessions"] = sessions if payload["entreno_hoy"] else []
    return payload, delete_ids, errors


@router.get("", response_class=HTMLResponse)
async def formulario(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    _athlete_required(user)

    target_date = hoy()
    parte, edit_token, discard_token = pd.get_today_state(db, user.id, target_date)

    if parte and parte.version_cuestionario == "mclean_1_5" and not get_settings().formulario_mclean_habilitado:
        raise HTTPException(status_code=503, detail="El formulario de este parte no está disponible.")
    if get_settings().formulario_mclean_habilitado and (parte is None or parte.version_cuestionario == "mclean_1_5"):
        return _render_mclean(request, user, parte, edit_state_token=edit_token, discard_token=discard_token)
    return _render_form(request, user, db, parte=parte,
                       edit_state_token=edit_token, discard_token=discard_token)


@router.post("", response_class=HTMLResponse)
async def guardar(
    request: Request,
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    _athlete_required(user)

    target_date = hoy()
    form = await request.form()
    parte, edit_token, discard_token = pd.get_today_state(db, user.id, target_date)
    if parte and parte.version_cuestionario == "mclean_1_5" and not get_settings().formulario_mclean_habilitado:
        raise HTTPException(status_code=503, detail="El formulario de este parte no está disponible.")
    if get_settings().formulario_mclean_habilitado and (parte is None or parte.version_cuestionario == "mclean_1_5"):
        payload, delete_ids, parse_errors = _parse_mclean_form(form, parte)
        if parse_errors:
            return _render_mclean(request, user, parte, form=form, errors=parse_errors,
                                  edit_state_token=form.get("edit_state_token"),
                                  discard_token=form.get("discard_token"), status_code=422)
        result = pd.save_daily_record(db, atleta_id=user.id, payload=payload,
            edit_state_token=form.get("edit_state_token"), discard_token=form.get("discard_token"),
            confirm_discard_sessions=_parse_bool(form.get("confirm_discard_sessions")),
            explicit_delete_session_ids=delete_ids or None, contrato_sesiones="trabajo_principal", fecha=target_date)
        if result.ok:
            return RedirectResponse(url="/parte?ok=1", status_code=302)
        return _render_mclean(request, user, result.parte or parte, form=form, errors=result.errors,
            message=result.message, conflict=result.conflict,
            edit_state_token=result.edit_state_token or form.get("edit_state_token"),
            discard_token=result.discard_token or form.get("discard_token"), status_code=result.status)
    payload, delete_ids, allow_replace, parse_errors = _session_payload(form)
    if parse_errors:
        return _render_form(
            request, user, db,
            parte=parte, form=form, errors=parse_errors,
            message="Hay errores en los datos enviados.",
            edit_state_token=edit_token,
            discard_token=discard_token,
            status_code=422,
        )

    result = pd.save_daily_record(
        db,
        atleta_id=user.id,
        payload=payload,
        edit_state_token=form.get("edit_state_token"),
        discard_token=form.get("discard_token"),
        confirm_discard_sessions=_parse_bool(form.get("confirm_discard_sessions")),
        explicit_delete_session_ids=delete_ids or None,
        allow_full_session_replacement=allow_replace,
        fecha=target_date,
    )

    if result.ok:
        return RedirectResponse(url="/parte?ok=1", status_code=302)

    if result.status == pd.STATUS_VALIDATION:
        return _render_form(
            request, user, db,
            parte=result.parte, form=form, errors=result.errors,
            message=result.message,
            edit_state_token=result.edit_state_token,
            discard_token=result.discard_token,
            status_code=422,
        )

    if result.status == pd.STATUS_CONFLICT:
        return _render_form(
            request, user, db,
            parte=result.parte, form=form, errors=result.errors,
            message=result.message, conflict=result.conflict, stale=result.stale,
            edit_state_token=result.edit_state_token,
            discard_token=result.discard_token,
            status_code=409,
        )

    if result.status == pd.STATUS_NOT_FOUND:
        return _render_form(
            request, user, db, form=form, errors=result.errors,
            message=result.message, status_code=404,
        )

    return _render_form(
        request, user, db, form=form, errors=result.errors,
        message=result.message, status_code=500,
    )
