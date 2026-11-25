"""Aggregate behavior on independently verified disposable PostgreSQL."""
from datetime import date, timedelta
import pytest
from app.models import ParteDiaria, SesionEntrenamiento
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
