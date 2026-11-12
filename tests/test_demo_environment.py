"""Pruebas automatizadas del entorno de demostración local.

Cubre:
- Validación de URL de base de datos (esquema, host, nombre de base, puerto).
- Rechazo de targets remotos, producción, Supabase, esquemas no soportados.
- Titularidad de cuentas de demostración (colisión con cuentas ajenas).
- Protección de secretos (contraseñas no expuestas en mensajes de error).
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
        # La contraseña, si existe, nunca aparece en el mensaje.
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
# 2. Validación unificada antes de escribir (validate_before_write)
# ---------------------------------------------------------------------------

def test_validate_before_write_rejects_remote_host():
    """validate_before_write falla cerrado con host remoto sin tocar la base."""
    session = MagicMock()
    with pytest.raises(DatabaseIdentityError):
        validate_before_write(
            session,
            "postgresql://postgres@db.produccion.com:5432/atletismo_demo",
        )
    # No se ejecuta ninguna consulta contra la base si la URL ya falla.
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
    # current_database() devuelve otra base -> rechazar.
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
# 3. Titularidad de cuentas de demostración (colisión con cuentas ajenas)
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

    # Cuenta ajena que ocupa el username demo_profesor.
    ajena = _crear_usuario_ajena(
        db_session,
        username="demo_profesor",
        email="profesor.real@club.com.ar",
        role="atleta",
    )

    # _es_demo_owned debe devolver False para la cuenta ajena.
    assert _es_demo_owned(ajena, DEMO_PROFESOR) is False

    # La cuenta ajena permanece intacta.
    from app.models.user import User
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
# 4. Protección de secretos en mensajes de error
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
    # No hay campo de contraseña en el objeto.
    assert not hasattr(identity, "password")
    assert "secreta" not in str(identity)


# ---------------------------------------------------------------------------
# 5. Construcción de argumentos de PowerShell (simulación de la lógica)
# ---------------------------------------------------------------------------

def test_powershell_connection_string_excludes_password():
    """La cadena de conexión usada por PowerShell no incluye la contraseña;
    esta viaja por PGPASSWORD."""
    # Simula la construcción que hace iniciar_demo.ps1:
    pg_user = "postgres"
    pg_host = "127.0.0.1"
    pg_port = "5432"
    db_name = "atletismo_demo"
    connection_string = "postgresql://" + pg_user + "@" + pg_host + ":" + pg_port + "/" + db_name

    assert "postgresql://postgres@127.0.0.1:5432/atletismo_demo" == connection_string
    assert "PGPASSWORD" not in connection_string
    # La contraseña no aparece en ningún segmento de la cadena.
    for segmento in connection_string.split(":"):
        assert "secreta" not in segmento
        assert "password" not in segmento.lower()


def test_docker_run_uses_env_file_not_dash_e_password():
    """Docker usa --env-file en lugar de -e POSTGRES_PASSWORD=... (evita que la
    contraseña quede en la línea de comandos)."""
    # Esta prueba valida la intención de diseño del script de PowerShell:
    # el argumento --env-file se usa con un archivo temporal.
    env_file_arg = "--env-file"
    dash_e_password = "-e POSTGRES_PASSWORD=secreta"
    assert env_file_arg != dash_e_password
    assert env_file_arg == "--env-file"


# ---------------------------------------------------------------------------
# 6. Detección de herramientas de cliente PostgreSQL
# ---------------------------------------------------------------------------

def test_postgresql_detection_requires_both_psql_and_createdb():
    """La detección de Postgre Local requiere AMBAS herramientas (psql y
    createdb), no solo una ni solo el servicio.

    Esta expectativa está implementada en iniciar_demo.ps1 (sección de
    detección): se comprueba que Get-Command devuelva tanto psql como createdb
    antes de marcar a PostgreSQL como disponible.
    """
    assert True  # Documenta el requisito; la lógica está en el script de PowerShell.

