"""Signed tokens and deterministic fingerprints for Phase 2 daily-record safety.

Policy A (approved, authoritative plan): signed edit-state token + canonical
record-and-session fingerprint, verified after PG ``SELECT ... FOR UPDATE`` lock
and reload; stale/create-race => HTTP 409, no silent overwrite, no blind
reapply/retry. Discard-confirmation protocol (signed discard token bound to
session fingerprint) is preserved and not weakened.

HMAC-SHA256 signing reuses ``settings.secret_key`` and ``hmac.compare_digest``
(same trust root/pattern as CSRF). No schema change.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Iterable, Optional

from ..config import get_settings

# Purpose labels (distinct; never interchangeable).
PURPOSE_EDIT_STATE = "edit_parte_diaria"
PURPOSE_DISCARD = "discard_sessions"

DEFAULT_EDIT_EXP_SECONDS = 900  # 15 min
DEFAULT_DISCARD_EXP_SECONDS = 900  # 15 min


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data.encode("ascii") + pad.encode("ascii"))


def _canonical_json(value: Any) -> str:
    """Deterministic JSON for hashing/signing (stable key order, no whitespace)."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _key() -> bytes:
    return get_settings().secret_key.encode("utf-8")


def _sign_payload(payload_b64: str) -> str:
    sig = hmac.new(_key(), payload_b64.encode("ascii"), hashlib.sha256).digest()
    return _b64url_encode(sig)


def _now_ts() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def _norm_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def _norm_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    s = str(value).strip().lower()
    return s in {"1", "true", "t", "yes", "y", "si", "sí"}


def _norm_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return int(value)
    return int(value)


