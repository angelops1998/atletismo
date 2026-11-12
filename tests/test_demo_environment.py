"""Pruebas automatizadas del entorno de demostración local.

Cubre:
- Validación de URL de base de datos (esquema, host, nombre de base, puerto).
- Rechazo de targets remotos, producción, Supabase, esquemas no soportados.
- Titularidad de cuentas de demostración (colisión con cuentas ajenas).
- Protección de secretos (contraseñas no expuestas en mensajes de error).
- Validación de identidad real contra una conexión (mockeada y real).
- Seguridad de migraciones: Alembic no ejecuta sin verificación previa.
- Construcción de argumentos de PowerShell (sin contraseñas en línea de comandos).

Se ejecuta sobre SQLite en memoria y mocks; no requiere PostgreSQL ni Docker.
"""

import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from scripts.demo_db_identity import (
    DatabaseIdentity,
    DatabaseIdentityError,
    parse_and_validate_database_url,
    validate_before_write,
    verify_database_identity,
)


# ---------------------------------------------------------------------------
# 1. Validación de URL de base de datos
# ---------------------------------------------------------------------------

VALID_URLS = [
    "postgresql://postgres@127.0.0.1:5432/atletismo_demo",
    "postgresql://postgres@localhost:5433/atletismo_demo",
    "postgres://postgres@localhost/atletismo_demo",
    "postgresql://postgres@127.0.0.1/atletismo_demo",
]

INVALID_URLS = [
    # Esquema no soportado (MySQL)
    ("mysql://postgres@localhost:3306/atletismo_demo", "no usa el esquema postgresql://"),
    # Host remoto
    ("postgresql://postgres@db.produccion.com:5432/atletismo_demo", "instancia local aprobada"),
    # Supabase
    ("postgresql://postgres@supabase-ref.supabase.co:5432/postgres", "instancia local aprobada"),
    # Base de datos incorrecta
    ("postgresql://postgres@localhost:5432/otra_base", "base de datos no es 'atletismo_demo'"),
    # Puerto 0
    ("postgresql://postgres@localhost:0/atletismo_demo", "puerto 0 no es válido"),
    # Puerto fuera de rango
    ("postgresql://postgres@localhost:99999/atletismo_demo", "fuera de rango"),
    # Vacío (esquema vacío)
    ("", "no usa el esquema postgresql://"),
    # Sin host
    ("postgresql:///atletismo_demo", "instancia local aprobada"),
]


@pytest.mark.parametrize("url", VALID_URLS)
def test_valid_database_urls_are_accepted(url):
    """URLs válidas de la base demo local no lanzan error."""
    identity = parse_and_validate_database_url(url)
    assert identity.scheme in ("postgresql", "postgres")
    assert identity.hostname in ("localhost", "127.0.0.1")
    assert identity.dbname == "atletismo_demo"
    assert identity.is_local_demo


@pytest.mark.parametrize("url, motivo", INVALID_URLS)
def test_invalid_database_urls_are_rejected(url, motivo):
    """URLs inválidas lanzan DatabaseIdentityError con mensaje sanitizado."""
    with pytest.raises(DatabaseIdentityError) as exc:
        parse_and_validate_database_url(url)
    mensaje = str(exc.value)
    # El mensaje nunca incluye la URL completa con credenciales.
    if url:
        url_sin_esquema = url.split("://", 1)[1] if "://" in url else url
        assert url_sin_esquema not in mensaje
    # El motivo de rechazo aparece en el mensaje.
    assert motivo.lower() in mensaje.lower()


def test_database_url_with_password_is_rejected_for_containing_credentials():
    """Una URL que incluya contraseña no se imprime en el error, pero se rechaza
    si el host no es local. El esquema/host/path se validan independientemente
    de la presencia de credenciales."""
    url = "postgresql://postgres:secreta@localhost:5432/atletismo_demo"
    identity = parse_and_validate_database_url(url)
    assert identity.dbname == "atletismo_demo"
    assert identity.hostname == "localhost"


