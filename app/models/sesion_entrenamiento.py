"""Sesión de entrenamiento asociada a un ``ParteDiaria``.

Cada registro diario puede tener múltiples sesiones. ``carga_sesion`` se
almacena como entero (duración × RPE); la recomputación autoritativa en backend
y las operaciones transaccionales/confirmación de descarte se implementan en
fases posteriores.
"""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base

# Tipos de entrenamiento permitidos (whitelist de dominio).
TIPOS_ENTRENAMIENTO = (
    "velocidad_sprint",
    "resistencia",
    "fuerza",
    "tecnica_coordinacion",
    "movilidad_recuperacion",
    "competencia",
    "entrenamiento_mixto",
    "otro",
)


class SesionEntrenamiento(Base):
    __tablename__ = "sesiones_entrenamiento"
    __table_args__ = (
        Index("ix_sesiones_entrenamiento_parte_diaria", "parte_diaria_id"),
        CheckConstraint("duracion_min > 0", name="ck_sesiones_entrenamiento_duracion_min"),
        CheckConstraint("rpe BETWEEN 1 AND 10", name="ck_sesiones_entrenamiento_rpe"),
        CheckConstraint("carga_sesion >= 0", name="ck_sesiones_entrenamiento_carga_sesion"),
        CheckConstraint(
            "tipo_entrenamiento IN ("
            "'velocidad_sprint','resistencia','fuerza','tecnica_coordinacion',"
            "'movilidad_recuperacion','competencia','entrenamiento_mixto','otro'"
            ")",
            name="ck_sesiones_entrenamiento_tipo",
        ),
    )

    id = Column(Integer, primary_key=True)
    parte_diaria_id = Column(
        Integer,
        ForeignKey("partes_diarios.id", ondelete="CASCADE"),
        nullable=False,
    )
    orden = Column(Integer, nullable=False)
    tipo_entrenamiento = Column(String(40), nullable=False)
    duracion_min = Column(Integer, nullable=False)
    rpe = Column(Integer, nullable=False)
    carga_sesion = Column(Integer, nullable=False)
    comentarios_entrenamiento = Column(Text, nullable=True)

    creado = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    parte_diaria = relationship("ParteDiaria", back_populates="sesiones")
