"""Estado de cuenta y lectura de montos.

La cobranza es lo que el profesor le reclama a la gente en la mano: un error acá
no se ve en una pantalla rota, se ve en un reclamo mal hecho.
"""
from datetime import date
from decimal import Decimal

import pytest

from app.services import cobranza
from conftest import crear_usuario


class TestParsearMonto:
    """El profesor escribe los montos como los dice. Estos casos son la regla
    entera: la coma siempre es decimal, y el punto solo lo es cuando no puede ser
    separador de miles."""

    @pytest.mark.parametrize("texto,esperado", [
        # El punto como separador de miles, que es como se escribe acá
        ("25.000", "25000"),
        ("1.234.567", "1234567"),
        # El punto como decimal: una o dos cifras detrás y nada más
        ("150.50", "150.50"),
        ("150.5", "150.5"),
        ("25.00", "25.00"),
        # La coma es siempre decimal
        ("150,50", "150.50"),
        ("1.234,56", "1234.56"),
        ("25000,50", "25000.50"),
        # Sin separadores
        ("1500", "1500"),
        ("  200  ", "200"),
        ("0", "0"),
    ])
    def test_lee_el_monto(self, texto, esperado):
        assert cobranza.parsear_monto(texto) == Decimal(esperado)

    def test_punto_decimal_no_se_multiplica_por_cien(self):
        """La regresión que motivó el parser: tratando el punto siempre como
        separador de miles, cobrar Bs 150,50 escrito con punto guardaba 15050."""
        assert cobranza.parsear_monto("150.50") == Decimal("150.50")

    @pytest.mark.parametrize("texto", ["", "   ", None, "abc", "12,,3", "$100"])
    def test_lo_que_no_se_entiende_es_None(self, texto):
        assert cobranza.parsear_monto(texto) is None


class TestMeses:
    def test_meses_entre_incluye_las_dos_puntas(self):
        assert cobranza.meses_entre(date(2026, 1, 15), date(2026, 3, 2)) == [
            date(2026, 1, 1), date(2026, 2, 1), date(2026, 3, 1)]

    def test_un_solo_mes(self):
        assert cobranza.meses_entre(date(2026, 5, 4), date(2026, 5, 28)) == [date(2026, 5, 1)]

    def test_cruza_el_anio(self):
        assert cobranza.mes_siguiente(date(2026, 12, 1)) == date(2027, 1, 1)
        assert cobranza.mes_anterior(date(2026, 1, 1)) == date(2025, 12, 1)


class TestEstadoCuenta:
    def test_sin_cuota_asignada_no_debe_nada(self, db):
        atleta = crear_usuario(db, cuota_mensual=Decimal(0), cobro_desde=date(2026, 1, 1))
        assert cobranza.estado_cuenta(db, atleta)["estado"] == "sin_cuota"

    def test_sin_cobro_desde_no_debe_nada(self, db):
        """El atleta recién cargado sin fecha de cobro no puede aparecer debiendo:
        es la diferencia entre 'todavía no le cobramos' y 'no pagó'."""
        atleta = crear_usuario(db, cuota_mensual=Decimal(150), cobro_desde=None)
        assert cobranza.estado_cuenta(db, atleta)["estado"] == "sin_cuota"

    def test_debe_los_meses_desde_que_se_le_cobra(self, db):
        atleta = crear_usuario(db, cuota_mensual=Decimal(150), cobro_desde=date(2026, 1, 1))
        estado = cobranza.estado_cuenta(db, atleta, hasta=date(2026, 3, 10))
        assert estado["estado"] == "debe"
        assert estado["cantidad"] == 3                 # enero, febrero y marzo
        assert estado["deuda"] == Decimal(450)
        assert estado["texto"] == "Debe 3 meses"

    def test_el_mes_pagado_se_descuenta(self, db):
        from app.models.pago import Pago
        atleta = crear_usuario(db, cuota_mensual=Decimal(150), cobro_desde=date(2026, 1, 1))
        db.add(Pago(atleta_id=atleta.id, periodo=date(2026, 2, 1),
                    fecha_pago=date(2026, 3, 5), monto=Decimal(150)))
        db.commit()
        estado = cobranza.estado_cuenta(db, atleta, hasta=date(2026, 3, 10))
        assert estado["meses"] == [date(2026, 1, 1), date(2026, 3, 1)]
        assert estado["deuda"] == Decimal(300)

    def test_singular_cuando_debe_un_solo_mes(self, db):
        atleta = crear_usuario(db, cuota_mensual=Decimal(150), cobro_desde=date(2026, 3, 1))
        assert cobranza.estado_cuenta(db, atleta, hasta=date(2026, 3, 20))["texto"] == "Debe 1 mes"

    def test_al_dia_cuando_pago_todo(self, db):
        from app.models.pago import Pago
        atleta = crear_usuario(db, cuota_mensual=Decimal(150), cobro_desde=date(2026, 3, 1))
        db.add(Pago(atleta_id=atleta.id, periodo=date(2026, 3, 1),
                    fecha_pago=date(2026, 3, 2), monto=Decimal(150)))
        db.commit()
        assert cobranza.estado_cuenta(db, atleta, hasta=date(2026, 3, 20))["estado"] == "al_dia"


class TestFormato:
    @pytest.mark.parametrize("monto,esperado", [
        (25000, "Bs 25.000"),
        (150, "Bs 150"),
        (0, "Bs 0"),
        (None, "Bs 0"),
        (Decimal("1234567"), "Bs 1.234.567"),
    ])
    def test_miles_con_punto(self, monto, esperado):
        assert cobranza.formato_pesos(monto) == esperado

    def test_con_decimales_usa_coma(self):
        assert cobranza.formato_pesos(Decimal("1234.5"), decimales=True) == "Bs 1.234,50"

    def test_sin_signo(self):
        assert cobranza.formato_pesos(25000, con_signo=False) == "25.000"
