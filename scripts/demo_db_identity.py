"""Validación unificada de la identidad de la base de datos de demostración.

Este módulo es el único punto de validación de la URL y la identidad del
servidor de base de datos antes de cualquier operación de escritura (migraciones,
seed, arranque de la aplicación). Se usa tanto desde ``scripts/seed_demo.py``
como desde el arranque de PowerShell (a través de ``python scripts/demo_db_identity.py``).

Nunca se imprime la URL completa de conexión ni la contraseña en mensajes de
error. Se falla cerrado: si la identidad no se puede establecer positivamente,
se detiene la ejecución.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

from sqlalchemy import create_engine, text


DEMO_DB_NAME = "atletismo_demo"
APPROVED_HOSTNAMES = ("localhost", "127.0.0.1")
SUPPORTED_SCHEMES = ("postgresql", "postgres")


class DatabaseIdentityError(Exception):
    """La URL de base de datos o la identidad del servidor no son válidas para el demo."""


@dataclass(frozen=True)
class DatabaseIdentity:
    scheme: str
    hostname: str
    port: Optional[int]
    dbname: str
    username: Optional[str]

    @property
    def is_local_demo(self) -> bool:
        return (
            self.scheme in SUPPORTED_SCHEMES
            and self.hostname in APPROVED_HOSTNAMES
            and self.dbname == DEMO_DB_NAME
            and (self.port is None or 1 <= self.port <= 65535)
        )


def parse_and_validate_database_url(url: str) -> DatabaseIdentity:
    """Parsea y valida estructuralmente una DATABASE_URL.

    Requisitos:
    - Esquema postgresql:// o postgres://
    - Host localhost o 127.0.0.1 (nunca remoto, Supabase, producción)
    - Base de datos exactamente ``atletismo_demo``
    - Puerto válido (1-65535) si se especifica; puerto 0 rechazado

    No se incluye la contraseña en el objeto devuelto ni en los mensajes de error.
    """
    try:
        parsed = urlparse(url)
    except Exception as exc:
        raise DatabaseIdentityError(
            "No se pudo parsear DATABASE_URL."
        ) from exc

    if parsed.scheme not in SUPPORTED_SCHEMES:
        raise DatabaseIdentityError(
            f"DATABASE_URL no usa el esquema postgresql://: {parsed.scheme}"
        )

    if parsed.hostname not in APPROVED_HOSTNAMES:
        raise DatabaseIdentityError(
            f"DATABASE_URL no apunta a una instancia local aprobada: {parsed.hostname}"
        )

    if parsed.path not in (f"/{DEMO_DB_NAME}", DEMO_DB_NAME):
        raise DatabaseIdentityError(
            f"La base de datos no es '{DEMO_DB_NAME}' (path: {parsed.path})."
        )

    try:
        puerto = parsed.port
    except ValueError as exc:
        raise DatabaseIdentityError(
            "Puerto de DATABASE_URL fuera de rango (0-65535)."
        ) from exc
    if puerto is not None and puerto == 0:
        raise DatabaseIdentityError("El puerto 0 no es válido para PostgreSQL.")

    return DatabaseIdentity(
        scheme=parsed.scheme,
        hostname=parsed.hostname or "",
        port=puerto,
        dbname=parsed.path.lstrip("/"),
        username=parsed.username,
    )


def verify_connected_identity(db_session) -> None:
    """Confirma que la conexión activa apunta a PostgreSQL ``atletismo_demo``.

    Ejecuta ``SELECT current_database(), version()`` contra el servidor realmente
    conectado y compara el nombre de la base y el motor. Nunca imprime la URL
    completa ni la contraseña.
    """
    try:
        row = db_session.execute(text("SELECT current_database(), version()")).first()
    except Exception as exc:
        raise DatabaseIdentityError(
            "No se pudo verificar la identidad del servidor conectado."
        ) from exc

    if row is None:
        raise DatabaseIdentityError(
            "El servidor no devolvió identidad de base de datos."
        )

    nombre_db = row[0]
    version = row[1] or ""
    if nombre_db != DEMO_DB_NAME:
        raise DatabaseIdentityError(
            f"La base de datos conectada es '{nombre_db}', se esperaba '{DEMO_DB_NAME}'."
        )
    if "PostgreSQL" not in version:
        raise DatabaseIdentityError("El motor conectado no es PostgreSQL.")


def validate_before_write(db_session, url: str) -> DatabaseIdentity:
    """Valida la URL y la identidad del servidor conectado antes de escribir.

    Es el punto único de validación que deben usar todas las rutas de escritura
    (migraciones, seed, arranque de la app). Falla cerrado si algo no cuadra.
    """
    identity = parse_and_validate_database_url(url)
    if not identity.is_local_demo:
        raise DatabaseIdentityError(
            "DATABASE_URL no apunta a la base de demostración aislada local."
        )
    verify_connected_identity(db_session)
    return identity


def verify_database_identity(url: str) -> DatabaseIdentity:
    """Valida la URL y verifica la identidad del servidor realmente conectado.

    Crea un engine de SQLAlchemy, establece una conexión real y ejecuta una
    consulta de identidad del servidor. Falla cerrado si la URL no es válida,
    la conexión falla, el motor no es PostgreSQL o la base no es
    ``atletismo_demo``.

    Se usa antes de ejecutar Alembic para asegurar que las migraciones no se
    apliquen a una base de datos incorrecta.
    """
    identity = parse_and_validate_database_url(url)
    if not identity.is_local_demo:
        raise DatabaseIdentityError(
            "DATABASE_URL no apunta a la base de demostración aislada local."
        )

    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            verify_connected_identity(conn)
    except DatabaseIdentityError:
        raise
    except Exception as exc:
        raise DatabaseIdentityError(
            "No se pudo verificar la identidad del servidor conectado."
        ) from exc
    finally:
        engine.dispose()

    return identity


def main() -> None:
    """Punto de entrada para validación desde la línea de comandos.

    Lee DATABASE_URL del entorno y valida su identidad. Con ``--verify-connection``
    establece una conexión real y verifica que el servidor conectado sea
    PostgreSQL con la base ``atletismo_demo``. Sin el flag, solo valida la
    estructura de la URL.

    Imprime DB_OK si todo cuadra. Sale con código distinto de cero y un
    mensaje sin credenciales si falla.
    """
    import os

    url = os.environ.get("DATABASE_URL", "")
    if not url:
        print("ERROR: DATABASE_URL no está definida.", file=sys.stderr)
        sys.exit(1)

    verify_connection = "--verify-connection" in sys.argv

    try:
        if verify_connection:
            verify_database_identity(url)
        else:
            parse_and_validate_database_url(url)
    except DatabaseIdentityError as exc:
        # Mensaje sanitizado: nunca incluir la URL completa (puede tener credenciales).
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    print("DB_OK")


if __name__ == "__main__":
    main()
