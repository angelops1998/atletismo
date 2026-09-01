from sqlalchemy import (Column, Integer, String, Date, DateTime, ForeignKey,
                        UniqueConstraint)
from sqlalchemy.sql import func
from ..database import Base

# Un atleta no puede tener dos estados el mismo día: tomar lista dos veces
# corrige la fila anterior en vez de agregar una nueva.
ESTADOS = ("presente", "ausente", "justificado")


class Asistencia(Base):
    """Lista de un día de entrenamiento.

    Sirve para dos cosas: ver quién está viniendo (un atleta que falta tres
    semanas seguidas normalmente está por darse de baja, y el profesor prefiere
    llamarlo antes) y darle contexto a las marcas y al bienestar.
    """
    __tablename__ = "asistencias"
    __table_args__ = (
        UniqueConstraint("atleta_id", "fecha", name="uq_asistencia_atleta_fecha"),
    )

    id = Column(Integer, primary_key=True)
    atleta_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                       index=True, nullable=False)
    fecha = Column(Date, nullable=False, index=True)
    estado = Column(String(15), nullable=False, default="presente", server_default="presente")
    nota = Column(String(200), nullable=True)

    creado = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
