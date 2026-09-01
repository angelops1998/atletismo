from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, Numeric, ForeignKey
from sqlalchemy.sql import func
from ..database import Base


class Marca(Base):
    """Un resultado del atleta en una prueba, fechado.

    El valor va en una sola columna numérica y qué significa lo define la prueba
    (segundos en 100 m, metros en salto largo): el catálogo con la unidad y el
    sentido —si menos es mejor o más es mejor— está en services/pruebas.py y no en
    la base, porque es una lista fija que no la edita nadie desde la app.
    """
    __tablename__ = "marcas"

    id = Column(Integer, primary_key=True)
    atleta_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                       index=True, nullable=False)
    prueba = Column(String(40), nullable=False, index=True)
    fecha = Column(Date, nullable=False, index=True)
    valor = Column(Numeric(8, 3), nullable=False)

    # Viento a favor (+) o en contra (-) en m/s. En velocidad y salto largo una
    # marca con más de +2.0 no es homologable, así que sin esto el profesor no
    # puede saber si una mejora es real o fue el viento.
    viento = Column(Numeric(4, 2), nullable=True)
    # Una marca de competencia y una de entrenamiento no se comparan de igual a
    # igual: en competencia siempre se rinde más.
    es_competencia = Column(Boolean, nullable=False, default=False, server_default="false")
    competencia = Column(String(120), nullable=True)
    lugar = Column(String(120), nullable=True)
    nota = Column(String(200), nullable=True)

    creado = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
