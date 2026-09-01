from sqlalchemy import (Column, Integer, String, Boolean, Date, DateTime, Text,
                        Numeric, ForeignKey, UniqueConstraint, Index)
from sqlalchemy.sql import func
from ..database import Base


class ParteSemanal(Base):
    """Lo que cada atleta carga una vez por semana. Es el corazón del sistema.

    La clave es (atleta_id, semana), donde `semana` es SIEMPRE el lunes de esa
    semana (ver tiempo.lunes_de). Eso es lo que hace que sea "una vez por semana"
    de verdad: el atleta que entra el jueves y el que entra el domingo escriben la
    misma fila, y si vuelve a entrar edita la que ya cargó en vez de duplicarla.

    Las escalas son todas 1–5 y en el MISMO sentido: 5 siempre es lo mejor. Es una
    adaptación del cuestionario de bienestar de Hooper, que es el estándar para
    monitorear deportistas justamente porque se contesta en un minuto. Mezclar
    sentidos (5 = mucho dolor) rompía los promedios sin que nadie lo notara.
    """
    __tablename__ = "partes_semanales"
    __table_args__ = (
        UniqueConstraint("atleta_id", "semana", name="uq_parte_atleta_semana"),
        Index("ix_partes_semana", "semana"),
    )

    id = Column(Integer, primary_key=True)
    atleta_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                       index=True, nullable=False)
    # Lunes de la semana que describe el parte.
    semana = Column(Date, nullable=False)

    # --- Bienestar (1 = muy mal … 5 = muy bien) ---
    sueno_calidad = Column(Integer, nullable=False)     # ¿Cómo dormiste?
    fatiga = Column(Integer, nullable=False)            # Nivel de energía
    dolor_muscular = Column(Integer, nullable=False)    # 5 = sin dolor
    estres = Column(Integer, nullable=False)            # 5 = tranquilo
    animo = Column(Integer, nullable=False)             # Ánimo general

    # --- Sueño ---
    horas_sueno = Column(Numeric(3, 1), nullable=True)  # promedio por noche

    # --- Alimentación ---
    comidas_dia = Column(Integer, nullable=True)
    alimentacion_calidad = Column(Integer, nullable=True)   # 1–5 contra el plan
    hidratacion_litros = Column(Numeric(3, 1), nullable=True)
    # Entrenar en ayunas es de los motivos más frecuentes de bajón en el
    # entrenamiento de la tarde, y el atleta no lo relaciona solo.
    come_antes_entrenar = Column(Boolean, nullable=True)
    suplementos = Column(String(200), nullable=True)

    # --- Cuerpo ---
    peso_kg = Column(Numeric(5, 2), nullable=True)

    # --- Carga de entrenamiento ---
    sesiones = Column(Integer, nullable=True)
    minutos_totales = Column(Integer, nullable=True)
    # Esfuerzo percibido 1–10 (escala de Borg modificada). Con los minutos da la
    # carga por sRPE, que es como se detectan los saltos de carga (ver alertas.py).
    rpe = Column(Integer, nullable=True)

    # --- Molestias / lesiones ---
    molestias = Column(Boolean, nullable=False, default=False, server_default="false")
    molestia_zona = Column(String(80), nullable=True)
    molestia_dolor = Column(Integer, nullable=True)     # 0–10

    comentarios = Column(Text, nullable=True)

    enviado = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    actualizado = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
