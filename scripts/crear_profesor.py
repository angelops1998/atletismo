"""Crea el usuario del profesor. Se corre una sola vez, al instalar.

No hay registro público: los atletas los da de alta el profesor desde el panel, y
el profesor se crea acá. Un formulario de registro abierto en una app con 30
personas es solo una puerta más para que entre alguien de afuera.

    python scripts/crear_profesor.py
"""
import sys
from pathlib import Path
from getpass import getpass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal            # noqa: E402
from app.models.user import User                 # noqa: E402
from app.auth import hash_password               # noqa: E402
from app.tiempo import hoy                       # noqa: E402


def main() -> None:
    db = SessionLocal()
    try:
        if db.query(User).filter(User.role == "profesor").first():
            existente = db.query(User).filter(User.role == "profesor").first()
            print(f"Ya existe un profesor: {existente.username}")
            respuesta = input("¿Crear otro de todos modos? [s/N] ").strip().lower()
            if respuesta != "s":
                return

        nombre = input("Nombre y apellido: ").strip()
        usuario = input("Usuario (para entrar): ").strip().lower()
        email = input("Correo (opcional): ").strip().lower()
        password = getpass("Contraseña: ")
        if len(password) < 8:
            sys.exit("La contraseña tiene que tener al menos 8 caracteres.")
        if password != getpass("Repetir la contraseña: "):
            sys.exit("Las contraseñas no coinciden.")

        if db.query(User).filter(User.username == usuario).first():
            sys.exit(f"El usuario «{usuario}» ya existe.")

        db.add(User(
            username=usuario,
            email=email or None,
            hashed_password=hash_password(password),
            full_name=nombre or usuario,
            role="profesor",
            fecha_alta=hoy(),
        ))
        db.commit()
        print(f"\nListo. Entrá en /auth/login con «{usuario}».")
    finally:
        db.close()


if __name__ == "__main__":
    main()
