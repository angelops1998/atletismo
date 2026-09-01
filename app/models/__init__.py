"""Importa todos los modelos para que Alembic los vea al autogenerar migraciones."""
from .user import User            # noqa: F401
from .parte import ParteSemanal   # noqa: F401
from .marca import Marca          # noqa: F401
from .asistencia import Asistencia  # noqa: F401
from .pago import Pago            # noqa: F401