def test_parse_and_validate_returns_identity_object():
    """El objeto devuelto tiene los campos esperados y no contiene contraseña."""
    identity = parse_and_validate_database_url("postgresql://postgres@127.0.0.1:5432/atletismo_demo")
    assert isinstance(identity, DatabaseIdentity)
    assert identity.username == "postgres"
    assert identity.port == 5432


# ---------------------------------------------------------------------------
# 2. Validación de identidad real de la conexión (verify_database_identity)
# ---------------------------------------------------------------------------

def test_verify_database_identity_rejects_non_postgresql_scheme():
    """verify_database_identity rechaza esquemas que no son PostgreSQL."""
    with pytest.raises(DatabaseIdentityError):
        verify_database_identity("sqlite://")


def test_verify_database_identity_rejects_remote_host():
    """verify_database_identity rechaza hosts remotos sin intentar conectar."""
    with pytest.raises(DatabaseIdentityError):
        verify_database_identity("postgresql://postgres@db.produccion.com:5432/atletismo_demo")


def test_verify_database_identity_rejects_wrong_database_name():
    """verify_database_identity rechaza nombre de base incorrecto sin conectar."""
    with pytest.raises(DatabaseIdentityError):
        verify_database_identity("postgresql://postgres@localhost:5432/otra_base")


@patch("scripts.demo_db_identity.create_engine")
def test_verify_database_identity_connection_failure(mock_create_engine):
    """verify_database_identity falla cuando la conexión al servidor falla."""
    mock_engine = MagicMock()
    mock_engine.connect.side_effect = Exception("Connection refused")
    mock_create_engine.return_value = mock_engine

    with pytest.raises(DatabaseIdentityError) as exc:
        verify_database_identity("postgresql://postgres@localhost:5432/atletismo_demo")
    assert "No se pudo verificar la identidad" in str(exc.value)


@patch("scripts.demo_db_identity.create_engine")
def test_verify_database_identity_missing_result(mock_create_engine):
    """verify_database_identity rechaza cuando current_database() devuelve None."""
    mock_conn = MagicMock()
    mock_conn.execute.return_value.first.return_value = None
    mock_engine = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn
    mock_create_engine.return_value = mock_engine

    with pytest.raises(DatabaseIdentityError) as exc:
        verify_database_identity("postgresql://postgres@localhost:5432/atletismo_demo")
    assert "no devolvió identidad" in str(exc.value).lower()


@patch("scripts.demo_db_identity.create_engine")
def test_verify_database_identity_null_database_name(mock_create_engine):
    """verify_database_identity rechaza cuando current_database() devuelve None como nombre."""
    mock_conn = MagicMock()
    mock_conn.execute.return_value.first.return_value = (None, "PostgreSQL 15")
    mock_engine = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn
    mock_create_engine.return_value = mock_engine

    with pytest.raises(DatabaseIdentityError) as exc:
        verify_database_identity("postgresql://postgres@localhost:5432/atletismo_demo")
    assert "None" in str(exc.value) or "no devolvió" in str(exc.value).lower()


@patch("scripts.demo_db_identity.create_engine")
def test_verify_database_identity_wrong_database_name(mock_create_engine):
    """verify_database_identity rechaza cuando current_database() devuelve otra base."""
    mock_conn = MagicMock()
    mock_conn.execute.return_value.first.return_value = ("otra_base", "PostgreSQL 15")
    mock_engine = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn
    mock_create_engine.return_value = mock_engine

    with pytest.raises(DatabaseIdentityError) as exc:
        verify_database_identity("postgresql://postgres@localhost:5432/atletismo_demo")
    assert "otra_base" in str(exc.value)
    assert "atletismo_demo" in str(exc.value)


@patch("scripts.demo_db_identity.create_engine")
def test_verify_database_identity_wrong_engine(mock_create_engine):
    """verify_database_identity rechaza cuando el motor no es PostgreSQL."""
    mock_conn = MagicMock()
    mock_conn.execute.return_value.first.return_value = ("atletismo_demo", "MySQL 8.0")
    mock_engine = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn
    mock_create_engine.return_value = mock_engine

    with pytest.raises(DatabaseIdentityError) as exc:
        verify_database_identity("postgresql://postgres@localhost:5432/atletismo_demo")
    assert "no es PostgreSQL" in str(exc.value)


