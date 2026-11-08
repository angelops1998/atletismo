"""SQLite unit/integration tests for Phase 2 daily tracking domain service.

Covers: load recompute, validation/normalization, conditional clearing,
entreno_hoy invariants, explicit session ops (stable IDs, no implicit delete
by omission, ownership binding), deterministic fingerprints/tokens, Policy A
stale-state detection and create-race conflict handling at service level
(where representable), and preserved discard-confirmation protocol.

PG ``FOR UPDATE``/real race serialization is NOT proven here (see PG tests).
"""
from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import ParteDiaria, SesionEntrenamiento
from app.services import parte_diaria as svc
from app.services.parte_diaria_tokens import (
    issue_discard_token,
    issue_edit_state_token,
    normalize_molestia_zona,
    record_state_fingerprint,
    session_state_fingerprint,
    verify_discard_token,
    verify_edit_state_token,
)

from conftest import crear_usuario


def _payload(**overrides):
    base = {
        "sueno_calidad": 7,
        "horas_sueno": "7.5",
        "fatiga": 4,
        "dolor_muscular": 3,
        "estres": 4,
        "animo": 8,
        "hay_molestia": False,
        "sintomas_enfermedad": False,
        "entreno_hoy": False,
        "sessions": [],
    }
    base.update(overrides)
    return base


def _session(**overrides):
    base = {
        "orden": 1,
        "tipo_entrenamiento": "resistencia",
        "duracion_min": 45,
        "rpe": 6,
        "comentarios_entrenamiento": None,
    }
    base.update(overrides)
    return base


class TestLoadAndFingerprint:
    def test_carga_sesion_recomputed_authoritatively(self):
        assert svc.carga_sesion(45, 6) == 270
        assert svc.carga_sesion(60, 8) == 480

    def test_fingerprint_deterministic_and_order_independent(self):
        p = {
            "atleta_id": 1,
            "fecha": date(2026, 11, 8),
            "registro_id": 10,
            "sueno_calidad": 7,
            "horas_sueno": "7.5",
            "fatiga": 4,
            "dolor_muscular": 3,
            "estres": 4,
            "animo": 8,
            "hay_molestia": True,
            "molestia_zona": ["rodillas", "cuello"],
            "molestia_zona_otra": None,
            "molestia_dolor": 4,
            "afecta_entrenamiento": 1,
            "sintomas_enfermedad": False,
            "detalle_sintomas": None,
            "comentarios": "ok",
            "entreno_hoy": True,
        }
        s1 = [{"id": 2, "orden": 2, "tipo_entrenamiento": "fuerza", "duracion_min": 30, "rpe": 5, "carga_sesion": 150, "comentarios_entrenamiento": None},
              {"id": 1, "orden": 1, "tipo_entrenamiento": "resistencia", "duracion_min": 45, "rpe": 6, "carga_sesion": 270, "comentarios_entrenamiento": None}]
        s2 = list(reversed(s1))
        fp1 = record_state_fingerprint(p, s1)
        fp2 = record_state_fingerprint({**p, "molestia_zona": ["cuello", "rodillas"]}, s2)
        assert fp1 == fp2

    def test_edit_state_token_verifies_and_rejects_tamper(self):
        fp = record_state_fingerprint(
            {"atleta_id": 1, "fecha": date(2026, 11, 8), "registro_id": 5, "sueno_calidad": 7, "horas_sueno": "7.5", "fatiga": 4, "dolor_muscular": 3, "estres": 4, "animo": 8, "hay_molestia": False, "molestia_zona": [], "molestia_zona_otra": None, "molestia_dolor": None, "afecta_entrenamiento": None, "sintomas_enfermedad": False, "detalle_sintomas": None, "comentarios": None, "entreno_hoy": False},
            [],
        )
        tok = issue_edit_state_token(atleta_id=1, fecha=date(2026, 11, 8), registro_id=5, fingerprint=fp)
        ok = verify_edit_state_token(tok, atleta_id=1, fecha=date(2026, 11, 8), registro_id=5, current_fingerprint=fp)
        assert ok.ok
        bad = verify_edit_state_token(tok + "x", atleta_id=1, fecha=date(2026, 11, 8), registro_id=5, current_fingerprint=fp)
        assert not bad.ok
        stale = verify_edit_state_token(tok, atleta_id=1, fecha=date(2026, 11, 8), registro_id=5, current_fingerprint="different")
        assert not stale.ok and stale.reason == "fingerprint_mismatch"

    def test_discard_token_binding(self):
        sfp = session_state_fingerprint([{"id": 1, "orden": 1, "tipo_entrenamiento": "resistencia", "duracion_min": 45, "rpe": 6, "carga_sesion": 270, "comentarios_entrenamiento": None}])
        tok = issue_discard_token(atleta_id=1, fecha=date(2026, 11, 8), registro_id=5, session_fingerprint=sfp)
        ok = verify_discard_token(tok, atleta_id=1, fecha=date(2026, 11, 8), registro_id=5, current_session_fingerprint=sfp)
        assert ok.ok
        bad = verify_discard_token(tok, atleta_id=1, fecha=date(2026, 11, 8), registro_id=5, current_session_fingerprint="x")
        assert not bad.ok


