"""Los controles de acceso, contra la app real.

Todo lo de este archivo es una regresión de algo que en algún momento estuvo mal:
son los casos que conviene que fallen ruidosamente si alguien toca un middleware
o agrega una pantalla sin acordarse del control.
"""
from datetime import date
from decimal import Decimal

import pytest

from conftest import con_csrf, crear_usuario, entrar


@pytest.fixture
def profe(db):
    return crear_usuario(db, username="profe", role="profesor", full_name="La Profe")


@pytest.fixture
def atleta(db):
    return crear_usuario(db, username="atleta1", full_name="Un Atleta")


class TestCSRF:
    """El control se decide por el método, no por el content-type.

    Cuando dependía del content-type, el mismo POST mandado como JSON salteaba la
    validación entera y llegaba al handler: alcanzaba para borrar un pago o
    resetearle la contraseña a un atleta sin traer ningún token.
    """

    @pytest.mark.parametrize("tipo", [
        "application/json",
        "text/plain",
        "application/x-www-form-urlencoded",
    ])
    def test_un_post_sin_token_no_pasa(self, client, profe, tipo):
        entrar(client, profe)
        r = client.post("/asistencia", content=b"{}", headers={"content-type": tipo})
        assert r.status_code == 403

    def test_un_post_sin_content_type_no_pasa(self, client, profe):
        entrar(client, profe)
        assert client.post("/asistencia").status_code == 403

    @pytest.mark.parametrize("metodo", ["POST", "PUT", "PATCH", "DELETE"])
    def test_ningun_metodo_que_escribe_queda_afuera(self, client, profe, metodo):
        entrar(client, profe)
        r = client.request(metodo, "/pagos/1/borrar", content=b"{}",
                           headers={"content-type": "application/json"})
        assert r.status_code == 403

    def test_con_el_token_del_formulario_pasa(self, client, profe):
        entrar(client, profe)
        token = con_csrf(client, "/asistencia")
        r = client.post("/asistencia", data={"csrf_token": token, "fecha": "2026-03-02"},
                        follow_redirects=False)
        assert r.status_code == 302

    def test_la_cookie_csrf_viaja_con_httponly(self, client):
        cabecera = client.get("/auth/login").headers["set-cookie"]
        assert "csrf_token=" in cabecera and "HttpOnly" in cabecera


