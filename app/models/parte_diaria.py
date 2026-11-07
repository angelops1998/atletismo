"""Registro diario del atleta (seguimiento diario).

Reemplaza funcionalmente al parte semanal (``partes_semanales``/``ParteSemanal``)
en fases posteriores; en Fase 1 solo se agrega el esquema (aditivo). La tabla
semanal y sus datos históricos se conservan intactos hasta la Fase 7 controlada.

- Una fila por (atleta, fecha). ``fecha`` es la fecha local del servidor
  (America/La_Paz, ver ``app.tiempo.hoy``) y la autoridad es del backend.
- Métricas de bienestar 1–10. Fatiga (bienestar) es independiente del RPE de sesión.
- ``entreno_hoy`` indica si hubo entrenamiento; las sesiones viven en
  ``sesiones_entrenamiento``. Las reglas de descarte/confirmación y la
  recomputación autoritativa de cargas se implementan en fases posteriores.
"""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base

# Zonas corporales permitidas para molestias (whitelist de dominio).
MOLESTIA_ZONAS = (
    "cuello",
    "hombros",
    "espalda",
    "cadera",
    "gluteos",
    "muslos",
    "rodillas",
    "pantorrillas",
    "tobillos",
    "pies",
    "brazos",
    "otro",
)


class ParteDiaria(Base):
    __tablename__ = "partes_diarios"
    __table_args__ = (
        UniqueConstraint("atleta_id", "fecha", name="uq_parte_diaria_atleta_fecha"),
        Index("ix_partes_diarios_atleta_fecha", "atleta_id", "fecha"),
        Index("ix_partes_diarios_fecha", "fecha"),
        CheckConstraint("sueno_calidad BETWEEN 1 AND 10", name="ck_partes_diarios_sueno_calidad"),
        CheckConstraint("fatiga BETWEEN 1 AND 10", name="ck_partes_diarios_fatiga"),
        CheckConstraint("dolor_muscular BETWEEN 1 AND 10", name="ck_partes_diarios_dolor_muscular"),
        CheckConstraint("estres BETWEEN 1 AND 10", name="ck_partes_diarios_estres"),
        CheckConstraint("animo BETWEEN 1 AND 10", name="ck_partes_diarios_animo"),
        CheckConstraint(
            "horas_sueno >= 0 AND horas_sueno <= 24",
            name="ck_partes_diarios_horas_sueno",
        ),
        CheckConstraint(
            "molestia_dolor IS NULL OR (molestia_dolor BETWEEN 1 AND 10)",
            name="ck_partes_diarios_molestia_dolor",
        ),
        CheckConstraint(
            "afecta_entrenamiento IS NULL OR (afecta_entrenamiento BETWEEN 0 AND 3)",
            name="ck_partes_diarios_afecta_entrenamiento",
        ),
    )

    id = Column(Integer, primary_key=True)
    atleta_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    # Fecha local (America/La_Paz) determinada por el servidor.
    fecha = Column(Date, nullable=False)

    # Bienestar 1-10 (obligatorios).
    sueno_calidad = Column(Integer, nullable=False)
    fatiga = Column(Integer, nullable=False)
    dolor_muscular = Column(Integer, nullable=False)
    estres = Column(Integer, nullable=False)
    animo = Column(Integer, nullable=False)
    horas_sueno = Column(Numeric(4, 1), nullable=False)

    # Molestias (condicionales; normalización backend en fases posteriores).
    hay_molestia = Column(Boolean, nullable=False, default=False, server_default="false")
    # PostgreSQL ARRAY(String); variante JSON para metadata SQLite (tests).
    molestia_zona = Column(ARRAY(String()).with_variant(JSON, "sqlite"), nullable=True)
    molestia_zona_otra = Column(String(120), nullable=True)
    molestia_dolor = Column(Integer, nullable=True)
    afecta_entrenamiento = Column(Integer, nullable=True)

    # Enfermedad/síntomas (detalle opcional cuando hay síntomas; backend normaliza).
    sintomas_enfermedad = Column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    detalle_sintomas = Column(Text, nullable=True)

    comentarios = Column(Text, nullable=True)
    entreno_hoy = Column(Boolean, nullable=False)

    enviado = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    actualizado = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    sesiones = relationship(
        "SesionEntrenamiento",
        back_populates="parte_diaria",
        cascade="all, delete-orphan",
        order_by="SesionEntrenamiento.orden, SesionEntrenamiento.id",
        passive_deletes=True,
    )
