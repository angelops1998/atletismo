"""La página pública del club.

Lo único que hay que sostener acá es lo que el club pidió explícitamente: que la
sección de seguimiento con datos no se vea sin cuenta, que los horarios y costos
sean los vigentes y que el equipo sea el real.
"""
from conftest import crear_usuario, entrar


class TestQueVeQuienNoTieneCuenta:
    def test_no_ve_la_seccion_de_entrenar_con_datos(self, client):
        for url in ("/", "/club"):
            r = client.get(url)
            assert r.status_code == 200
            assert "Entrenamos con datos" not in r.text
            assert 'id="metodo"' not in r.text

    def test_ve_la_piramide_y_la_oferta(self, client):
        cuerpo = client.get("/").text
        assert "Pirámide Delta" in cuerpo
        for nivel in ("Formación multilateral", "Especialización deportiva", "Alto rendimiento"):
            assert nivel in cuerpo
        assert "Qué ofrecemos" in cuerpo
        assert "girar, rodar, atrapar, lanzar, saltar, correr" in cuerpo

    def test_horarios_y_costos_vigentes(self, client):
        cuerpo = client.get("/").text
        assert "Pista Verde" in cuerpo and "Félix Capriles" in cuerpo and "Laguna Alalay" in cuerpo
        assert "9:45 a 11:15" in cuerpo and "16:30 a 18:00" in cuerpo and "9:00 a 10:15" in cuerpo
        assert "17:00 a 18:15" in cuerpo and "17:00 a 18:00" in cuerpo
        assert "Bs 200" in cuerpo and "Bs 150" in cuerpo
        assert "prueba gratuita" in cuerpo

    def test_el_equipo_es_el_real(self, client):
        cuerpo = client.get("/").text
        assert "Mario Andrés Candia Antezana" in cuerpo
        assert "Laura Ramos Cameo" in cuerpo
        assert "de ejemplo" not in cuerpo


class TestQueVeQuienTieneCuenta:
    def test_con_sesion_si_ve_entrenar_con_datos(self, client, db):
        atleta = crear_usuario(db)
        entrar(client, atleta)
        r = client.get("/club")
        assert r.status_code == 200
        assert "Entrenamos con datos" in r.text
        assert 'href="/inicio"' in r.text      # el botón lleva a su panel, no al login

    def test_la_raiz_con_sesion_sigue_yendo_al_panel(self, client, db):
        atleta = crear_usuario(db)
        entrar(client, atleta)
        r = client.get("/", follow_redirects=False)
        assert r.status_code == 302 and r.headers["location"] == "/inicio"
