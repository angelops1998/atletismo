"""Phase 2 core domain service for daily tracking (ParteDiaria).

Scope (service-level): validation/normalization, authoritative load recompute,
reported-day aggregation (missing != 0), conditional field cleanup, explicit
session operations (stable IDs, ownership binding, no implicit delete by
omission), transactional save with PG parent-row locking, Policy A stale-state
and create-race conflict handling (409 semantics at service result level),
and preserved signed discard-confirmation protocol.

No routers/templates/migrations/weekly-consumer changes. No ACWR/new alert
heuristics. PostgreSQL is authoritative for ``FOR UPDATE``/race behavior.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models.parte_diaria import MOLESTIA_ZONAS, ParteDiaria
from ..models.sesion_entrenamiento import SesionEntrenamiento, TIPOS_ENTRENAMIENTO
from ..tiempo import hoy, lunes_de
from .parte_diaria_tokens import (
    issue_discard_token,
    issue_edit_state_token,
    record_state_fingerprint,
    session_state_fingerprint,
    sorted_normalized_sessions,
    verify_discard_token,
    verify_edit_state_token,
)

# HTTP-like status codes for Phase 3 mapping (service remains transport-agnostic).
STATUS_OK = 200
STATUS_VALIDATION = 422
STATUS_CONFLICT = 409
STATUS_FORBIDDEN = 403
STATUS_NOT_FOUND = 404

MOLESTIA_ZONAS_SET = set(MOLESTIA_ZONAS)
TIPOS_SET = set(TIPOS_ENTRENAMIENTO)


@dataclass
class ServiceResult:
    ok: bool
    status: int
    message: Optional[str] = None
    errors: list[str] = field(default_factory=list)
    parte: Optional[ParteDiaria] = None
    edit_state_token: Optional[str] = None
    discard_token: Optional[str] = None
    current_fingerprint: Optional[str] = None
    conflict: bool = False
    stale: bool = False
    created: bool = False

    @property
    def data(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "status": self.status,
            "message": self.message,
            "errors": self.errors,
            "edit_state_token": self.edit_state_token,
            "discard_token": self.discard_token,
            "conflict": self.conflict,
            "stale": self.stale,
            "created": self.created,
        }


class DomainValidationError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


def _dialect_name(db: Session) -> str:
    try:
        bind = db.get_bind()
        return (bind.dialect.name or "").lower() if bind else ""
    except Exception:
        return ""


def _supports_for_update(db: Session) -> bool:
    return _dialect_name(db) in {"postgresql"}


def _to_int(value: Any, *, name: str, min_v: int, max_v: int, required: bool) -> Optional[int]:
    if value is None or value == "":
        if required:
            raise DomainValidationError([f"{name} es requerido."])
        return None
    try:
        if isinstance(value, bool):
            n = int(value)
        elif isinstance(value, (int,)):
            n = value
        elif isinstance(value, float):
            n = int(value)
        else:
            n = int(str(value).strip())
    except (TypeError, ValueError):
        raise DomainValidationError([f"{name} inválido."])
    if n < min_v or n > max_v:
        raise DomainValidationError([f"{name} fuera de rango ({min_v}-{max_v})."])
    return n


def _to_decimal(value: Any, *, name: str, min_v: Decimal, max_v: Decimal, required: bool) -> Optional[Decimal]:
    if value is None or value == "":
        if required:
            raise DomainValidationError([f"{name} es requerido."])
        return None
    try:
        d = value if isinstance(value, Decimal) else Decimal(str(value).strip().replace(",", "."))
    except (InvalidOperation, TypeError, ValueError):
        raise DomainValidationError([f"{name} inválido."])
    if d < min_v or d > max_v:
        raise DomainValidationError([f"{name} fuera de rango ({min_v}-{max_v})."])
    # Normalize to 1 decimal place for Numeric(4,1) compatibility.
    return d.quantize(Decimal("0.1"))


def _to_bool(value: Any, *, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    s = str(value).strip().lower()
    if s in {"1", "true", "t", "yes", "y", "si", "sí"}:
        return True
    if s in {"0", "false", "f", "no", "n"}:
        return False
    return default


def _to_text(value: Any, *, max_len: Optional[int] = None) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    if max_len is not None:
        s = s[:max_len]
    return s


def normalize_molestia_zona(zonas: Any) -> list[str]:
    if zonas is None:
        return []
    if isinstance(zonas, str):
        items = [z.strip() for z in zonas.split(",") if z.strip()]
    elif isinstance(zonas, Iterable):
        items = [str(z).strip() for z in zonas if str(z).strip()]
    else:
        items = [str(zonas).strip()]
    clean = sorted(set(items))
    invalid = [z for z in clean if z not in MOLESTIA_ZONAS_SET]
    if invalid:
        raise DomainValidationError([f"Zona(s) de molestia inválida(s): {', '.join(invalid)}."])
    return clean


def serialize_parte(parte: ParteDiaria) -> dict[str, Any]:
    sesiones = sorted(
        (serialize_session(s) for s in (parte.sesiones or [])),
        key=lambda s: (s.get("orden") or 10**9, s.get("id") or 10**9),
    )
    return {
        "id": parte.id,
        "registro_id": parte.id,
        "atleta_id": parte.atleta_id,
        "fecha": parte.fecha,
        "sueno_calidad": parte.sueno_calidad,
        "horas_sueno": parte.horas_sueno,
        "fatiga": parte.fatiga,
        "dolor_muscular": parte.dolor_muscular,
        "estres": parte.estres,
        "animo": parte.animo,
        "hay_molestia": bool(parte.hay_molestia),
        "molestia_zona": list(parte.molestia_zona) if parte.molestia_zona else [],
        "molestia_zona_otra": parte.molestia_zona_otra,
        "molestia_dolor": parte.molestia_dolor,
        "afecta_entrenamiento": parte.afecta_entrenamiento,
        "sintomas_enfermedad": bool(parte.sintomas_enfermedad),
        "detalle_sintomas": parte.detalle_sintomas,
        "comentarios": parte.comentarios,
        "entreno_hoy": bool(parte.entreno_hoy),
        "sessions": sesiones,
    }


def serialize_session(s: SesionEntrenamiento) -> dict[str, Any]:
    return {
        "id": s.id,
        "orden": s.orden,
        "tipo_entrenamiento": s.tipo_entrenamiento,
        "duracion_min": s.duracion_min,
        "rpe": s.rpe,
        "carga_sesion": s.carga_sesion,
        "comentarios_entrenamiento": s.comentarios_entrenamiento,
    }


def current_fingerprint(parte: ParteDiaria) -> str:
    data = serialize_parte(parte)
    return record_state_fingerprint(data, data.get("sessions") or [])


def current_session_fingerprint(parte: ParteDiaria) -> str:
    data = serialize_parte(parte)
    return session_state_fingerprint(data.get("sessions") or [])


def _lock_today_query(db: Session, atleta_id: int, fecha: date):
    stmt = select(ParteDiaria).where(
        ParteDiaria.atleta_id == atleta_id, ParteDiaria.fecha == fecha
    )
    if _supports_for_update(db):
        stmt = stmt.with_for_update()
    return stmt


def load_today_for_update(db: Session, atleta_id: int, fecha: Optional[date] = None) -> Optional[ParteDiaria]:
    """Load today's ParteDiaria with PG row lock when supported."""
    f = fecha or hoy()
    return db.execute(_lock_today_query(db, atleta_id, f)).scalars().first()


