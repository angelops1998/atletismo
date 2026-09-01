from sqlalchemy import (Column, Integer, String, Date, DateTime, Numeric,
                        ForeignKey, UniqueConstraint)
from sqlalchemy.sql import func
from ..database import Base

METODOS = ("efectivo", "transferencia", "otro")


class Pago(Base):
    """Una cuota cobrada.

    `periodo` es el mes que cubre el pago (guardado como su día 1), y es distinto
    de `fecha_pago`: en marzo se cobra la cuota de marzo, pero también se cobra la
    de febrero que quedó debiendo. Sin separar las dos fechas no hay forma de
    saber qué meses están saldados, que es justamente lo que el profesor pregunta.

    La deuda no se guarda en ninguna columna: se calcula contando los meses desde
    `users.cobro_desde` y restando los períodos pagados (ver services/cobranza.py).
    Así el estado de cuenta no se puede desincronizar y queda auditable pago a pago.
    """
    __tablename__ = "pagos"
    __table_args__ = (
        UniqueConstraint("atleta_id", "periodo", name="uq_pago_atleta_periodo"),
    )

    id = Column(Integer, primary_key=True)
    atleta_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                       index=True, nullable=False)
    periodo = Column(Date, nullable=False, index=True)   # día 1 del mes que cubre
    fecha_pago = Column(Date, nullable=False)
    monto = Column(Numeric(12, 2), nullable=False)
    metodo = Column(String(20), nullable=False, default="efectivo", server_default="efectivo")
    nota = Column(String(200), nullable=True)

    creado = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
