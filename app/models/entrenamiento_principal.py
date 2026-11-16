"""Estructura planificada del entrenamiento principal de un parte diario."""
from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from ..database import Base


class EntrenamientoPrincipal(Base):
    __tablename__ = "entrenamientos_principales"
    __table_args__ = (
        CheckConstraint("estructura_tipo IN ('aerobico', 'velocidad')", name="ck_entrenamiento_principal_tipo"),
        CheckConstraint("series > 0 AND repeticiones_por_serie > 0 AND distancia_m > 0", name="ck_entrenamiento_principal_cantidades"),
        CheckConstraint("descanso_micro_min_s >= 0 AND descanso_micro_max_s >= descanso_micro_min_s", name="ck_entrenamiento_principal_micro"),
        CheckConstraint("descanso_macro_min_s >= 0 AND descanso_macro_max_s >= descanso_macro_min_s", name="ck_entrenamiento_principal_macro"),
        CheckConstraint("tiempo_rep_min_s >= 0 AND tiempo_rep_max_s >= tiempo_rep_min_s", name="ck_entrenamiento_principal_tiempo"),
    )

    id = Column(Integer, primary_key=True)
    parte_diaria_id = Column(Integer, ForeignKey("partes_diarios.id", ondelete="CASCADE"), nullable=False, unique=True)
    estructura_tipo = Column(String(16), nullable=False)
    series = Column(Integer, nullable=False)
    repeticiones_por_serie = Column(Integer, nullable=False)
    distancia_m = Column(Integer, nullable=False)
    descanso_micro_min_s = Column(Integer, nullable=False)
    descanso_micro_max_s = Column(Integer, nullable=False)
    descanso_macro_min_s = Column(Integer, nullable=False)
    descanso_macro_max_s = Column(Integer, nullable=False)
    tiempo_rep_min_s = Column(Integer, nullable=False)
    tiempo_rep_max_s = Column(Integer, nullable=False)

    parte_diaria = relationship("ParteDiaria", back_populates="entrenamiento_principal")
