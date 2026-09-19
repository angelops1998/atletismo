"""Las reglas que convierten los partes en avisos accionables.

Es el módulo cuyos umbrales están pensados para ajustarse después de usar el
sistema unos meses. Estos tests fijan lo que cada regla significa hoy: cuando se
mueva un umbral, tiene que verse acá qué cambió y no descubrirse en el panel.
"""
from decimal import Decimal

from app.services import alertas, bienestar
from conftest import crear_parte, crear_usuario, semana


def tipos(lista):
    return {a["tipo"] for a in lista}


def buscar(lista, tipo):
    return next((a for a in lista if a["tipo"] == tipo), None)


class TestACWR:
    """Carga de la última semana contra el promedio de las anteriores. Es el
    indicador que anticipa la lesión por sobrecarga."""

    def _serie(self, cargas):
        return [{"carga": c} for c in cargas]

    def test_carga_estable_da_uno(self):
        assert alertas.acwr(self._serie([1000, 1000, 1000, 1000, 1000])) == 1.0

    def test_el_doble_de_lo_habitual(self):
        assert alertas.acwr(self._serie([1000, 1000, 1000, 1000, 2000])) == 2.0

    def test_sin_carga_esta_semana_no_hay_ratio(self):
        assert alertas.acwr(self._serie([1000, 1000, None])) is None

    def test_con_menos_de_dos_semanas_previas_no_alcanza(self):
        """Con una sola semana de referencia el ratio es puro ruido."""
        assert alertas.acwr(self._serie([1000, 2000])) is None

    def test_serie_vacia(self):
        assert alertas.acwr([]) is None

    def test_no_divide_por_cero_si_las_previas_son_cero(self):
        assert alertas.acwr(self._serie([0, 0, 0, 1500])) is None