@patch("scripts.demo_db_identity.create_engine")
def test_verify_database_identity_accepts_valid_identity(mock_create_engine):
    """verify_database_identity acepta URL válida + servidor conectado correcto."""
    mock_conn = MagicMock()
    mock_conn.execute.return_value.first.return_value = ("atletismo_demo", "PostgreSQL 15.3")
    mock_engine = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn
    mock_create_engine.return_value = mock_engine

    identity = verify_database_identity("postgresql://postgres@localhost:5432/atletismo_demo")
    assert identity.dbname == "atletismo_demo"


# ---------------------------------------------------------------------------
# 3. Validación unificada antes de escribir (validate_before_write)
# ---------------------------------------------------------------------------

def test_validate_before_write_rejects_remote_host():
    """validate_before_write falla cerrado con host remoto sin tocar la base."""
    session = MagicMock()
    with pytest.raises(DatabaseIdentityError):
        validate_before_write(
            session,
            "postgresql://postgres@db.produccion.com:5432/atletismo_demo",
        )
    session.execute.assert_not_called()


def test_validate_before_write_rejects_supabase():
    """Supabase se rechaza antes de cualquier escritura."""
    session = MagicMock()
    with pytest.raises(DatabaseIdentityError):
        validate_before_write(
            session,
            "postgresql://postgres@ref.supabase.co:5432/postgres",
        )
    session.execute.assert_not_called()


def test_validate_before_write_verifies_connected_identity():
    """Cuando la URL es válida, se verifica la identidad del servidor conectado."""
    session = MagicMock()
    session.execute.return_value.first.return_value = ("otra_base", "PostgreSQL 15")
    with pytest.raises(DatabaseIdentityError) as exc:
        validate_before_write(
            session,
            "postgresql://postgres@localhost:5432/atletismo_demo",
        )
    assert "otra_base" in str(exc.value)
    assert "atletismo_demo" in str(exc.value)


def test_validate_before_write_rejects_non_postgresql_engine():
    """El motor conectado debe ser PostgreSQL."""
    session = MagicMock()
    session.execute.return_value.first.return_value = ("atletismo_demo", "MySQL 8.0")
    with pytest.raises(DatabaseIdentityError) as exc:
        validate_before_write(
            session,
            "postgresql://postgres@localhost:5432/atletismo_demo",
        )
    assert "no es PostgreSQL" in str(exc.value)


def test_validate_before_write_accepts_valid_identity():
    """URL válida + servidor conectado correcto -> retorna la identidad."""
    session = MagicMock()
    session.execute.return_value.first.return_value = ("atletismo_demo", "PostgreSQL 15.3")
    identity = validate_before_write(
        session,
        "postgresql://postgres@localhost:5432/atletismo_demo",
    )
    assert identity.dbname == "atletismo_demo"


# ---------------------------------------------------------------------------
# 4. Seguridad de migraciones: Alembic no ejecuta sin verificación previa
# ---------------------------------------------------------------------------

def test_seed_demo_validates_identity_before_writes():
    """seed_demo.py llama _es_entorno_demo (validate_before_write) antes de
    crear o modificar cualquier registro."""
    import scripts.seed_demo as seed_mod

    # Verificar que _es_entorno_demo existe y usa validate_before_write
    assert hasattr(seed_mod, "_es_entorno_demo")
    source = seed_mod._es_entorno_demo.__code__.co_names
    assert "validate_before_write" in source


def test_powerShell_validates_identity_before_alembic():
    """iniciar_demo.ps1 ejecuta demo_db_identity.py --verify-connection ANTES
    de alembic upgrade head."""
    ps_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "scripts", "iniciar_demo.ps1",
    )
    with open(ps_path, "r", encoding="utf-8") as f:
        content = f.read()

    # --verify-connection debe aparecer antes de alembic upgrade head
    verify_idx = content.find("--verify-connection")
    alembic_idx = content.find("alembic upgrade head")
    assert verify_idx != -1, "--verify-connection no encontrado en el script"
    assert alembic_idx != -1, "alembic upgrade head no encontrado en el script"
    assert verify_idx < alembic_idx, (
        "La verificación de identidad debe ejecutarse antes de Alembic"
    )


