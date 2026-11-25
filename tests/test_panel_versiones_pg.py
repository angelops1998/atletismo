"""Aggregate behavior on independently verified disposable PostgreSQL."""
from datetime import date, timedelta
import pytest
from app.models import ParteDiaria, SesionEntrenamiento, User
from app.routers.estadisticas import _serie_con_cortes
from app.services.grafico import linea
from app.services import seguimiento_diario as sd
from test_parte_diaria_concurrency_pg import pg_engine, pg_session_factory, tracked, _create_user


@pytest.mark.pg
def test_pg_mixed_versions_and_duration_groups(pg_session_factory, tracked):
    athlete_id = _create_user(pg_session_factory, "panelmixed", tracked)
    day = date(2026, 11, 20)
    with pg_session_factory() as db:
        legacy = ParteDiaria(atleta_id=athlete_id, fecha=day, sueno_calidad=10, fatiga=9,
            dolor_muscular=8, estres=7, animo=6, horas_sueno=8, entreno_hoy=True)
        mclean = ParteDiaria(atleta_id=athlete_id, fecha=day + timedelta(days=1),
            version_cuestionario="mclean_1_5", mclean_sueno=1, mclean_fatiga=2,
            mclean_dolor_muscular=3, mclean_estres=4, mclean_animo=5, horas_sueno=8, entreno_hoy=True)
        legacy.sesiones.append(SesionEntrenamiento(orden=1, tipo_entrenamiento="fuerza",
            duracion_min=40, rpe=5, carga_sesion=999, tipo_duracion="no_especificada"))
        mclean.sesiones.append(SesionEntrenamiento(orden=1, tipo_entrenamiento="fuerza",
            duracion_min=30, rpe=5, carga_sesion=150, tipo_duracion="trabajo_principal"))
        db.add_all([legacy, mclean]); db.commit()
        tracked.track_parte(legacy); tracked.track_parte(mclean)
        summary = sd.resumen_diario_atleta(db, athlete_id)
        assert summary["series"]["sueno_calidad"] == [10.0, None]
        assert summary["series"]["mclean_sueno"] == [None, 1.0]
        assert summary["promedios"]["mclean_suma"] == 15
        groups = summary["sesiones"]["por_tipo"]
        assert (groups["no_especificada"]["minutos"], groups["no_especificada"]["carga"]) == (40, 999)
        assert (groups["trabajo_principal"]["minutos"], groups["trabajo_principal"]["carga"]) == (30, 150)


@pytest.mark.pg
def test_pg_resumen_reportes_periodo_mixto_y_cortes(pg_session_factory, tracked):
    athlete_id = _create_user(pg_session_factory, "agregado_mixto", tracked)
    second_id = _create_user(pg_session_factory, "agregado_mclean", tracked)
    day = date(2026, 11, 1)
    with pg_session_factory() as db:
        old = ParteDiaria(atleta_id=athlete_id, fecha=day, sueno_calidad=10, fatiga=9,
            dolor_muscular=8, estres=7, animo=6, horas_sueno=8, entreno_hoy=True)
        new = ParteDiaria(atleta_id=second_id, fecha=day, version_cuestionario="mclean_1_5",
            mclean_sueno=1, mclean_fatiga=2, mclean_dolor_muscular=3, mclean_estres=4,
            mclean_animo=5, horas_sueno=7, entreno_hoy=True)
        later = ParteDiaria(atleta_id=second_id, fecha=day + timedelta(days=2), version_cuestionario="mclean_1_5",
            mclean_sueno=3, mclean_fatiga=3, mclean_dolor_muscular=3, mclean_estres=3,
            mclean_animo=3, horas_sueno=8, entreno_hoy=False)
        old.sesiones.append(SesionEntrenamiento(orden=1, tipo_entrenamiento="resistencia",
            duracion_min=40, rpe=5, carga_sesion=999, tipo_duracion="no_especificada"))
        new.sesiones.append(SesionEntrenamiento(orden=1, tipo_entrenamiento="fuerza",
            duracion_min=30, rpe=5, carga_sesion=150, tipo_duracion="trabajo_principal"))
        db.add_all([old, new, later]); db.commit()
        for parte in (old, new, later):
            tracked.track_parte(parte)
        athletes = db.query(User).filter(User.id.in_([athlete_id, second_id])).all()
        rows = sd.reportes_del_periodo(db, day, day + timedelta(days=2), [athlete_id, second_id])
        summary = sd.resumen_reportes(rows, athletes, day, day + timedelta(days=2))
        assert summary["total_reportes"] == 3
        assert summary["promedios"]["sueno_calidad"] == 10
        assert summary["promedios_mclean"]["mclean_sueno"] == 2
        assert summary["promedios_mclean"]["suma"] == 15
        assert summary["promedios_mclean"]["promedio"] == 3
        assert summary["distribuciones"]["sueno_calidad"][10] == 1
        assert summary["distribuciones_mclean"]["mclean_sueno"][1] == 1
        assert summary["tendencia"][0]["sueno_calidad"] == 10
        assert summary["tendencia"][0]["mclean_sueno"] == 1
        series = _serie_con_cortes(summary["tendencia"], "mclean_sueno")
        assert series == [1.0, None, 3.0]
        assert linea(series)["segmentos"] == []
        groups = summary["sesiones"]["por_tipo"]
        assert (groups["no_especificada"]["minutos"], groups["no_especificada"]["carga"]) == (40, 999)
        assert (groups["trabajo_principal"]["minutos"], groups["trabajo_principal"]["carga"]) == (30, 150)
        assert summary["sesiones"]["tipos_realizados"]["fuerza"] == 1
        db.expire_all()
        assert db.query(SesionEntrenamiento).filter_by(id=old.sesiones[0].id).one().carga_sesion == 999