class TestReglasDelAtleta:
    def test_sin_parte_avisa(self, db):
        atleta = crear_usuario(db)
        assert "sin_parte" in tipos(alertas.del_atleta(db, atleta))

    def test_con_el_parte_cargado_no_avisa(self, db):
        atleta = crear_usuario(db)
        crear_parte(db, atleta.id, semana(0))
        assert "sin_parte" not in tipos(alertas.del_atleta(db, atleta))

    def test_bienestar_bajo(self, db):
        atleta = crear_usuario(db)
        crear_parte(db, atleta.id, semana(0), sueno_calidad=2,
                    dolor_muscular=3, estres=3, animo=2)          # 10
        aviso = buscar(alertas.del_atleta(db, atleta), "bienestar_bajo")
        assert aviso and aviso["nivel"] == "alta"

    def test_un_item_en_el_minimo(self, db):
        atleta = crear_usuario(db)
        crear_parte(db, atleta.id, semana(0), animo=1)
        aviso = buscar(alertas.del_atleta(db, atleta), "item_minimo")
        assert aviso and "ánimo" in aviso["detalle"]

    def test_caida_contra_sus_propias_semanas(self, db):
        """La comparación es contra él mismo. Un atleta que venía en 20 y cae a
        15 tiene que saltar, aunque 15 sea un buen número para el club."""
        atleta = crear_usuario(db)
        for atras in (3, 2, 1):
            crear_parte(db, atleta.id, semana(atras), sueno_calidad=5,
                        dolor_muscular=5, estres=5, animo=5)      # 20
        crear_parte(db, atleta.id, semana(0), sueno_calidad=4,
                    dolor_muscular=4, estres=4, animo=3)          # 15 (-25%)
        aviso = buscar(alertas.del_atleta(db, atleta), "caida_bienestar")
        assert aviso and aviso["nivel"] == "alta"

    def test_el_que_siempre_puntua_bajo_no_salta_por_eso(self, db):
        """Es la razón de comparar contra uno mismo: un atleta constante en 12 no
        empeoró, y contra el promedio del club se lo vería siempre en rojo."""
        atleta = crear_usuario(db)
        for atras in (3, 2, 1, 0):
            crear_parte(db, atleta.id, semana(atras), sueno_calidad=3,
                        dolor_muscular=3, estres=3, animo=3)      # 12 siempre
        assert "caida_bienestar" not in tipos(alertas.del_atleta(db, atleta))

    def test_molestia_con_dolor_alto_es_prioridad_alta(self, db):
        atleta = crear_usuario(db)
        crear_parte(db, atleta.id, semana(0), molestias=True,
                    molestia_zona="isquiotibial", molestia_dolor=8)
        aviso = buscar(alertas.del_atleta(db, atleta), "molestia")
        assert aviso["nivel"] == "alta"
        assert "isquiotibial" in aviso["detalle"] and "8/10" in aviso["detalle"]

    def test_molestia_leve_es_prioridad_media(self, db):
        atleta = crear_usuario(db)
        crear_parte(db, atleta.id, semana(0), molestias=True,
                    molestia_zona="gemelo", molestia_dolor=3)
        assert buscar(alertas.del_atleta(db, atleta), "molestia")["nivel"] == "media"

    def test_duerme_poco_dos_semanas_seguidas(self, db):
        atleta = crear_usuario(db)
        crear_parte(db, atleta.id, semana(1), horas_sueno=Decimal("6.0"))
        crear_parte(db, atleta.id, semana(0), horas_sueno=Decimal("6.5"))
        assert "sueno_insuficiente" in tipos(alertas.del_atleta(db, atleta))

    def test_una_sola_mala_noche_no_avisa(self, db):
        atleta = crear_usuario(db)
        crear_parte(db, atleta.id, semana(1), horas_sueno=Decimal("8.0"))
        crear_parte(db, atleta.id, semana(0), horas_sueno=Decimal("6.0"))
        assert "sueno_insuficiente" not in tipos(alertas.del_atleta(db, atleta))

    def test_salto_de_carga(self, db):
        atleta = crear_usuario(db)
        for atras in (4, 3, 2, 1):
            crear_parte(db, atleta.id, semana(atras), rpe=5, minutos_totales=200)
        crear_parte(db, atleta.id, semana(0), rpe=8, minutos_totales=400)
        aviso = buscar(alertas.del_atleta(db, atleta), "salto_de_carga")
        assert aviso and aviso["nivel"] == "alta"

    def test_cuota_vencida_aparece_entre_las_alertas(self, db):
        from datetime import date
        atleta = crear_usuario(db, cuota_mensual=Decimal(150),
                               cobro_desde=date(2020, 1, 1))
        crear_parte(db, atleta.id, semana(0))
        assert "pago_vencido" in tipos(alertas.del_atleta(db, atleta))

    def test_las_urgentes_van_primero(self, db):
        """El panel muestra la lista tal cual sale: si una cuota vencida queda
        arriba de un dolor 8/10, el profesor lee primero lo que menos importa."""
        from datetime import date
        atleta = crear_usuario(db, cuota_mensual=Decimal(150),
                               cobro_desde=date(2020, 1, 1))
        crear_parte(db, atleta.id, semana(0), molestias=True,
                    molestia_zona="rodilla", molestia_dolor=9)
        salida = alertas.del_atleta(db, atleta)
        niveles = [alertas.PRIORIDAD[a["nivel"]] for a in salida]
        assert niveles == sorted(niveles)
        assert salida[0]["tipo"] == "molestia"


class TestAlertasDelClub:
    def test_los_atletas_sin_alertas_no_aparecen(self, db):
        tranquilo = crear_usuario(db, username="tranquilo")
        crear_parte(db, tranquilo.id, semana(0), sueno_calidad=5,
                    dolor_muscular=5, estres=5, animo=5)
        assert alertas.del_club(db) == []

    def test_no_incluye_a_los_dados_de_baja(self, db):
        crear_usuario(db, username="exatleta", is_active=False)
        assert alertas.del_club(db) == []

    def test_ordena_por_el_atleta_mas_urgente(self, db):
        """Los nombres están puestos para que el orden alfabético ponga a `leve`
        primero: si el test pasa, es por la prioridad y no por el nombre."""
        from datetime import date
        leve = crear_usuario(db, username="leve", full_name="A Leve",
                             cuota_mensual=Decimal(150), cobro_desde=date.today())
        grave = crear_usuario(db, username="grave", full_name="Z Grave")
        crear_parte(db, leve.id, semana(0))            # solo debe la cuota: baja
        crear_parte(db, grave.id, semana(0), animo=1)  # puntuó el mínimo: alta

        salida = alertas.del_club(db)
        assert [f["atleta"].username for f in salida] == ["grave", "leve"]
        assert tipos(salida[1]["alertas"]) == {"pago_vencido"}