class TestRoles:
    PANTALLAS_DEL_PROFESOR = ["/panel", "/atletas", "/pagos", "/marcas",
                              "/asistencia", "/estadisticas"]

    @pytest.mark.parametrize("ruta", PANTALLAS_DEL_PROFESOR)
    def test_el_atleta_no_entra_a_lo_del_club(self, client, atleta, ruta):
        entrar(client, atleta)
        assert client.get(ruta).status_code == 403

    def test_el_atleta_no_ve_la_ficha_de_otro(self, client, db, atleta):
        otro = crear_usuario(db, username="otro")
        entrar(client, atleta)
        assert client.get(f"/atletas/{otro.id}").status_code == 403

    @pytest.mark.parametrize("ruta", PANTALLAS_DEL_PROFESOR)
    def test_sin_sesion_manda_al_login(self, client, ruta):
        r = client.get(ruta, follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"].startswith("/auth/login")

    def test_el_profesor_no_carga_partes(self, client, profe):
        """El parte lo carga cada atleta sobre sí mismo."""
        entrar(client, profe)
        assert client.get("/parte").status_code == 403

    def test_la_landing_es_publica(self, client):
        assert client.get("/club").status_code == 200
        assert client.get("/auth/login").status_code == 200


class TestSesion:
    def test_token_sin_huella_no_sirve(self, client, profe):
        """Los tokens emitidos antes de que la sesión quedara atada a la
        contraseña no valen: por eso al desplegar todos entran una vez más."""
        from app.auth import create_access_token
        client.cookies.set("access_token", create_access_token({"sub": profe.username}))
        r = client.get("/panel", follow_redirects=False)
        assert r.status_code == 302

    def test_resetear_la_contrasena_echa_al_atleta(self, client, db, profe, atleta):
        entrar(client, atleta)
        assert client.get("/mis-datos").status_code == 200
        sesion_del_atleta = client.cookies.get("access_token")

        entrar(client, profe)
        token = con_csrf(client, f"/atletas/{atleta.id}")
        assert client.post(f"/atletas/{atleta.id}/password", data={"csrf_token": token},
                           follow_redirects=False).status_code == 302

        client.cookies.clear()
        client.cookies.set("access_token", sesion_del_atleta)
        r = client.get("/mis-datos", follow_redirects=False)
        assert r.headers["location"].startswith("/auth/login"), \
            "la sesión vieja del atleta tenía que caerse al login"

    def test_la_contrasena_provisoria_no_va_en_la_url(self, client, profe, atleta):
        """El query string queda escrito en el log de acceso y en el historial del
        navegador; ahí una contraseña en claro no vence nunca."""
        entrar(client, profe)
        token = con_csrf(client, f"/atletas/{atleta.id}")
        r = client.post(f"/atletas/{atleta.id}/password", data={"csrf_token": token},
                        follow_redirects=False)
        assert r.headers["location"] == f"/atletas/{atleta.id}"
        assert "alta=" not in r.headers["location"]
        assert "HttpOnly" in r.headers["set-cookie"]

    def test_la_provisoria_se_muestra_una_sola_vez(self, client, profe, atleta):
        entrar(client, profe)
        token = con_csrf(client, f"/atletas/{atleta.id}")
        client.post(f"/atletas/{atleta.id}/password", data={"csrf_token": token},
                    follow_redirects=False)
        assert "Contraseña provisoria" in client.get(f"/atletas/{atleta.id}").text
        assert "Contraseña provisoria" not in client.get(f"/atletas/{atleta.id}").text


class TestRedirecciones:
    def test_el_login_no_manda_afuera(self, client, atleta):
        token = con_csrf(client)
        r = client.post("/auth/login", data={
            "identificador": "atleta1", "password": "claveprueba1",
            "csrf_token": token, "next": "/\\otrositio.com",
        }, follow_redirects=False)
        assert r.headers["location"] == "/inicio"

    def test_el_login_respeta_el_destino_interno(self, client, atleta):
        token = con_csrf(client)
        r = client.post("/auth/login", data={
            "identificador": "atleta1", "password": "claveprueba1",
            "csrf_token": token, "next": "/mis-datos",
        }, follow_redirects=False)
        assert r.headers["location"] == "/mis-datos"


class TestFuerzaBruta:
    def test_despues_de_varios_fallos_corta(self, client, atleta):
        from app.routers import auth as router_auth
        token = con_csrf(client)
        datos = {"identificador": "atleta1", "password": "equivocada",
                 "csrf_token": token}
        codigos = [client.post("/auth/login", data=datos).status_code
                   for _ in range(router_auth.INTENTOS_MAX + 2)]
        assert codigos[:router_auth.INTENTOS_MAX] == [401] * router_auth.INTENTOS_MAX
        assert codigos[-1] == 429

    def test_no_deja_afuera_a_los_demas(self, client, db, atleta):
        """Contando solo por usuario, cualquiera podría bloquear al profesor
        tirándole contraseñas mal a propósito."""
        from app.routers import auth as router_auth
        crear_usuario(db, username="otro")
        token = con_csrf(client)
        for _ in range(router_auth.INTENTOS_MAX + 1):
            client.post("/auth/login", data={"identificador": "atleta1",
                                             "password": "mal", "csrf_token": token})
        r = client.post("/auth/login", data={"identificador": "otro",
                                             "password": "mal", "csrf_token": token})
        assert r.status_code == 401

    def test_el_header_de_ip_no_lo_elige_el_atacante(self, client, atleta):
        """Render no descarta el X-Forwarded-For que venga de afuera: le agrega la
        suya al final. Si el freno leyera la primera entrada, rotar ese header
        daría intentos infinitos y no serviría de nada."""
        from app.routers import auth as router_auth
        token = con_csrf(client)
        codigos = []
        for i in range(router_auth.INTENTOS_MAX + 2):
            r = client.post("/auth/login",
                            data={"identificador": "atleta1", "password": "mal",
                                  "csrf_token": token},
                            headers={"X-Forwarded-For": f"10.0.0.{i}, 172.16.0.1"})
            codigos.append(r.status_code)
        assert codigos[-1] == 429, "cambiando el header se saltea el freno"

    def test_separa_por_la_ip_que_puso_el_proxy(self, client, atleta):
        """La última entrada sí la pone el proxy: dos personas distintas detrás de
        él tienen que contar por separado."""
        from app.routers import auth as router_auth
        token = con_csrf(client)
        datos = {"identificador": "atleta1", "password": "mal", "csrf_token": token}
        for _ in range(router_auth.INTENTOS_MAX + 1):
            client.post("/auth/login", data=datos,
                        headers={"X-Forwarded-For": "172.16.0.1"})
        r = client.post("/auth/login", data=datos,
                        headers={"X-Forwarded-For": "172.16.0.2"})
        assert r.status_code == 401


class TestCabeceras:
    def test_manda_las_cabeceras_de_seguridad(self, client):
        h = client.get("/auth/login").headers
        assert h["x-content-type-options"] == "nosniff"
        assert h["x-frame-options"] == "DENY"
        assert h["referrer-policy"] == "same-origin"
        assert "frame-ancestors 'none'" in h["content-security-policy"]
        assert "script-src 'self'" in h["content-security-policy"]

    def test_no_publica_la_documentacion_de_la_api(self, client):
        for ruta in ("/docs", "/redoc", "/openapi.json"):
            assert client.get(ruta).status_code == 404


class TestSinTerceros:
    """La app no carga nada de afuera.

    Es el mismo criterio que hace que los gráficos sean SVG generados en el
    servidor: se abre desde la pista con mala señal, y una hoja de estilos de un
    tercero bloquea el render detrás de dos handshakes más. De paso, ninguna
    visita de un atleta llega a Google.
    """

    def test_ninguna_pantalla_pide_recursos_a_otro_origen(self, client, profe, atleta):
        entrar(client, profe)
        pantallas = ["/club", "/panel", "/atletas", "/pagos", "/marcas",
                     "/asistencia", "/estadisticas", "/cuenta"]
        for ruta in pantallas:
            cuerpo = client.get(ruta).text
            for host in ("fonts.googleapis.com", "fonts.gstatic.com"):
                assert host not in cuerpo, f"{ruta} carga {host}"

    def test_la_politica_no_habilita_ningun_origen_externo(self, client):
        csp = client.get("/auth/login").headers["content-security-policy"]
        assert "style-src 'self' 'unsafe-inline';" in csp
        assert "font-src 'self';" in csp
        assert "https://" not in csp

    def test_las_tipografias_se_sirven_desde_la_app(self, client):
        hoja = client.get("/static/css/fuentes.css")
        assert hoja.status_code == 200
        assert "https://" not in hoja.text
        for nombre in ("hanken-grotesk-400-800-latin.woff2",
                       "barlow-condensed-700-latin.woff2"):
            assert nombre in hoja.text
            assert client.get(f"/static/fonts/{nombre}").status_code == 200