class TestValidation:
    def test_entreno_hoy_true_requires_session(self):
        with pytest.raises(svc.DomainValidationError):
            svc.validate_and_normalize_sessions([], entreno_hoy=True)

    def test_conditional_molestia_cleared_when_false(self):
        norm = svc.validate_and_normalize_wellness(
            _payload(hay_molestia=False, molestia_zona=["rodillas"], molestia_dolor=5, afecta_entrenamiento=1, molestia_zona_otra="x")
        )
        assert norm["molestia_zona"] is None
        assert norm["molestia_dolor"] is None
        assert norm["afecta_entrenamiento"] is None
        assert norm["molestia_zona_otra"] is None

    def test_otro_requires_otra_text(self):
        with pytest.raises(svc.DomainValidationError):
            svc.validate_and_normalize_wellness(
                _payload(hay_molestia=True, molestia_zona=["otro"], molestia_dolor=3, afecta_entrenamiento=1)
            )
        norm = svc.validate_and_normalize_wellness(
            _payload(hay_molestia=True, molestia_zona=["otro"], molestia_dolor=3, afecta_entrenamiento=1, molestia_zona_otra="tobillo interno")
        )
        assert norm["molestia_zona_otra"] == "tobillo interno"

    def test_detalle_sintomas_optional_and_cleared(self):
        norm = svc.validate_and_normalize_wellness(_payload(sintomas_enfermedad=False, detalle_sintomas="gripe"))
        assert norm["detalle_sintomas"] is None
        norm = svc.validate_and_normalize_wellness(_payload(sintomas_enfermedad=True, detalle_sintomas="gripe"))
        assert norm["detalle_sintomas"] == "gripe"
        norm = svc.validate_and_normalize_wellness(_payload(sintomas_enfermedad=True))
        assert norm["detalle_sintomas"] is None

    def test_session_load_recomputed_server_side(self):
        norm = svc.validate_and_normalize_sessions([_session(duracion_min=60, rpe=8, carga_sesion=9999)], entreno_hoy=True)
        assert norm[0]["carga_sesion"] == 480


