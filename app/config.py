from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    # La sesión es deslizante (ver SesionDeslizanteMiddleware): mientras la persona
    # use la app la cookie se renueva sola, así que este valor es cuánto puede
    # estar SIN entrar antes de que le pidan la contraseña de nuevo. Los atletas
    # entran una vez por semana: con una sesión corta les pediría la contraseña
    # todas las veces y terminarían no cargando el parte.
    access_token_expire_minutes: int = 60 * 24 * 60  # 60 días
    https_only: bool = False

    # Datos del club que se muestran en la página pública y en los mensajes.
    # Viven acá y no en la base porque son de la instalación, no del uso diario.
    club_nombre: str = "Club de Atletismo"
    club_telefono: str = ""
    club_whatsapp: str = ""
    club_email: str = ""
    club_direccion: str = ""
    club_instagram: str = ""
    club_facebook: str = ""

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    try:
        settings = Settings()
    except Exception:
        raise SystemExit(
            "\n[ERROR] No se pudo cargar la configuración.\n"
            "Asegurate de que existe el archivo .env con DATABASE_URL y SECRET_KEY.\n"
            "Podés partir de la plantilla:  cp .env.example .env\n"
        )
    if not settings.secret_key:
        raise SystemExit(
            "\n[ERROR] SECRET_KEY está vacío en el .env.\n"
            "Generá una clave con: python -c \"import secrets; print(secrets.token_hex(64))\"\n"
        )
    return settings
