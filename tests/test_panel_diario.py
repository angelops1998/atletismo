from datetime import date, timedelta
from decimal import Decimal
import re

from app.models.entrenamiento_principal import EntrenamientoPrincipal
from app.models.parte_diaria import ParteDiaria
from app.models.sesion_entrenamiento import SesionEntrenamiento
from conftest import crear_parte, crear_usuario, entrar


def crear_reporte(db, atleta_id, dia, **campos):
    valores = {
        "sueno_calidad": 8, "fatiga": 3, "dolor_muscular": 2,
        "estres": 4, "animo": 9, "horas_sueno": Decimal("7.5"),
        "hay_molestia": False, "sintomas_enfermedad": False,
        "entreno_hoy": True,
    }
    valores.update(campos)
    parte = ParteDiaria(atleta_id=atleta_id, fecha=dia, **valores)
    db.add(parte)
    db.flush()
    return parte


def agregar_estructura(db, parte, **campos):
    valores = {
        "estructura_tipo": "aerobico", "series": 3,
        "repeticiones_por_serie": 4, "distancia_m": 400,
        "descanso_micro_min_s": 30, "descanso_micro_max_s": 60,
        "descanso_macro_min_s": 180, "descanso_macro_max_s": 300,
        "tiempo_rep_min_s": 100, "tiempo_rep_max_s": 120,
    }
    valores.update(campos)
    estructura = EntrenamientoPrincipal(parte_diaria_id=parte.id, **valores)
    db.add(estructura)
    return estructura


def test_panel_cuenta_partes_diarios_de_la_fecha_y_no_partes_semanales(client, db):
    profe = crear_usuario(db, username="profe", role="profesor")
    uno = crear_usuario(db, username="uno", full_name="Atleta Uno")
    dos = crear_usuario(db, username="dos", full_name="Atleta Dos")
    dia = date(2026, 11, 14)
    crear_parte(db, dos.id, date(2026, 11, 9))
    crear_reporte(db, uno.id, dia, entreno_hoy=False)
    db.commit()
    entrar(client, profe)

    response = client.get("/panel", params={"fecha": dia.isoformat()})
    assert response.status_code == 200
    assert "1/2" in response.text
    assert "Sin parte diario para 14/11/26" in response.text
    assert "Atleta Uno" in response.text and "Atleta Dos" in response.text
    assert "No entrenó" in response.text


def test_dashboard_muestra_detalle_de_molestia_sintomas_y_link_al_perfil(client, db):
    profe = crear_usuario(db, username="profe", role="profesor")
    atleta = crear_usuario(db, username="atleta", full_name="Corredor")
    dia = date(2026, 11, 14)
    crear_reporte(db, atleta.id, dia, hay_molestia=True,
                  molestia_zona=["rodillas", "otro"], molestia_zona_otra="tendón",
                  molestia_dolor=7, afecta_entrenamiento=2,
                  sintomas_enfermedad=True, detalle_sintomas="Tos",
                  comentarios="Avisé al entrenador")
    db.commit()
    entrar(client, profe)

    response = client.get("/panel", params={"fecha": dia.isoformat()})
    assert response.status_code == 200
    for fragment in ("rodillas", "tendón", "7/10", "Impacto en el entrenamiento",
                     "Tos", "Avisé al entrenador", "/atletas/"):
        assert fragment in response.text


def test_roster_usa_estado_diario_y_mantiene_estado_financiero(client, db):
    profe = crear_usuario(db, username="profe", role="profesor")
    uno = crear_usuario(db, username="uno", full_name="Atleta Uno")
    dos = crear_usuario(db, username="dos", full_name="Atleta Dos")
    dia = date(2026, 11, 14)
    crear_parte(db, dos.id, date(2026, 11, 9))
    crear_reporte(db, uno.id, dia, sueno_calidad=10, fatiga=1,
                  hay_molestia=True, molestia_zona=["pantorrillas"],
                  molestia_dolor=5, sintomas_enfermedad=True)
    db.commit()
    entrar(client, profe)

    response = client.get("/atletas", params={"fecha": dia.isoformat()})
    assert response.status_code == 200
    assert "Sueño 10/10" in response.text
    assert "Fatiga 1/10" in response.text
    assert "Molestia · 5/10 · pantorrillas" in response.text
    assert "Síntomas declarados" in response.text
    assert "Sin parte para 14/11/26" in response.text