def load_today(db: Session, atleta_id: int, fecha: Optional[date] = None) -> Optional[ParteDiaria]:
    f = fecha or hoy()
    return db.execute(
        select(ParteDiaria).where(ParteDiaria.atleta_id == atleta_id, ParteDiaria.fecha == f)
    ).scalars().first()


def get_today_state(db: Session, atleta_id: int, fecha: Optional[date] = None) -> tuple[Optional[ParteDiaria], Optional[str], Optional[str]]:
    """Read today state and issue fresh tokens for current persisted state."""
    f = fecha or hoy()
    parte = load_today(db, atleta_id, f)
    if not parte:
        return None, None, None
    fp = current_fingerprint(parte)
    sfp = current_session_fingerprint(parte)
    edit_tok = issue_edit_state_token(
        atleta_id=atleta_id, fecha=f, registro_id=parte.id, fingerprint=fp
    )
    discard_tok = issue_discard_token(
        atleta_id=atleta_id, fecha=f, registro_id=parte.id, session_fingerprint=sfp
    )
    return parte, edit_tok, discard_tok


def carga_sesion(duracion_min: int, rpe: int) -> int:
    return int(duracion_min) * int(rpe)


def carga_diaria(parte: Optional[ParteDiaria]) -> int:
    """Daily load for a reported record. Missing record is NOT zero (handled by caller)."""
    if not parte:
        return 0
    if not parte.entreno_hoy:
        return 0
    return sum(int(s.carga_sesion or 0) for s in (parte.sesiones or []))


