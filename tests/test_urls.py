"""Validación de los destinos de redirección.

Es una función de cinco líneas y es la que decide si el login del club puede
usarse para mandar a alguien a otro sitio. Los casos raros son el test.
"""
import pytest

from app.urls import ruta_interna

DEFECTO = "/panel"


class TestRutaInterna:
    @pytest.mark.parametrize("destino", [
        "/panel",
        "/atletas/5",
        "/pagos?error=monto",
        "/asistencia?fecha=2026-03-02&ok=1",
        "  /marcas  ",                 # el espacio de más no lo invalida
    ])
    def test_acepta_las_rutas_de_la_app(self, destino):
        assert ruta_interna(destino, DEFECTO) == destino.strip()

    @pytest.mark.parametrize("destino", [
        "//otrositio.com",             # protocolo relativo
        "https://otrositio.com",
        "http://otrositio.com",
        "otrositio.com",
        "",
        "   ",
        None,
    ])
    def test_rechaza_lo_que_sale_de_la_app(self, destino):
        assert ruta_interna(destino, DEFECTO) == DEFECTO

    @pytest.mark.parametrize("destino", [
        "/\\otrositio.com",            # el navegador lo normaliza a "//"
        "/\\/otrositio.com",
        "/\x00/otrositio.com",         # el NUL se cae y abajo queda un "//"
        "/\r\n/otrositio.com",
    ])
    def test_rechaza_la_barra_invertida_y_los_controles(self, destino):
        """Pedir solo que empiece con "/" y no con "//" no alcanza: los
        navegadores tratan la barra invertida como barra común, y descartan los
        caracteres de control antes de resolver la dirección."""
        assert ruta_interna(destino, DEFECTO) == DEFECTO

    def test_el_control_suelto_no_habilita_un_destino_externo(self):
        """Sacado el tabulador queda "/otrositio.com", que es una ruta interna
        (un 404 de la app) y no una salida a otro sitio."""
        assert ruta_interna("/\totrositio.com", DEFECTO) == "/otrositio.com"