def test_ficha_muestra_estructura_completa_sesiones_y_orden_diario(client, db):
    profe = crear_usuario(db, username="profe", role="profesor")
    atleta = crear_usuario(db, username="atleta", full_name="Corredor")
    anterior = crear_reporte(db, atleta.id, date(2026, 11, 13), entreno_hoy=False)
    actual = crear_reporte(db, atleta.id, date(2026, 11, 14),
                           hay_molestia=True, molestia_zona=["rodillas"],
                           molestia_dolor=6, afecta_entrenamiento=1,
                           sintomas_enfermedad=True, detalle_sintomas="Congestión",
                           comentarios="Molestia al final")
    agregar_estructura(db, actual, estructura_tipo="velocidad", series=4,
                       repeticiones_por_serie=3, distancia_m=100,
                       descanso_micro_min_s=45, descanso_micro_max_s=60,
                       descanso_macro_min_s=240, descanso_macro_max_s=360,
                       tiempo_rep_min_s=12, tiempo_rep_max_s=15)
    db.add(SesionEntrenamiento(parte_diaria_id=actual.id, orden=1,
                               tipo_entrenamiento="velocidad_sprint", duracion_min=45,
                               rpe=7, carga_sesion=315,
                               comentarios_entrenamiento="Series de pista"))
    db.commit()
    entrar(client, profe)

    response = client.get(f"/atletas/{atleta.id}")
    assert response.status_code == 200
    text = response.text
    assert 'id="reporte-' in text
    for fragment in ("14 de noviembre de 2026", "Calidad del sueño", "Ánimo:",
                     "Velocidad", "4 × 3 (12 repeticiones)", "100 m",
                     "00:45–01:00", "04:00–06:00", "00:12–00:15",
                     "Sesión 1 · Velocidad sprint", "45 min · RPE 7/10 · carga almacenada 315",
                     "Series de pista", "Congestión", "Molestia al final", "No entrenó"):
        assert fragment in text
    tabla = re.search(r'<table class="tabla-historial-diario".*?</table>', text, re.S)
    assert tabla
    assert tabla.group(0).index("14/11/26") < tabla.group(0).index("13/11/26")


def test_ficha_muestra_estructura_sin_sesiones_y_no_inventa_entrenamiento(client, db):
    profe = crear_usuario(db, username="profe", role="profesor")
    atleta = crear_usuario(db, username="atleta")
    con_entreno = crear_reporte(db, atleta.id, date(2026, 11, 14))
    agregar_estructura(db, con_entreno)
    crear_reporte(db, atleta.id, date(2026, 11, 13), entreno_hoy=False)
    db.commit()
    entrar(client, profe)

    response = client.get(f"/atletas/{atleta.id}")
    assert response.status_code == 200
    assert "3 × 4 (12 repeticiones)" in response.text
    assert "No hay sesiones individuales registradas para este parte" in response.text
    assert "El atleta indicó que no entrenó. No se registra una estructura principal" in response.text
    assert "13 de noviembre de 2026" in response.text


def test_ficha_filtra_historial_por_fecha_y_pagina(client, db):
    profe = crear_usuario(db, username="profe", role="profesor")
    atleta = crear_usuario(db, username="atleta")
    crear_reporte(db, atleta.id, date(2026, 11, 12))
    crear_reporte(db, atleta.id, date(2026, 11, 13))
    crear_reporte(db, atleta.id, date(2026, 11, 14))
    db.commit()
    entrar(client, profe)

    response = client.get(f"/atletas/{atleta.id}", params={
        "desde": "2026-11-13", "hasta": "2026-11-13", "pagina": "1",
    })
    assert response.status_code == 200
    assert "13 de noviembre de 2026" in response.text
    assert "12 de noviembre de 2026" not in response.text
    assert "14 de noviembre de 2026" not in response.text
    assert "1 partes en el período seleccionado" in response.text
    assert "escala 1–10" in response.text