@dataclass
class WeeklyAggregation:
    carga_semanal: int
    dias_reportados: int
    dias_con_entreno: int
    cargas_diarias: dict[str, Optional[int]]  # iso date -> carga or None if missing


def aggregate_week_reported(
    db: Session, atleta_id: int, semana_lunes: date
) -> WeeklyAggregation:
    """Aggregate Mon-Sun using only reported daily records. Missing != 0."""
    dias = [semana_lunes.fromordinal(semana_lunes.toordinal() + i) for i in range(7)]
    rows = (
        db.execute(
            select(ParteDiaria).where(
                ParteDiaria.atleta_id == atleta_id, ParteDiaria.fecha.in_(dias)
            )
        )
        .scalars()
        .all()
    )
    by_fecha = {r.fecha: r for r in rows}
    cargas: dict[str, Optional[int]] = {}
    total = 0
    dias_entreno = 0
    for d in dias:
        r = by_fecha.get(d)
        if not r:
            cargas[d.isoformat()] = None  # missing != 0
            continue
        cd = carga_diaria(r)
        cargas[d.isoformat()] = cd
        total += cd
        if r.entreno_hoy and (r.sesiones or []):
            dias_entreno += 1
    return WeeklyAggregation(
        carga_semanal=total,
        dias_reportados=len(by_fecha),
        dias_con_entreno=dias_entreno,
        cargas_diarias=cargas,
    )


