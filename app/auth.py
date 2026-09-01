from datetime import datetime, timedelta, timezone
from typing import Optional
import hashlib
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from .database import get_db
from .models.user import User
from .config import get_settings

settings = get_settings()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def huella_password(hashed_password: str) -> str:
    """Un resumen corto del hash de la contraseña, que viaja dentro del token.

    Es lo que hace que cambiar la contraseña cierre las sesiones abiertas en otros
    aparatos. Sin esto, el token seguía valiendo 60 días: si la provisoria que el
    profesor anotó en un papel se filtró, cambiarla no echaba a quien ya había
    entrado con ella, que es justo el caso para el que existe el cambio obligado.

    Se deriva del hash y no de una columna nueva porque bcrypt genera una sal
    distinta cada vez: cambia sola en cada cambio de contraseña, incluido el
    reseteo que hace el profesor, sin nada que acordarse de actualizar.
    """
    return hashlib.sha256(hashed_password.encode()).hexdigest()[:16]


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def set_auth_cookie(response, token: str) -> None:
    """Deja la cookie de sesión con la misma vida que el token que lleva adentro."""
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=settings.access_token_expire_minutes * 60,
        samesite="lax",
        secure=settings.https_only,
    )


def refrescar_token(token: str) -> Optional[str]:
    """Si al token le queda menos de la mitad de vida, devuelve uno nuevo.

    Es lo que hace que la sesión sea deslizante. Importa sobre todo para el
    atleta, que entra una vez por semana desde el celular: sin esto la sesión se
    le vencería entre parte y parte y tendría que recordar la contraseña cada vez.
    Devuelve None si no hace falta renovar o si el token no sirve.
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None
    username = payload.get("sub")
    exp = payload.get("exp")
    huella = payload.get("pv")
    # Sin huella el token ya no vale para nada (ver get_current_user_optional):
    # renovarlo solo serviría para que una cookie muerta se arrastre para siempre.
    if not username or not exp or not huella:
        return None
    restante = datetime.fromtimestamp(exp, timezone.utc) - datetime.now(timezone.utc)
    if restante > timedelta(minutes=settings.access_token_expire_minutes) / 2:
        return None
    # La huella se arrastra tal cual: renovar no revalida nada, y un token de una
    # contraseña vieja tiene que seguir siendo inválido después de renovarse.
    return create_access_token(data={"sub": username, "pv": huella})


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()


def authenticate_user(db: Session, identificador: str, password: str) -> Optional[User]:
    """Acepta email o nombre de usuario.

    Los atletas son chicos y adultos que entran una vez por semana: pedirles el
    email exacto era la principal fuente de logins fallidos, y varios ni siquiera
    tienen correo propio. Por eso el profesor les da un usuario corto y se puede
    entrar con cualquiera de los dos.
    """
    identificador = identificador.strip().lower()
    if not identificador:
        return None
    user = get_user_by_email(db, identificador) or get_user_by_username(db, identificador)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def get_token_from_cookie(request: Request) -> Optional[str]:
    return request.cookies.get("access_token")


def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Devuelve el usuario actual si está autenticado, o None."""
    token = get_token_from_cookie(request)
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: str = payload.get("sub")
        if not username:
            return None
    except JWTError:
        return None
    user = get_user_by_username(db, username)
    if not user:
        return None
    # Token emitido con otra contraseña (o sin huella, de antes de que existiera):
    # no vale. Al soltar este cambio todos entran una vez más, y listo.
    if payload.get("pv") != huella_password(user.hashed_password):
        return None
    return user


class NotAuthenticatedException(Exception):
    def __init__(self, next_url: str = "/"):
        self.next_url = next_url


class DebeCambiarPassword(Exception):
    """El usuario todavía tiene la contraseña provisoria que le dio el profesor."""


def get_current_user_libre(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """El usuario actual, SIN exigirle que cambie la contraseña provisoria.

    Lo usa la pantalla de cuenta: es adonde se lo manda justamente para que la
    cambie, así que exigirle ahí el cambio lo dejaría en un redirect infinito.
    """
    user = get_current_user_optional(request, db)
    if not user:
        raise NotAuthenticatedException(next_url=request.url.path)
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Tu cuenta está desactivada.")
    return user


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """Devuelve el usuario actual, o redirige al login / al cambio de contraseña.

    El control de la contraseña provisoria vive acá y no en cada router: si
    dependiera de que cada pantalla se acuerde de chequearlo, alcanzaría con que
    una sola se olvidara para que la contraseña que el profesor anotó en un papel
    siguiera sirviendo para siempre.
    """
    user = get_current_user_libre(request, db)
    if user.debe_cambiar_password:
        raise DebeCambiarPassword()
    return user


def get_current_profesor(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """Como get_current_user, pero exige rol profesor.

    Todo lo que sea del club (padrón, pagos, estadísticas del grupo) pasa por acá.
    Un atleta que llegue a esas rutas recibe 403: nunca ve datos de otro atleta.
    """
    user = get_current_user(request, db)
    if user.role != "profesor":
        raise HTTPException(status_code=403, detail="Solo el profesor puede ver esto.")
    return user
