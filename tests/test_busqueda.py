"""La búsqueda del padrón.

Es un LIKE sobre el nombre. Los comodines de LIKE son caracteres corrientes en un
buscador, y sin escaparlos la pantalla contestaba cualquier cosa: un "%" devolvía
el padrón entero como si hubiera coincidido con todos.
"""
import pytest

from conftest import crear_usuario, entrar

NOMBRES = ["Lucía Fernández", "Mateo Rivas", "Ana 100% Test", "Juan_Pablo Díaz"]


@pytest.fixture
def buscar(client, db):
    """Deja al profesor con la sesión abierta y devuelve una función de búsqueda
    que responde con los nombres que quedaron en pantalla."""
    profe = crear_usuario(db, username="profe", role="profesor")
    for i, nombre in enumerate(NOMBRES):
        crear_usuario(db, username=f"u{i}", full_name=nombre)
    entrar(client, profe)

    def consultar(q: str) -> set[str]:
        cuerpo = client.get("/atletas", params={"q": q}).text
        return {n for n in NOMBRES if n in cuerpo}

    return consultar


class TestBusqueda:
    def test_encuentra_por_parte_del_nombre(self, buscar):
        assert buscar("fern") == {"Lucía Fernández"}

    def test_no_distingue_mayusculas(self, buscar):
        assert buscar("RIVAS") == {"Mateo Rivas"}

    def test_sin_texto_muestra_todos(self, buscar):
        assert buscar("") == set(NOMBRES)

    def test_sin_resultados_no_rompe(self, buscar):
        assert buscar("zzzz") == set()

    def test_el_porcentaje_no_trae_el_padron_entero(self, buscar):
        """Antes `%` funcionaba como comodín y devolvía a todos. Ahora es un
        carácter más: encuentra al único que lo tiene en el nombre."""
        assert buscar("%") == {"Ana 100% Test"}

    def test_el_guion_bajo_no_es_comodin_de_un_caracter(self, buscar):
        """Con `_` como comodín, "Luc_a" encontraba a Lucía. Ahora solo encuentra
        al que tiene un guión bajo de verdad."""
        assert buscar("Luc_a") == set()
        assert buscar("Juan_Pablo") == {"Juan_Pablo Díaz"}

    def test_la_barra_invertida_tampoco_rompe(self, buscar):
        """Es el carácter de escape: sin escaparlo a él también, un `\\` suelto
        dejaba el patrón mal formado."""
        assert buscar("\\") == set()
        assert buscar("100\\%") == set()