def validate_and_normalize_wellness(data: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    out: dict[str, Any] = {}

    def req_int(name: str, lo: int, hi: int) -> None:
        try:
            out[name] = _to_int(data.get(name), name=name, min_v=lo, max_v=hi, required=True)
        except DomainValidationError as e:
            errors.extend(e.errors)

    req_int("sueno_calidad", 1, 10)
    req_int("fatiga", 1, 10)
    req_int("dolor_muscular", 1, 10)
    req_int("estres", 1, 10)
    req_int("animo", 1, 10)

    try:
        out["horas_sueno"] = _to_decimal(
            data.get("horas_sueno"),
            name="horas_sueno",
            min_v=Decimal("0"),
            max_v=Decimal("24"),
            required=True,
        )
    except DomainValidationError as e:
        errors.extend(e.errors)

    hay_molestia = _to_bool(data.get("hay_molestia"), default=False)
    out["hay_molestia"] = hay_molestia
    if hay_molestia:
        try:
            zonas = normalize_molestia_zona(data.get("molestia_zona"))
        except DomainValidationError as e:
            errors.extend(e.errors)
            zonas = []
        if not zonas:
            errors.append("Seleccioná al menos una zona de molestia.")
        out["molestia_zona"] = zonas or None
        if "otro" in (zonas or []):
            otra = _to_text(data.get("molestia_zona_otra"), max_len=120)
            if not otra:
                errors.append("Indicá la otra zona de molestia.")
            out["molestia_zona_otra"] = otra
        else:
            out["molestia_zona_otra"] = None
        try:
            out["molestia_dolor"] = _to_int(
                data.get("molestia_dolor"), name="molestia_dolor", min_v=1, max_v=10, required=True
            )
        except DomainValidationError as e:
            errors.extend(e.errors)
        try:
            out["afecta_entrenamiento"] = _to_int(
                data.get("afecta_entrenamiento"),
                name="afecta_entrenamiento",
                min_v=0,
                max_v=3,
                required=True,
            )
        except DomainValidationError as e:
            errors.extend(e.errors)
    else:
        out["molestia_zona"] = None
        out["molestia_zona_otra"] = None
        out["molestia_dolor"] = None
        out["afecta_entrenamiento"] = None

    sintomas = _to_bool(data.get("sintomas_enfermedad"), default=False)
    out["sintomas_enfermedad"] = sintomas
    detalle = _to_text(data.get("detalle_sintomas"))
    out["detalle_sintomas"] = detalle if sintomas else None

    out["comentarios"] = _to_text(data.get("comentarios"))
    out["entreno_hoy"] = _to_bool(data.get("entreno_hoy"), default=False)

    if errors:
        raise DomainValidationError(errors)
    return out


def validate_and_normalize_sessions(
    raw_sessions: Any, *, entreno_hoy: bool
) -> list[dict[str, Any]]:
    errors: list[str] = []
    if raw_sessions is None:
        raw_sessions = []
    if not isinstance(raw_sessions, list):
        raise DomainValidationError(["sessions debe ser una lista."])

    normalized: list[dict[str, Any]] = []
    for idx, raw in enumerate(raw_sessions):
        if not isinstance(raw, dict):
            errors.append(f"Sesión {idx + 1} inválida.")
            continue
        sid = raw.get("id")
        sid_norm = None
        if sid is not None and sid != "":
            try:
                sid_norm = int(sid)
            except (TypeError, ValueError):
                errors.append(f"Sesión {idx + 1}: id inválido.")
                continue
        tipo = _to_text(raw.get("tipo_entrenamiento"))
        if not tipo or tipo not in TIPOS_SET:
            errors.append(f"Sesión {idx + 1}: tipo_entrenamiento inválido.")
            continue
        try:
            dur = _to_int(raw.get("duracion_min"), name=f"Sesión {idx + 1} duracion_min", min_v=1, max_v=10**6, required=True)
            rpe = _to_int(raw.get("rpe"), name=f"Sesión {idx + 1} rpe", min_v=1, max_v=10, required=True)
            orden = _to_int(raw.get("orden"), name=f"Sesión {idx + 1} orden", min_v=0, max_v=10**6, required=False)
        except DomainValidationError as e:
            errors.extend(e.errors)
            continue
        if dur is None or rpe is None:
            continue
        normalized.append(
            {
                "id": sid_norm,
                "orden": orden if orden is not None else idx + 1,
                "tipo_entrenamiento": tipo,
                "duracion_min": dur,
                "rpe": rpe,
                "carga_sesion": carga_sesion(dur, rpe),
                "comentarios_entrenamiento": _to_text(raw.get("comentarios_entrenamiento")),
            }
        )

    if entreno_hoy and not normalized:
        errors.append("Agregá al menos una sesión válida cuando entrenaste hoy.")
    if not entreno_hoy:
        # entreno_hoy=false means zero sessions persisted; caller must not pass sessions
        # except through discard/explicit replacement flow. Service enforces empty result.
        normalized = []

    # Stable ordering
    normalized.sort(key=lambda s: (s.get("orden") or 10**9, s.get("id") or 10**9))
    for i, s in enumerate(normalized, start=1):
        if s.get("orden") is None:
            s["orden"] = i

    if errors:
        raise DomainValidationError(errors)
    return normalized


def _sessions_match_state(parte: ParteDiaria, desired_sessions: list[dict[str, Any]]) -> bool:
    """Used to detect no-op / whether submitted state already means no sessions."""
    current = sorted_normalized_sessions(serialize_parte(parte).get("sessions") or [])
    desired = sorted_normalized_sessions(desired_sessions)
    # Compare canonical fields relevant to persisted state
    def key(s):
        return {k: s.get(k) for k in ["id", "orden", "tipo_entrenamiento", "duracion_min", "rpe", "carga_sesion", "comentarios_entrenamiento"]}
    return [key(s) for s in current] == [key(s) for s in desired]


def _apply_sessions(
    db: Session,
    parte: ParteDiaria,
    desired_sessions: list[dict[str, Any]],
    *,
    allow_delete_omitted: bool = False,
    explicit_delete_ids: Optional[set[int]] = None,
) -> None:
    """Apply explicit session operations. Default: no implicit delete by omission."""
    explicit_delete_ids = explicit_delete_ids or set()
    current_by_id = {s.id: s for s in (parte.sesiones or []) if s.id is not None}
    desired_ids = {s["id"] for s in desired_sessions if s.get("id") is not None}

    # Ownership/binding: every referenced id must belong to locked record.
    for ref_id in desired_ids | explicit_delete_ids:
        if ref_id not in current_by_id:
            raise DomainValidationError([f"Sesión {ref_id} no pertenece al registro actual."])

    # Deletes: explicit only, unless validated full replacement mode.
    if allow_delete_omitted:
        to_delete = set(current_by_id.keys()) - desired_ids
    else:
        to_delete = set(explicit_delete_ids)
        # Any current id omitted but not explicitly deleted is preserved.
        # (We do not auto-delete; desired list represents upserts/adds.)

    for did in to_delete:
        obj = current_by_id.get(did)
        if obj is not None:
            db.delete(obj)

    # Refresh map after deletes
    db.flush()
    current_by_id = {s.id: s for s in (parte.sesiones or []) if s.id is not None}

    # Upsert/update and add
    for ds in desired_sessions:
        sid = ds.get("id")
        if sid is not None and sid in current_by_id:
            obj = current_by_id[sid]
            obj.orden = ds["orden"]
            obj.tipo_entrenamiento = ds["tipo_entrenamiento"]
            obj.duracion_min = ds["duracion_min"]
            obj.rpe = ds["rpe"]
            obj.carga_sesion = ds["carga_sesion"]  # authoritative recompute
            obj.comentarios_entrenamiento = ds["comentarios_entrenamiento"]
        elif sid is None:
            parte.sesiones.append(
                SesionEntrenamiento(
                    orden=ds["orden"],
                    tipo_entrenamiento=ds["tipo_entrenamiento"],
                    duracion_min=ds["duracion_min"],
                    rpe=ds["rpe"],
                    carga_sesion=ds["carga_sesion"],
                    comentarios_entrenamiento=ds["comentarios_entrenamiento"],
                )
            )
        # if sid provided but deleted explicitly in same request, ignore (conflict avoided by validation)

    db.flush()


def _apply_wellness(parte: ParteDiaria, norm: dict[str, Any]) -> None:
    for k, v in norm.items():
        if k == "sessions":
            continue
        setattr(parte, k, v)


def _fresh_tokens(parte: ParteDiaria) -> tuple[str, str]:
    fp = current_fingerprint(parte)
    sfp = current_session_fingerprint(parte)
    edit_tok = issue_edit_state_token(
        atleta_id=parte.atleta_id, fecha=parte.fecha, registro_id=parte.id, fingerprint=fp
    )
    discard_tok = issue_discard_token(
        atleta_id=parte.atleta_id, fecha=parte.fecha, registro_id=parte.id, session_fingerprint=sfp
    )
    return edit_tok, discard_tok


def _conflict_result(
    db: Session,
    atleta_id: int,
    fecha: date,
    message: str,
    *,
    stale: bool = False,
) -> ServiceResult:
    db.rollback()
    parte = load_today(db, atleta_id, fecha)
    edit_tok = discard_tok = None
    if parte:
        try:
            # no lock needed for token issuance; reflects current committed state
            db.refresh(parte)
        except Exception:
            parte = load_today(db, atleta_id, fecha)
        if parte:
            edit_tok, discard_tok = _fresh_tokens(parte)
    return ServiceResult(
        ok=False,
        status=STATUS_CONFLICT,
        message=message,
        parte=parte,
        edit_state_token=edit_tok,
        discard_token=discard_tok,
        current_fingerprint=current_fingerprint(parte) if parte else None,
        conflict=True,
        stale=stale,
        errors=[message],
    )


def save_daily_record(
    db: Session,
    *,
    atleta_id: int,
    payload: dict[str, Any],
    edit_state_token: Optional[str] = None,
    discard_token: Optional[str] = None,
    confirm_discard_sessions: bool = False,
    explicit_delete_session_ids: Optional[Iterable[int]] = None,
    allow_full_session_replacement: bool = False,
    fecha: Optional[date] = None,
) -> ServiceResult:
    """Create/update today's daily record transactionally with Policy A.

    - Server date authority: ``fecha`` defaults to ``hoy()`` (athlete today-only).
    - Existing record mutations require valid edit-state token verified AFTER
      ``FOR UPDATE`` lock + reload. Stale/tamper/wrong binding => 409, no write.
    - ``IntegrityError`` on create race => rollback+reload => 409, no blind reapply.
    - ``entreno_hoy`` true->false with existing sessions requires valid discard
      token + explicit confirmation (preserved protocol); stale => conflict, no delete.
    """
    target_fecha = fecha or hoy()
    explicit_delete_ids = {int(x) for x in (explicit_delete_session_ids or [])}

    try:
        wellness = validate_and_normalize_wellness(payload)
        sessions = validate_and_normalize_sessions(
            payload.get("sessions"), entreno_hoy=wellness["entreno_hoy"]
        )
    except DomainValidationError as e:
        return ServiceResult(
            ok=False, status=STATUS_VALIDATION, message="Datos inválidos.", errors=e.errors
        )

    try:
        parte = load_today_for_update(db, atleta_id, target_fecha)

        if parte is None:
            # Create path
            if not wellness["entreno_hoy"]:
                sessions = []
            new = ParteDiaria(atleta_id=atleta_id, fecha=target_fecha)
            _apply_wellness(new, wellness)
            db.add(new)
            db.flush()
            # Add sessions
            if sessions:
                for ds in sessions:
                    new.sesiones.append(
                        SesionEntrenamiento(
                            orden=ds["orden"],
                            tipo_entrenamiento=ds["tipo_entrenamiento"],
                            duracion_min=ds["duracion_min"],
                            rpe=ds["rpe"],
                            carga_sesion=ds["carga_sesion"],
                            comentarios_entrenamiento=ds["comentarios_entrenamiento"],
                        )
                    )
            try:
                db.commit()
            except IntegrityError:
                return _conflict_result(
                    db,
                    atleta_id,
                    target_fecha,
                    "El registro de hoy fue creado o actualizado en otra solicitud. Recargá los datos actuales y volvé a intentarlo.",
                    stale=True,
                )
            db.refresh(new)
            edit_tok, discard_tok2 = _fresh_tokens(new)
            return ServiceResult(
                ok=True,
                status=STATUS_OK,
                message="Registro diario guardado.",
                parte=new,
                edit_state_token=edit_tok,
                discard_token=discard_tok2,
                current_fingerprint=current_fingerprint(new),
                created=True,
            )

        # Existing record: Policy A edit-state verification AFTER lock+reload.
        current_fp = current_fingerprint(parte)
        ver = verify_edit_state_token(
            edit_state_token or "",
            atleta_id=atleta_id,
            fecha=target_fecha,
            registro_id=parte.id,
            current_fingerprint=current_fp,
        )
        if not ver.ok:
            return _conflict_result(
                db,
                atleta_id,
                target_fecha,
                "Tu información está desactualizada. Recargá el registro actual antes de guardar.",
                stale=True,
            )

        has_existing_sessions = bool(parte.sesiones)
        turning_off_training = bool(parte.entreno_hoy) and not bool(wellness["entreno_hoy"])
        if turning_off_training and has_existing_sessions:
            # Preserve discard-confirmation protocol (no silent delete).
            current_sfp = current_session_fingerprint(parte)
            if not confirm_discard_sessions or not discard_token:
                # Step 1 / intent: no deletion, issue discard token for current state.
                db.rollback()
                parte = load_today(db, atleta_id, target_fecha)
                edit_tok2, discard_tok2 = _fresh_tokens(parte) if parte else (None, None)
                return ServiceResult(
                    ok=False,
                    status=STATUS_VALIDATION,
                    message="Confirmá explícitamente el descarte de las sesiones existentes antes de guardar sin entrenamiento.",
                    errors=["Se requiere confirmación explícita para descartar sesiones."],
                    parte=parte,
                    edit_state_token=edit_tok2,
                    discard_token=discard_tok2 or issue_discard_token(
                        atleta_id=atleta_id, fecha=target_fecha, registro_id=parte.id, session_fingerprint=current_sfp
                    ),
                    current_fingerprint=current_fingerprint(parte) if parte else current_fp,
                    conflict=False,
                )
            dver = verify_discard_token(
                discard_token,
                atleta_id=atleta_id,
                fecha=target_fecha,
                registro_id=parte.id,
                current_session_fingerprint=current_sfp,
            )
            if not dver.ok:
                return _conflict_result(
                    db,
                    atleta_id,
                    target_fecha,
                    "La confirmación de descarte es inválida o está desactualizada. Recargá el registro actual.",
                    stale=True,
                )
            # Authorized discard in same locked tx
            for s in list(parte.sesiones or []):
                db.delete(s)
            parte.entreno_hoy = False
            _apply_wellness(parte, {**wellness, "entreno_hoy": False})
            db.commit()
            db.refresh(parte)
            edit_tok2, discard_tok2 = _fresh_tokens(parte)
            return ServiceResult(
                ok=True,
                status=STATUS_OK,
                message="Registro diario actualizado (sesiones descartadas).",
                parte=parte,
                edit_state_token=edit_tok2,
                discard_token=discard_tok2,
                current_fingerprint=current_fingerprint(parte),
            )

        # Normal update
        if not wellness["entreno_hoy"]:
            sessions = []
            # If currently has sessions but not turning off training in the guarded
            # branch above, keep safe: require discard path. (Should be unreachable.)
            if has_existing_sessions and not parte.entreno_hoy:
                pass
            elif has_existing_sessions and parte.entreno_hoy:
                # covered by turning_off_training
                pass

        _apply_wellness(parte, wellness)
        if wellness["entreno_hoy"]:
            _apply_sessions(
                db,
                parte,
                sessions,
                allow_delete_omitted=allow_full_session_replacement,
                explicit_delete_ids=explicit_delete_ids,
            )
            parte.entreno_hoy = True
        else:
            # entreno_hoy false and no discard-needed case (no existing sessions)
            for s in list(parte.sesiones or []):
                db.delete(s)
            parte.entreno_hoy = False

        db.commit()
        db.refresh(parte)
        edit_tok2, discard_tok2 = _fresh_tokens(parte)
        return ServiceResult(
            ok=True,
            status=STATUS_OK,
            message="Registro diario actualizado.",
            parte=parte,
            edit_state_token=edit_tok2,
            discard_token=discard_tok2,
            current_fingerprint=current_fingerprint(parte),
        )
    except DomainValidationError as e:
        db.rollback()
        return ServiceResult(
            ok=False, status=STATUS_VALIDATION, message="Datos inválidos.", errors=e.errors
        )
    except IntegrityError:
        return _conflict_result(
            db,
            atleta_id,
            target_fecha,
            "Conflicto al guardar el registro diario. Recargá los datos actuales y volvé a intentarlo.",
            stale=True,
        )
    except Exception as e:
        db.rollback()
        return ServiceResult(
            ok=False,
            status=STATUS_VALIDATION,
            message="No se pudo guardar el registro diario.",
            errors=[str(e)],
        )


def discard_sessions(
    db: Session,
    *,
    atleta_id: int,
    edit_state_token: Optional[str],
    discard_token: Optional[str],
    confirm: bool,
    fecha: Optional[date] = None,
) -> ServiceResult:
    """Preserved discard-confirmation protocol as an explicit service operation."""
    target_fecha = fecha or hoy()
    if not confirm or not discard_token:
        parte = load_today(db, atleta_id, target_fecha)
        edit_tok2 = discard_tok2 = None
        if parte:
            edit_tok2, discard_tok2 = _fresh_tokens(parte)
        return ServiceResult(
            ok=False,
            status=STATUS_VALIDATION,
            message="Confirmación explícita requerida para descartar sesiones.",
            errors=["Confirmación requerida."],
            parte=parte,
            edit_state_token=edit_tok2,
            discard_token=discard_tok2,
        )

    try:
        parte = load_today_for_update(db, atleta_id, target_fecha)
        if not parte:
            db.rollback()
            return ServiceResult(
                ok=False, status=STATUS_NOT_FOUND, message="No existe registro diario para hoy.", errors=["Registro no encontrado."]
            )
        # Verify edit-state (no weakening) + discard token against locked current state
        current_fp = current_fingerprint(parte)
        ever = verify_edit_state_token(
            edit_state_token or "",
            atleta_id=atleta_id,
            fecha=target_fecha,
            registro_id=parte.id,
            current_fingerprint=current_fp,
        )
        if not ever.ok:
            return _conflict_result(
                db, atleta_id, target_fecha,
                "Tu información está desactualizada. Recargá el registro actual antes de descartar sesiones.",
                stale=True,
            )
        current_sfp = current_session_fingerprint(parte)
        dver = verify_discard_token(
            discard_token,
            atleta_id=atleta_id,
            fecha=target_fecha,
            registro_id=parte.id,
            current_session_fingerprint=current_sfp,
        )
        if not dver.ok:
            return _conflict_result(
                db, atleta_id, target_fecha,
                "La confirmación de descarte es inválida o está desactualizada. Recargá el registro actual.",
                stale=True,
            )
        for s in list(parte.sesiones or []):
            db.delete(s)
        parte.entreno_hoy = False
        db.commit()
        db.refresh(parte)
        edit_tok2, discard_tok2 = _fresh_tokens(parte)
        return ServiceResult(
            ok=True,
            status=STATUS_OK,
            message="Sesiones descartadas.",
            parte=parte,
            edit_state_token=edit_tok2,
            discard_token=discard_tok2,
            current_fingerprint=current_fingerprint(parte),
        )
    except IntegrityError:
        return _conflict_result(
            db, atleta_id, target_fecha, "Conflicto al descartar sesiones. Recargá e intentá de nuevo.", stale=True
        )
    except Exception as e:
        db.rollback()
        return ServiceResult(ok=False, status=STATUS_VALIDATION, message="No se pudo descartar sesiones.", errors=[str(e)])


__all__ = [
    "ServiceResult",
    "DomainValidationError",
    "STATUS_OK",
    "STATUS_VALIDATION",
    "STATUS_CONFLICT",
    "STATUS_FORBIDDEN",
    "STATUS_NOT_FOUND",
    "load_today",
    "load_today_for_update",
    "get_today_state",
    "serialize_parte",
    "serialize_session",
    "current_fingerprint",
    "current_session_fingerprint",
    "carga_sesion",
    "carga_diaria",
    "aggregate_week_reported",
    "validate_and_normalize_wellness",
    "validate_and_normalize_sessions",
    "save_daily_record",
    "discard_sessions",
]
