from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, Text, Numeric
from sqlalchemy.sql import func
from ..database import Base


class User(Base):
    """Profesor y atletas viven en la misma tabla.

    El club tiene un profesor y ~30 afiliados, y todos entran con usuario y
    contraseña: separar "usuario" de "ficha del afiliado" en dos tablas obligaría
    a un JOIN en cada pantalla para no ganar nada. Los campos de la ficha
    deportiva quedan en NULL en la fila del profesor.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(150), nullable=True)
    # role: "profesor" (dueño del club, ve todo) | "atleta" (ve solo lo suyo)
    role = Column(String(20), nullable=False, default="atleta", server_default="atleta")
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")

    # El profesor da de alta al atleta con una contraseña provisoria y se la pasa
    # en mano. Mientras esto sea True, la app lo obliga a cambiarla al entrar:
    # si no, la contraseña que quedó anotada en un papel sigue sirviendo para
    # siempre y varios atletas terminan compartiendo la misma.
    debe_cambiar_password = Column(Boolean, nullable=False, default=False, server_default="false")

    # --- Ficha deportiva (solo atletas) ---
    fecha_nacimiento = Column(Date, nullable=True)
    documento = Column(String(20), nullable=True)
    telefono = Column(String(30), nullable=True)
    # Categoría por edad (Menores, Cadetes, Juveniles, Mayores, Máster…). Texto
    # libre a propósito: cada federación las nombra distinto y cambian de año a año.
    categoria = Column(String(40), nullable=True)
    prueba_principal = Column(String(40), nullable=True)
    fecha_alta = Column(Date, nullable=True)
    contacto_emergencia = Column(String(150), nullable=True)
    # Lesiones previas, alergias, medicación: lo que el profesor necesita saber
    # antes de mandar a alguien a una serie de velocidad.
    observaciones_medicas = Column(Text, nullable=True)

    # --- Cobro (solo atletas) ---
    # Cuota mensual de ESTE atleta: el profesor cobra distinto según el plan, la
    # cantidad de días por semana o si hay hermanos en el club, así que el monto
    # no puede ser único para todos.
    cuota_mensual = Column(Numeric(10, 2), nullable=False, default=0, server_default="0")
    # Desde qué mes se le empieza a cobrar. La deuda se calcula contando los meses
    # entre esta fecha y hoy, y restando los pagos registrados (ver cobranza.py):
    # sin esta fecha, un atleta que entró en marzo aparecería debiendo enero y febrero.
    cobro_desde = Column(Date, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    @property
    def nombre(self) -> str:
        """Cómo se lo nombra en pantalla."""
        return self.full_name or self.username

    def edad(self, referencia=None) -> int | None:
        """Años cumplidos. La categoría y varias referencias de rendimiento
        dependen de la edad, así que se calcula y no se guarda."""
        if not self.fecha_nacimiento:
            return None
        from ..tiempo import hoy as _hoy
        ref = referencia or _hoy()
        return ref.year - self.fecha_nacimiento.year - (
            (ref.month, ref.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
        )
