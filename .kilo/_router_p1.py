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

from ..database import get_db
from ..services import parte_diaria as pd
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


def _parse_session_item(text: str) -> dict:
    """Parse one session line: id|orden|tipo|duracion|rpe|comentarios.

    The pipe delimiter keeps the form simple and avoids JSON parsing on the
    client side. ``id`` is empty for new sessions.
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


def _session_payload(form) -> tuple:
    """Build the service payload from the submitted form.

    Returns (payload, delete_ids, allow_replace). Sessions are parsed from
    repeated ``sessions`` fields plus optional explicit-delete and
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
        "hay_molestia": form.get("hay_molestia") == "1",
        "molestia_zona": _parse_zonas(form.get("molestia_zona", "")),
        "molestia_zona_otra": form.get("molestia_zona_otra", ""),
        "molestia_dolor": form.get("molestia_dolor", ""),
        "afecta_entrenamiento": form.get("afecta_entrenamiento", ""),
        "sintomas_enfermedad": form.get("sintomas_enfermedad") == "1",
        "detalle_sintomas": form.get("detalle_sintomas", ""),
        "comentarios": form.get("comentarios", ""),
        "entreno_hoy": form.get("entreno_hoy") == "1",
        "sessions": raw,
    }
    return payload, delete_ids, allow_replace