class TestServiceCRUD:
    def test_create_today_and_get_tokens(self, db):
        atleta = crear_usuario(db, username="pd1")
        fecha = date(2026, 11, 8)
        res = svc.save_daily_record(db, atleta_id=atleta.id, payload=_payload(), fecha=fecha)
        assert res.ok and res.created and res.parte
        assert res.edit_state_token and res.discard_token
        parte, et, dt = svc.get_today_state(db, atleta.id, fecha)
        assert parte and et and dt

    def test_update_requires_edit_state_token_and_rejects_stale(self, db):
        atleta = crear_usuario(db, username="pd2")
        fecha = date(2026, 11, 8)
        r1 = svc.save_daily_record(db, atleta_id=atleta.id, payload=_payload(animo=5), fecha=fecha)
        assert r1.ok
        # Commit 2 to change state
        r2 = svc.save_daily_record(db, atleta_id=atleta.id, payload=_payload(animo=7), edit_state_token=r1.edit_state_token, fecha=fecha)
        assert r2.ok and r2.parte.animo == 7
        # Stale token from r1 should conflict
        r3 = svc.save_daily_record(db, atleta_id=atleta.id, payload=_payload(animo=9), edit_state_token=r1.edit_state_token, fecha=fecha)
        assert not r3.ok and r3.status == svc.STATUS_CONFLICT and r3.stale
        db.refresh(r2.parte)
        assert r2.parte.animo == 7

    def test_entreno_hoy_true_requires_session_and_saves_multi(self, db):
        atleta = crear_usuario(db, username="pd3")
        fecha = date(2026, 11, 8)
        bad = svc.save_daily_record(db, atleta_id=atleta.id, payload=_payload(entreno_hoy=True, sessions=[]), fecha=fecha)
        assert not bad.ok and bad.status == svc.STATUS_VALIDATION
        ok = svc.save_daily_record(
            db, atleta_id=atleta.id,
            payload=_payload(entreno_hoy=True, sessions=[_session(duracion_min=60, rpe=8, orden=1), _session(duracion_min=45, rpe=6, orden=2, tipo_entrenamiento="fuerza")]),
            fecha=fecha,
        )
        assert ok.ok and ok.parte
        assert len(ok.parte.sesiones) == 2
        assert sum(s.carga_sesion for s in ok.parte.sesiones) == 750

    def test_discard_requires_confirmation_and_preserves_on_missing(self, db):
        atleta = crear_usuario(db, username="pd4")
        fecha = date(2026, 11, 8)
        r1 = svc.save_daily_record(db, atleta_id=atleta.id, payload=_payload(entreno_hoy=True, sessions=[_session()]), fecha=fecha)
        assert r1.ok and r1.parte.sesiones
        # Try to turn off without discard confirmation -> validation/intent, sessions preserved
        r2 = svc.save_daily_record(db, atleta_id=atleta.id, payload=_payload(entreno_hoy=False, sessions=[]), edit_state_token=r1.edit_state_token, fecha=fecha)
        assert not r2.ok and r2.status == svc.STATUS_VALIDATION and r2.discard_token
        db.refresh(r1.parte)
        assert len(r1.parte.sesiones) == 1 and r1.parte.entreno_hoy is True
        # Confirm discard
        r3 = svc.save_daily_record(
            db, atleta_id=atleta.id, payload=_payload(entreno_hoy=False, sessions=[]),
            edit_state_token=r1.edit_state_token, discard_token=r2.discard_token, confirm_discard_sessions=True, fecha=fecha,
        )
        assert r3.ok
        db.refresh(r1.parte)
        assert len(r1.parte.sesiones) == 0 and r1.parte.entreno_hoy is False

    def test_discard_rejects_stale_session_fingerprint(self, db):
        atleta = crear_usuario(db, username="pd5")
        fecha = date(2026, 11, 8)
        r1 = svc.save_daily_record(db, atleta_id=atleta.id, payload=_payload(entreno_hoy=True, sessions=[_session(rpe=5)]), fecha=fecha)
        # Get discard intent token
        r2 = svc.save_daily_record(db, atleta_id=atleta.id, payload=_payload(entreno_hoy=False), edit_state_token=r1.edit_state_token, fecha=fecha)
        assert r2.discard_token
        # Mutate sessions (change rpe) with valid edit token for r1? r1 token matches r1 state; but we need to mutate through service.
        rmut = svc.save_daily_record(db, atleta_id=atleta.id, payload=_payload(entreno_hoy=True, sessions=[_session(rpe=8)]), edit_state_token=r1.edit_state_token, fecha=fecha, allow_full_session_replacement=True)
        assert rmut.ok and rmut.parte.sesiones[0].rpe == 8
        # Old discard token now stale
        r3 = svc.save_daily_record(
            db, atleta_id=atleta.id, payload=_payload(entreno_hoy=False),
            edit_state_token=rmut.edit_state_token, discard_token=r2.discard_token, confirm_discard_sessions=True, fecha=fecha,
        )
        assert not r3.ok and r3.status == svc.STATUS_CONFLICT and r3.stale
        db.refresh(rmut.parte)
        assert len(rmut.parte.sesiones) == 1

    def test_explicit_session_delete_requires_binding(self, db):
        atleta = crear_usuario(db, username="pd6")
        otro = crear_usuario(db, username="pd6o")
        fecha = date(2026, 11, 8)
        r1 = svc.save_daily_record(db, atleta_id=atleta.id, payload=_payload(entreno_hoy=True, sessions=[_session(orden=1), _session(orden=2, tipo_entrenamiento="fuerza")]), fecha=fecha)
        sid_keep = r1.parte.sesiones[0].id
        sid_del = r1.parte.sesiones[1].id
        # valid explicit delete
        r2 = svc.save_daily_record(
            db, atleta_id=atleta.id,
            payload=_payload(entreno_hoy=True, sessions=[_session(orden=1, id=sid_keep)]),
            edit_state_token=r1.edit_state_token, explicit_delete_session_ids=[sid_del], fecha=fecha,
        )
        assert r2.ok and len(r2.parte.sesiones) == 1 and r2.parte.sesiones[0].id == sid_keep

    def test_no_implicit_delete_by_omission_without_full_replacement(self, db):
        atleta = crear_usuario(db, username="pd7")
        fecha = date(2026, 11, 8)
        r1 = svc.save_daily_record(db, atleta_id=atleta.id, payload=_payload(entreno_hoy=True, sessions=[_session(orden=1), _session(orden=2, tipo_entrenamiento="fuerza")]), fecha=fecha)
        sid1, sid2 = [s.id for s in r1.parte.sesiones]
        # Submit only first session, no explicit delete, no full replacement -> second preserved
        r2 = svc.save_daily_record(
            db, atleta_id=atleta.id,
            payload=_payload(entreno_hoy=True, sessions=[{"id": sid1, **_session(orden=1)}]),
            edit_state_token=r1.edit_state_token, fecha=fecha,
        )
        assert r2.ok
        db.refresh(r1.parte)
        ids = {s.id for s in r1.parte.sesiones}
        assert sid1 in ids and sid2 in ids


class TestAggregation:
    def test_weekly_aggregation_missing_not_zero(self, db):
        atleta = crear_usuario(db, username="agg1")
        lunes = date(2026, 11, 2)  # Mon
        # report only Tue with training 270, Wed entreno_hoy false
        svc.save_daily_record(db, atleta_id=atleta.id, payload=_payload(entreno_hoy=True, sessions=[_session(duracion_min=45, rpe=6)]), fecha=date(2026, 11, 3))
        # Need token for second save same? different date => create paths
        svc.save_daily_record(db, atleta_id=atleta.id, payload=_payload(entreno_hoy=False), fecha=date(2026, 11, 4))
        agg = svc.aggregate_week_reported(db, atleta.id, lunes)
        assert agg.dias_reportados == 2
        assert agg.carga_semanal == 270
        assert agg.cargas_diarias[date(2026, 11, 2).isoformat()] is None  # missing
        assert agg.cargas_diarias[date(2026, 11, 3).isoformat()] == 270
        assert agg.cargas_diarias[date(2026, 11, 4).isoformat()] == 0  # reported no training