def test_ficha_tabla_graficos_y_kpis_son_diarios_y_conserva_secciones_admin(client, db):
    profe = crear_usuario(db, username="profe", role="profesor")
    atleta = crear_usuario(db, username="atleta", full_name="Corredora")
    primero = crear_reporte(db, atleta.id, date(2026, 11, 12),
                            sueno_calidad=6, fatiga=2, dolor_muscular=3,
                            estres=4, animo=10, horas_sueno=Decimal("6.0"),
                            entreno_hoy=True)
    agregar_estructura(db, primero)
    db.add(SesionEntrenamiento(parte_diaria_id=primero.id, orden=1,
                               tipo_entrenamiento="resistencia", duracion_min=45,
                               rpe=6, carga_sesion=270))
    segundo = crear_reporte(db, atleta.id, date(2026, 11, 14),
                            sueno_calidad=10, fatiga=6, dolor_muscular=7,
                            estres=8, animo=6, horas_sueno=Decimal("10.0"),
                            entreno_hoy=False, hay_molestia=True,
                            sintomas_enfermedad=True)
    db.add(SesionEntrenamiento(parte_diaria_id=segundo.id, orden=1,
                               tipo_entrenamiento="movilidad_recuperacion", duracion_min=30,
                               rpe=4, carga_sesion=120))
    db.commit()
    entrar(client, profe)

    response = client.get(f"/atletas/{atleta.id}")
    assert response.status_code == 200
    text = response.text
    for fragment in ("Resumen diario", "Evolución diaria", "Historial diario",
                     "Calidad del sueño", "Fatiga", "Dolor muscular", "Estrés", "Ánimo",
                     "Horas de sueño", "2 partes en el período seleccionado",
                     "8.0", "4.0", "5.0", "8.0", "8.0", "1 / 1",
                     "1 sesiones", "45 min guardados", "RPE promedio 6.0",
                     "carga almacenada total 270", "30 min guardados",
                     "carga almacenada total 120", "tabla-historial-diario",
                     "12/11/26", "14/11/26", "No entrenó", "Marcas",
                     "Cuota y pagos", "Asistencia", "Ficha"):
        assert fragment in text
    for obsolete in ("Histórico semanal", "Partes semanales", "Carga de entrenamiento semanal",
                     "Ratio de carga semanal", "Bienestar histórico"):
        assert obsolete not in text
    assert text.index("12/11/26") < text.index("14/11/26")


def test_ficha_resumen_vacio_no_presenta_ceros_como_observaciones(client, db):
    profe = crear_usuario(db, username="profe", role="profesor")
    atleta = crear_usuario(db, username="atleta")
    entrar(client, profe)

    response = client.get(f"/atletas/{atleta.id}")
    assert response.status_code == 200
    assert "0 partes en el período seleccionado" in response.text
    assert "Todavía no hay partes diarios para resumir" in response.text
    assert "No hay observaciones diarias para graficar" in response.text
    assert "—</div><div class=\"etiqueta\">Calidad del sueño" in response.text
    assert "—</div><div class=\"etiqueta\">Molestias declaradas" in response.text
    assert "No hay sesiones individuales en este período" in response.text
    assert "Partes semanales" not in response.text


def test_servicio_genera_series_diarias_cronologicas_con_cortes(client, db):
    atleta = crear_usuario(db, username="atleta")
    fechas = [date(2026, 11, 10), date(2026, 11, 11),
              date(2026, 11, 14), date(2026, 11, 15)]
    for indice, dia in enumerate(fechas, start=1):
        crear_reporte(db, atleta.id, dia, fatiga=indice)
    db.commit()

    from app.services.seguimiento_diario import resumen_diario_atleta
    resumen = resumen_diario_atleta(db, atleta.id,
                                    desde=fechas[0], hasta=fechas[-1])
    assert resumen["observaciones"][0]["fecha"] == fechas[0]
    assert resumen["observaciones"][-1]["fecha"] == fechas[-1]
    assert resumen["series"]["fatiga"] == [1.0, 2.0, None, 3.0, 4.0]
    assert resumen["promedios"]["fatiga"] == 2.5
    from app.services.grafico import linea
    grafico = linea(resumen["series"]["fatiga"], minimo=1, maximo=10)
    assert grafico["puntos"][2] is None
    assert len(grafico["segmentos"]) == 2


def test_paginacion_de_tabla_mantiene_filtros_de_fecha(client, db):
    profe = crear_usuario(db, username="profe", role="profesor")
    atleta = crear_usuario(db, username="atleta")
    inicio = date(2026, 10, 26)
    for indice in range(21):
        crear_reporte(db, atleta.id, inicio + timedelta(days=indice))
    db.commit()
    entrar(client, profe)

    response = client.get(f"/atletas/{atleta.id}", params={
        "desde": inicio.isoformat(), "hasta": (inicio + timedelta(days=20)).isoformat(),
    })
    assert response.status_code == 200
    assert "Página 1 de 2" in response.text
    assert f"?pagina=2&desde={inicio.isoformat()}&hasta=" in response.text
    primera_tabla = re.search(r'<table class="tabla-historial-diario".*?</table>', response.text, re.S)
    assert primera_tabla and "26/10/26" not in primera_tabla.group(0)
    segunda = client.get(f"/atletas/{atleta.id}", params={
        "pagina": 2, "desde": inicio.isoformat(),
        "hasta": (inicio + timedelta(days=20)).isoformat(),
    })
    assert segunda.status_code == 200
    assert "Página 2 de 2" in segunda.text
    tabla = re.search(r'<table class="tabla-historial-diario".*?</table>', segunda.text, re.S)
    assert tabla and "26/10/26" in tabla.group(0)