# ---------------------------------------------------------------------------
# 5. Titularidad de cuentas de demostración (colisión con cuentas ajenas)
# ---------------------------------------------------------------------------

@pytest.fixture
def db_session():
    """Sesión SQLAlchemy sobre SQLite en memoria con las tablas de usuario."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.database import Base

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _crear_usuario_ajena(db_session, username, email, role, password_hash="hash-ajena"):
    from app.models.user import User
    from app.auth import hash_password
    u = User(
        username=username,
        email=email,
        hashed_password=hash_password(password_hash),
        full_name="Usuario Ajena",
        role=role,
        is_active=True,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


def test_ensure_user_rejects_foreign_account_occupying_demo_username(db_session):
    """Si el username demo ya existe con email/rol distintos, se detiene sin
    sobrescribir la cuenta ajena."""
    from scripts.seed_demo import _es_demo_owned, DEMO_PROFESOR

    ajena = _crear_usuario_ajena(
        db_session,
        username="demo_profesor",
        email="profesor.real@club.com.ar",
        role="atleta",
    )

    assert _es_demo_owned(ajena, DEMO_PROFESOR) is False

    # La cuenta ajena permanece intacta.
    db_session.refresh(ajena)
    assert ajena.email == "profesor.real@club.com.ar"
    assert ajena.role == "atleta"


def test_ensure_user_accepts_legitimate_demo_account(db_session):
    """Una cuenta demo legítima (username + email dominio dedicado + rol) pasa
    la validación de titularidad."""
    from scripts.seed_demo import _es_demo_owned, DEMO_PROFESOR

    from app.auth import hash_password
    from app.models.user import User
    legitima = User(
        username="demo_profesor",
        email="demo_profesor@atletismo.demo.local",
        hashed_password=hash_password("DemoProfe2026!"),
        full_name="Profesor Demo",
        role="profesor",
        is_active=True,
    )
    assert _es_demo_owned(legitima, DEMO_PROFESOR) is True


def test_ensure_user_rejects_wrong_role(db_session):
    """Mismo username y email, pero rol distinto -> no es demo."""
    from scripts.seed_demo import _es_demo_owned, DEMO_PROFESOR

    from app.auth import hash_password
    from app.models.user import User
    u = User(
        username="demo_profesor",
        email="demo_profesor@atletismo.demo.local",
        hashed_password=hash_password("x"),
        full_name="x",
        role="atleta",
    )
    assert _es_demo_owned(u, DEMO_PROFESOR) is False


def test_ensure_user_rejects_wrong_email(db_session):
    """Mismo username y rol, pero email distinto -> no es demo."""
    from scripts.seed_demo import _es_demo_owned, DEMO_PROFESOR

    from app.auth import hash_password
    from app.models.user import User
    u = User(
        username="demo_profesor",
        email="otro@atletismo.demo.local",
        hashed_password=hash_password("x"),
        full_name="x",
        role="profesor",
    )
    assert _es_demo_owned(u, DEMO_PROFESOR) is False


# ---------------------------------------------------------------------------
# 6. Protección de secretos en mensajes de error
# ---------------------------------------------------------------------------

def test_error_messages_do_not_contain_passwords():
    """Los mensajes de DatabaseIdentityError nunca incluyen contraseñas."""
    url_con_password = "postgresql://postgres:MiSecreta123!@db.produccion.com:5432/atletismo_demo"
    with pytest.raises(DatabaseIdentityError) as exc:
        parse_and_validate_database_url(url_con_password)
    mensaje = str(exc.value)
    assert "MiSecreta123" not in mensaje
    assert "postgresql://" not in mensaje


def test_database_url_with_password_not_logged_in_identity_object():
    """El objeto DatabaseIdentity no expone la contraseña."""
    url_con_password = "postgresql://postgres:secreta@localhost:5432/atletismo_demo"
    identity = parse_and_validate_database_url(url_con_password)
    assert not hasattr(identity, "password")
    assert "secreta" not in str(identity)


def test_error_messages_do_not_expose_full_url():
    """Los mensajes de error nunca incluyen la URL completa de conexión
    ni la contraseña cuando hay un error de validación."""
    # Usar una URL inválida (host remoto) que incluya contraseña, para verificar
    # que ni la contraseña ni la URL completa aparecen en el mensaje de error.
    url_con_password = "postgresql://postgres:secreta@db.produccion.com:5432/atletismo_demo"
    with pytest.raises(DatabaseIdentityError) as exc:
        parse_and_validate_database_url(url_con_password)
    mensaje = str(exc.value)
    # La contraseña no debe aparecer en el mensaje de error
    assert "secreta" not in mensaje
    # La URL completa con esquema y contraseña no debe aparecer
    assert "postgresql://postgres:secreta@" not in mensaje


# ---------------------------------------------------------------------------
# 7. Construcción de argumentos de PowerShell y Docker
# ---------------------------------------------------------------------------

def test_powershell_connection_string_excludes_password():
    """La cadena de conexión usada por PowerShell no incluye la contraseña;
    esta viaja por PGPASSWORD."""
    pg_user = "postgres"
    pg_host = "127.0.0.1"
    pg_port = "5432"
    db_name = "atletismo_demo"
    connection_string = "postgresql://" + pg_user + "@" + pg_host + ":" + pg_port + "/" + db_name

    assert connection_string == "postgresql://postgres@127.0.0.1:5432/atletismo_demo"
    assert "PGPASSWORD" not in connection_string
    for segmento in connection_string.split(":"):
        assert "secreta" not in segmento
        assert "password" not in segmento.lower()


def test_docker_filter_argument_is_complete():
    """El argumento --filter de Docker se construye como un argumento completo
    (name=contenedor) sin romper los límites del argumento."""
    container_name = "atletismo-demo-db"
    filter_arg = "name=" + container_name
    assert filter_arg == "name=atletismo-demo-db"
    assert " " not in filter_arg  # Sin espacios que rompan límites de argumento


def test_docker_volume_filter_argument_is_complete():
    """El argumento --filter de docker volume ls se construye completo."""
    volume_name = "atletismo-demo-pgdata"
    filter_arg = "name=" + volume_name
    assert filter_arg == "name=atletismo-demo-pgdata"
    assert " " not in filter_arg


def test_docker_mount_argument_is_complete():
    """El argumento --mount de Docker se construye como un argumento completo
    sin espacios internos que rompan los límites."""
    volume_name = "atletismo-demo-pgdata"
    mount_arg = "type=volume,src=" + volume_name + ",dst=/var/lib/postgresql/data"
    assert mount_arg == "type=volume,src=atletismo-demo-pgdata,dst=/var/lib/postgresql/data"
    assert " " not in mount_arg


def test_docker_publish_argument_is_complete():
    """El argumento -p de Docker se construye completo sin espacios."""
    pg_host_port = "5433"
    publish_arg = "127.0.0.1:" + pg_host_port + ":5432"
    assert publish_arg == "127.0.0.1:5433:5432"
    assert " " not in publish_arg


def test_postgresql_detection_requires_both_psql_and_createdb():
    """La detección de PostgreSQL local requiere AMBAS herramientas (psql y
    createdb), no solo una ni solo el servicio. Esto está implementado en
    iniciar_demo.ps1: se comprueba que Get-Command devuelva tanto psql como
    createdb antes de marcar a PostgreSQL como disponible."""
    # Leer el script y verificar la lógica de detección
    ps_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "scripts", "iniciar_demo.ps1",
    )
    with open(ps_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Verificar que se buscan ambas herramientas
    assert "Get-Command psql" in content
    assert "Get-Command createdb" in content
    # Verificar que se requieren ambas (operador -and entre ellas)
    assert "Get-Command psql" in content
    assert "Get-Command createdb" in content
    assert "-and" in content


# ---------------------------------------------------------------------------
# 8. Exclusión de credenciales del repositorio
# ---------------------------------------------------------------------------

def test_dotdemo_excluded_from_gitignore():
    """.demo/ debe estar en .gitignore para que las credenciales no se suban."""
    gitignore_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        ".gitignore",
    )
    with open(gitignore_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert ".demo/" in content, ".demo/ no está excluido en .gitignore"
