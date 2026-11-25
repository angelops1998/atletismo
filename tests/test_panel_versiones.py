"""Segregación de bienestar y duración en vistas docentes, con SQLite en memoria."""
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.models import ParteDiaria, SesionEntrenamiento
from app.services import seguimiento_diario as sd
from conftest import crear_usuario, entrar

DIA = date(2026, 11, 20)


def parte(db, atleta, dia, mclean=False):
    p = ParteDiaria(atleta_id=atleta.id, fecha=dia, horas_sueno=Decimal("8.0"),
        entreno_hoy=True, hay_molestia=False, sintomas_enfermedad=False,
        **({"version_cuestionario": "mclean_1_5", "mclean_sueno": 1, "mclean_fatiga": 2,
            "mclean_dolor_muscular": 3, "mclean_estres": 4, "mclean_animo": 5}
           if mclean else {"sueno_calidad": 10, "fatiga": 9, "dolor_muscular": 8, "estres": 7, "animo": 6}))
    db.add(p); db.flush()
    return p


def sesion(db, p, tipo, duracion, carga):
    db.add(SesionEntrenamiento(parte_diaria_id=p.id, orden=1, tipo_entrenamiento="fuerza",
           tipo_duracion=tipo, duracion_min=duracion, rpe=5, carga_sesion=carga))
    db.flush()


def test_mixed_periods_separate_versions_and_recorded_loads(db):
    athlete = crear_usuario(db, username="mixto")
    old = parte(db, athlete, DIA)
    new = parte(db, athlete, DIA + timedelta(days=1), mclean=True)
    later = parte(db, athlete, DIA + timedelta(days=2))
    sesion(db, old, "no_especificada", 40, 999)
    sesion(db, new, "trabajo_principal", 30, 150)
    db.commit()
    before = [(x.id, x.carga_sesion, x.tipo_duracion) for x in db.query(SesionEntrenamiento).order_by(SesionEntrenamiento.id)]
    individual = sd.resumen_diario_atleta(db, athlete.id)
    assert individual["promedios"]["sueno_calidad"] == 10
    assert individual["promedios"]["mclean_sueno"] == 1
    assert individual["promedios"]["mclean_suma"] == 15 and individual["promedios"]["mclean_promedio"] == 3
    assert individual["series"]["sueno_calidad"] == [10.0, None, 10.0]
    assert individual["series"]["mclean_sueno"] == [None, 1.0, None]
    from app.services.grafico import linea
    assert linea(individual["series"]["sueno_calidad"], minimo=1, maximo=10)["segmentos"] == []
    groups = individual["sesiones"]["por_tipo"]
    assert (groups["no_especificada"]["minutos"], groups["no_especificada"]["carga"]) == (40, 999)
    assert (groups["trabajo_principal"]["minutos"], groups["trabajo_principal"]["carga"]) == (30, 150)
    summary = sd.resumen_reportes([old, new, later], [athlete], DIA, DIA + timedelta(days=2))
    assert summary["promedios"]["sueno_calidad"] == 10
    assert summary["promedios_mclean"]["mclean_sueno"] == 1
    assert summary["promedios_mclean"]["suma"] == 15 and summary["promedios_mclean"]["promedio"] == 3
    assert summary["tendencia"][0]["mclean_sueno"] is None and summary["tendencia"][1]["sueno_calidad"] is None
    assert summary["sesiones"]["por_tipo"]["no_especificada"]["carga"] == 999
    assert summary["sesiones"]["por_tipo"]["trabajo_principal"]["carga"] == 150
    after = [(x.id, x.carga_sesion, x.tipo_duracion) for x in db.query(SesionEntrenamiento).order_by(SesionEntrenamiento.id)]
    assert before == after


def test_same_day_mixed_group_averages_are_separate(db):
    a = crear_usuario(db, username="mclean_athlete")
    b = crear_usuario(db, username="legacy_athlete")
    m = parte(db, a, DIA, mclean=True)
    h = parte(db, b, DIA)
    db.commit()
    summary = sd.resumen_reportes([m, h], [a, b], DIA, DIA)
    assert summary["tendencia"][0]["sueno_calidad"] == 10
    assert summary["tendencia"][0]["mclean_sueno"] == 1
    assert summary["distribuciones"]["sueno_calidad"][10] == 1
    assert summary["distribuciones_mclean"]["mclean_sueno"][1] == 1
    assert summary["filas_atletas"][0]["sesiones_por_tipo"]["trabajo_principal"]["cantidad"] == 0


def test_teacher_views_show_mclean_history_and_separate_durations(client, db):
    teacher = crear_usuario(db, username="profe_mixto", role="profesor")
    athlete = crear_usuario(db, username="atleta_mixto")
    historic = parte(db, athlete, DIA)
    mclean = parte(db, athlete, DIA + timedelta(days=1), mclean=True)
    sesion(db, historic, "no_especificada", 40, 999)
    sesion(db, mclean, "trabajo_principal", 30, 150)
    db.commit()
    entrar(client, teacher)
    ficha = client.get(f"/atletas/{athlete.id}")
    assert ficha.status_code == 200
    for label in ("Histórico 1–10", "McLean 1–5", "Sueño 1/5", "Fatiga 2/5",
                  "Dolor muscular 3/5", "Estrés 4/5", "Ánimo 5/5", "Suma 15/25", "Promedio 3.0/5",
                  "Duración no especificada", "Trabajo principal", "carga almacenada 999", "carga almacenada 150"):
        assert label in ficha.text
    assert "None/10" not in ficha.text
    stats = client.get("/estadisticas", params={"desde": DIA.isoformat(), "hasta": (DIA + timedelta(days=1)).isoformat()})
    assert stats.status_code == 200
    for label in ("Bienestar histórico promedio", "Bienestar McLean", "Suma promedio (5–25)",
                  "Duración no especificada: 1 sesiones · 40 minutos", "Trabajo principal: 1 sesiones · 30 minutos",
                  "carga almacenada total 999", "carga almacenada total 150", "Sueño McLean 1–5"):
        assert label in stats.text
    assert "70 minutos" not in stats.text and "carga almacenada total 1149" not in stats.text
    panel = client.get("/panel", params={"fecha": (DIA + timedelta(days=1)).isoformat()})
    lista = client.get("/atletas", params={"fecha": (DIA + timedelta(days=1)).isoformat()})
    assert panel.status_code == lista.status_code == 200
    assert "McLean 1–5" in panel.text and "Suma 15/25" in panel.text
    assert "McLean 1–5" in lista.text and "Sueño 1/5" in lista.text and "None/10" not in lista.text
    db.expire_all()
    assert db.query(SesionEntrenamiento).filter_by(tipo_duracion="no_especificada").one().carga_sesion == 999
    assert db.query(ParteDiaria).filter_by(version_cuestionario="mclean_1_5").one().mclean_animo == 5


@pytest.mark.parametrize("path", ["/panel", "/estadisticas", "/atletas", "/atletas/{id}"])
def test_athlete_cannot_read_teacher_views(client, db, path):
    a = crear_usuario(db, username="sin_permiso")
    entrar(client, a)
    response = client.get(path.format(id=a.id))
    assert response.status_code == 403