def test_otras_vistas_docentes_siguen_sin_presentacion_semanal(client, db):
    profe = crear_usuario(db, username="profe", role="profesor")
    crear_usuario(db, username="atleta")
    entrar(client, profe)
    for ruta in ("/panel", "/atletas", "/estadisticas"):
        response = client.get(ruta)
        assert response.status_code == 200
        assert "Parte semanal" not in response.text
        assert "bienestar de la semana" not in response.text.lower()


def test_costo_de_ficha_no_crece_por_cada_parte_diario(client, db, contar_consultas):
    profe = crear_usuario(db, username="profe", role="profesor")
    atleta = crear_usuario(db, username="atleta")
    entrar(client, profe)
    inicio = date(2026, 1, 1)
    for indice in range(5):
        crear_reporte(db, atleta.id, inicio + timedelta(days=indice))
    db.commit()
    with contar_consultas() as pocas:
        assert client.get(f"/atletas/{atleta.id}").status_code == 200

    for indice in range(5, 30):
        crear_reporte(db, atleta.id, inicio + timedelta(days=indice))
    db.commit()
    with contar_consultas() as muchas:
        assert client.get(f"/atletas/{atleta.id}").status_code == 200
    assert muchas.total == pocas.total


def test_estadisticas_filtra_fechas_y_agrega_solo_reportes_diarios(client, db):
    profe = crear_usuario(db, username="profe", role="profesor")
    uno = crear_usuario(db, username="uno", full_name="Atleta Uno")
    dos = crear_usuario(db, username="dos", full_name="Atleta Dos")
    dia = date(2026, 11, 14)
    crear_parte(db, dos.id, date(2026, 11, 9), animo=1)
    actual = crear_reporte(db, uno.id, dia, sueno_calidad=10, fatiga=8,
                           dolor_muscular=6, estres=4, animo=9,
                           horas_sueno=Decimal("8.0"), hay_molestia=True,
                           molestia_zona=["rodillas"], sintomas_enfermedad=True)
    agregar_estructura(db, actual)
    db.add(SesionEntrenamiento(parte_diaria_id=actual.id, orden=1,
                               tipo_entrenamiento="resistencia", duracion_min=45,
                               rpe=7, carga_sesion=315))
    db.commit()
    entrar(client, profe)

    response = client.get("/estadisticas", params={"desde": dia.isoformat(), "hasta": dia.isoformat()})
    assert response.status_code == 200
    text = response.text
    assert "1 / 2 oportunidades" in text
    assert "50.0%" in text
    assert "8.0" in text and "1–10" in text
    assert "10: 1" in text
    assert "rodillas" in text
    assert "Aeróbico" in text
    assert "RPE promedio 7.0" in text
    assert "315" in text
    assert "Carga guardada" in text
    assert "No constituyen una evaluación médica" in text
    assert "Atleta Uno" in text and "Atleta Dos" in text
    assert "10" in text and "8" in text


def test_filtros_diarios_rechazan_fechas_invalidas_y_periodos_invertidos(client, db):
    profe = crear_usuario(db, username="profe", role="profesor")
    atleta = crear_usuario(db, username="atleta")
    entrar(client, profe)
    assert client.get("/panel", params={"fecha": "no-es-fecha"}).status_code == 422
    assert client.get("/atletas", params={"fecha": "2026-2-1"}).status_code == 422
    assert client.get(f"/atletas/{atleta.id}", params={"pagina": "-1"}).status_code == 422
    assert client.get("/estadisticas", params={"desde": "2026-11-15", "hasta": "2026-11-14"}).status_code == 422


def test_atleta_no_accede_a_estadisticas_ni_a_ficha_ajena(client, db):
    atleta = crear_usuario(db, username="atleta")
    otro = crear_usuario(db, username="otro")
    entrar(client, atleta)
    assert client.get("/estadisticas").status_code in (302, 403)
    assert client.get(f"/atletas/{otro.id}").status_code in (302, 403)
