"""Phase 3 router integration for daily tracking (Phase 3 only).

Replaces the weekly /parte workflow with the approved daily, today-only
workflow over the existing Phase 2 domain services. Policy A and the signed
discard-confirmation protocol are preserved exactly; the router is a thin
HTTP/controller layer and does not duplicate domain validation, locking or
concurrency handling.
"""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..services import bienestar, parte_diaria as pd
from ..templates_config import templates
from ..tiempo import hoy, lunes_actual, lunes_de

router = APIRouter(prefix="/parte", tags=["parte"])


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


def _parse_session_item(text: str) -> dict:
    """Parse one session line: id|orden|tipo|duracion|rpe|comentarios.

    The pipe delimiter keeps the form simple and avoids JSON parsing on the
    client side. id is empty for new sessions.
    """
    parts = text.split("|")
    item = {"orden": 1, "tipo_entrenamiento": "resistencia",
            "duracion_min": 45, "rpe": 6, "comentarios_entrenamiento": None}
    if len(parts) >= 1 and parts[0].strip():
        try:
            item["id"] = int(parts[0].strip())
        except ValueError:
            item["id"] = None
    else:
        item["id"] = None
    if len(parts) >= 2 and parts[1].strip():
        try:
            item["orden"] = int(parts[1].strip())
        except ValueError:
            pass
    if len(parts) >= 3 and parts[2].strip():
        item["tipo_entrenamiento"] = parts[2].strip()
    if len(parts) >= 4 and parts[3].strip():
        try:
            item["duracion_min"] = int(parts[3].strip())
        except ValueError:
            pass
    if len(parts) >= 5 and parts[4].strip():
        try:
            item["rpe"] = int(parts[4].strip())
        except ValueError:
            pass
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

    Returns (payload, delete_ids, allow_replace). Sessions are parsed from
    repeated sessions fields plus optional explicit-delete and
    full-replacement flags.
    """
    sessions = form.getlist("sessions") if hasattr(form, "getlist") else form.get("sessions", [])
    raw = []
    for item in sessions:
        item = item.strip()
        if not item:
            continue
        raw.append(_parse_session_item(item))
    explicit = form.getlist("delete_session_ids") if hasattr(form, "getlist") else []
    delete_ids = []
    for item in explicit:
        item = item.strip()
        if item:
            try:
                delete_ids.append(int(item))
            except ValueError:
                pass
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
    return payload, delete_ids, allow_replace


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
    }


def _render_form(request, user, db, *, parte=None, form=None, errors=None,
                 message=None, conflict=False, stale=False, created=False,
                 edit_state_token=None, discard_token=None, status_code=200):
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
        "items": bienestar.ITEMS,
        "etiquetas": bienestar.ETIQUETAS,
        "rpe_escala": bienestar.RPE_ESCALA,
        "rpe_franjas": bienestar.RPE_FRANJAS,
        "sessions_form": sessions_form,
        "delete_form": delete_form,
    }, status_code=status_code)


@router.get("", response_class=HTMLResponse)
async def formulario(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    _athlete_required(user)

    target_date = hoy()
    parte, edit_token, discard_token = pd.get_today_state(db, user.id, target_date)

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
    payload, delete_ids, allow_replace = _session_payload(form)

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