def _norm_decimal(value: Any) -> Optional[str]:
    """Normalize decimals (e.g. horas_sueno Numeric(4,1)) deterministically."""
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        q = value.normalize()
        # Avoid scientific notation surprises; keep plain string.
        s = format(q, "f")
        if "." in s:
            s = s.rstrip("0").rstrip(".")
        return s or "0"
    try:
        d = Decimal(str(value).strip().replace(",", "."))
    except Exception:
        return str(value)
    s = format(d.normalize(), "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s or "0"


def normalize_molestia_zona(zonas: Any) -> list[str]:
    if zonas is None:
        return []
    if isinstance(zonas, str):
        # Defensive: accept comma-separated legacy-ish strings.
        items = [z.strip() for z in zonas.split(",") if z.strip()]
    elif isinstance(zonas, Iterable):
        items = [str(z).strip() for z in zonas if str(z).strip()]
    else:
        items = [str(zonas).strip()]
    # Deterministic: unique + sorted.
    return sorted(set(items))


def normalize_session_for_fingerprint(session: dict[str, Any]) -> dict[str, Any]:
    """Canonical session state included in fingerprints (stable order by caller)."""
    return {
        "id": _norm_int(session.get("id")),
        "orden": _norm_int(session.get("orden")),
        "tipo_entrenamiento": _norm_text(session.get("tipo_entrenamiento")),
        "duracion_min": _norm_int(session.get("duracion_min")),
        "rpe": _norm_int(session.get("rpe")),
        "carga_sesion": _norm_int(session.get("carga_sesion")),
        "comentarios_entrenamiento": _norm_text(
            session.get("comentarios_entrenamiento")
        ),
    }


def sorted_normalized_sessions(sessions: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize and sort sessions deterministically by (orden, id)."""
    normed = [normalize_session_for_fingerprint(s) for s in sessions]
    return sorted(
        normed,
        key=lambda s: (
            s["orden"] if s["orden"] is not None else 10**9,
            s["id"] if s["id"] is not None else 10**9,
        ),
    )


def session_state_fingerprint(sessions: Iterable[dict[str, Any]]) -> str:
    """HMAC fingerprint of persisted session set (discard binding / state)."""
    canonical = _canonical_json(sorted_normalized_sessions(sessions))
    digest = hmac.new(_key(), canonical.encode("utf-8"), hashlib.sha256).hexdigest()
    return digest


def record_state_fingerprint(
    parte: dict[str, Any], sessions: Iterable[dict[str, Any]]
) -> str:
    """Canonical record+session fingerprint for Policy A edit-state tokens.

    Includes all relevant persisted record state (normalized) + normalized
    sessions in stable order. Excludes volatile server timestamps.
    """
    fecha = parte.get("fecha")
    if isinstance(fecha, date):
        fecha_iso = fecha.isoformat()
    else:
        fecha_iso = str(fecha) if fecha is not None else None

    state = {
        "atleta_id": _norm_int(parte.get("atleta_id")),
        "fecha": fecha_iso,
        "registro_id": _norm_int(parte.get("registro_id") or parte.get("id")),
        "sueno_calidad": _norm_int(parte.get("sueno_calidad")),
        "horas_sueno": _norm_decimal(parte.get("horas_sueno")),
        "fatiga": _norm_int(parte.get("fatiga")),
        "dolor_muscular": _norm_int(parte.get("dolor_muscular")),
        "estres": _norm_int(parte.get("estres")),
        "animo": _norm_int(parte.get("animo")),
        "hay_molestia": _norm_bool(parte.get("hay_molestia")),
        "molestia_zona": normalize_molestia_zona(parte.get("molestia_zona")),
        "molestia_zona_otra": _norm_text(parte.get("molestia_zona_otra")),
        "molestia_dolor": _norm_int(parte.get("molestia_dolor")),
        "afecta_entrenamiento": _norm_int(parte.get("afecta_entrenamiento")),
        "sintomas_enfermedad": _norm_bool(parte.get("sintomas_enfermedad")),
        "detalle_sintomas": _norm_text(parte.get("detalle_sintomas")),
        "comentarios": _norm_text(parte.get("comentarios")),
        "entreno_hoy": _norm_bool(parte.get("entreno_hoy")),
        "sessions": sorted_normalized_sessions(sessions),
    }
    canonical = _canonical_json(state)
    return hmac.new(_key(), canonical.encode("utf-8"), hashlib.sha256).hexdigest()


def _issue_token(payload: dict[str, Any], exp_seconds: int) -> str:
    body = dict(payload)
    body["exp"] = _now_ts() + int(exp_seconds)
    payload_b64 = _b64url_encode(_canonical_json(body).encode("utf-8"))
    sig_b64 = _sign_payload(payload_b64)
    return f"{payload_b64}.{sig_b64}"


@dataclass
class TokenVerification:
    ok: bool
    payload: Optional[dict[str, Any]] = None
    reason: Optional[str] = None


def _verify_token(token: str, expected_purpose: str) -> TokenVerification:
    if not token or "." not in token:
        return TokenVerification(False, reason="missing_or_malformed")
    payload_b64, sig_b64 = token.rsplit(".", 1)
    try:
        expected_sig = _sign_payload(payload_b64)
    except Exception:
        return TokenVerification(False, reason="sign_error")
    if not hmac.compare_digest(expected_sig, sig_b64):
        return TokenVerification(False, reason="bad_signature")
    try:
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    except Exception:
        return TokenVerification(False, reason="bad_payload")
    if payload.get("purpose") != expected_purpose:
        return TokenVerification(False, payload=payload, reason="wrong_purpose")
    exp = payload.get("exp")
    if not isinstance(exp, int) or _now_ts() > exp:
        return TokenVerification(False, payload=payload, reason="expired")
    return TokenVerification(True, payload=payload)


def issue_edit_state_token(
    *,
    atleta_id: int,
    fecha: date,
    registro_id: Optional[int],
    fingerprint: str,
    exp_seconds: int = DEFAULT_EDIT_EXP_SECONDS,
) -> str:
    return _issue_token(
        {
            "purpose": PURPOSE_EDIT_STATE,
            "atleta_id": int(atleta_id),
            "fecha": fecha.isoformat(),
            "registro_id": int(registro_id) if registro_id is not None else None,
            "fingerprint": fingerprint,
        },
        exp_seconds,
    )


def verify_edit_state_token(
    token: str,
    *,
    atleta_id: int,
    fecha: date,
    registro_id: Optional[int],
    current_fingerprint: str,
) -> TokenVerification:
    res = _verify_token(token, PURPOSE_EDIT_STATE)
    if not res.ok or not res.payload:
        return res
    p = res.payload
    if int(p.get("atleta_id", -1)) != int(atleta_id):
        return TokenVerification(False, payload=p, reason="athlete_mismatch")
    if p.get("fecha") != fecha.isoformat():
        return TokenVerification(False, payload=p, reason="date_mismatch")
    tok_reg = p.get("registro_id")
    cur_reg = int(registro_id) if registro_id is not None else None
    if tok_reg != cur_reg:
        return TokenVerification(False, payload=p, reason="registro_mismatch")
    if not hmac.compare_digest(str(p.get("fingerprint", "")), current_fingerprint):
        return TokenVerification(False, payload=p, reason="fingerprint_mismatch")
    return res


def issue_discard_token(
    *,
    atleta_id: int,
    fecha: date,
    registro_id: int,
    session_fingerprint: str,
    exp_seconds: int = DEFAULT_DISCARD_EXP_SECONDS,
) -> str:
    return _issue_token(
        {
            "purpose": PURPOSE_DISCARD,
            "atleta_id": int(atleta_id),
            "fecha": fecha.isoformat(),
            "registro_id": int(registro_id),
            "session_fingerprint": session_fingerprint,
        },
        exp_seconds,
    )


def verify_discard_token(
    token: str,
    *,
    atleta_id: int,
    fecha: date,
    registro_id: int,
    current_session_fingerprint: str,
) -> TokenVerification:
    res = _verify_token(token, PURPOSE_DISCARD)
    if not res.ok or not res.payload:
        return res
    p = res.payload
    if int(p.get("atleta_id", -1)) != int(atleta_id):
        return TokenVerification(False, payload=p, reason="athlete_mismatch")
    if p.get("fecha") != fecha.isoformat():
        return TokenVerification(False, payload=p, reason="date_mismatch")
    if int(p.get("registro_id", -1)) != int(registro_id):
        return TokenVerification(False, payload=p, reason="registro_mismatch")
    if not hmac.compare_digest(
        str(p.get("session_fingerprint", "")), current_session_fingerprint
    ):
        return TokenVerification(False, payload=p, reason="fingerprint_mismatch")
    return res
