"""Allow new session types without changing historical codes or rows.

Revision ID: a82d51f4c930
Revises: f2a7c94b1d30
"""
from alembic import op
import sqlalchemy as sa

revision = "a82d51f4c930"
down_revision = "f2a7c94b1d30"
branch_labels = None
depends_on = None

TABLE = "sesiones_entrenamiento"
CONSTRAINT = "ck_sesiones_entrenamiento_tipo"
OLD_TYPES = ("velocidad_sprint", "resistencia", "fuerza", "tecnica_coordinacion",
             "movilidad_recuperacion", "competencia", "entrenamiento_mixto", "otro")
NEW_TYPES = ("aerobico", "lactico", "velocidad")


def _expression(values):
    return "tipo_entrenamiento IN (" + ",".join("'" + value + "'" for value in values) + ")"


def upgrade():
    with op.batch_alter_table(TABLE) as batch:
        batch.drop_constraint(CONSTRAINT, type_="check")
        batch.create_check_constraint(CONSTRAINT, _expression(OLD_TYPES + NEW_TYPES))


def downgrade():
    # Do not silently rewrite or discard new session types.
    bind = op.get_bind()
    count = bind.execute(sa.text(
        "SELECT count(*) FROM sesiones_entrenamiento "
        "WHERE tipo_entrenamiento IN ('aerobico','lactico','velocidad')"
    )).scalar_one()
    if count:
        raise RuntimeError("Downgrade bloqueado: existen sesiones con tipos nuevos.")
    with op.batch_alter_table(TABLE) as batch:
        batch.drop_constraint(CONSTRAINT, type_="check")
        batch.create_check_constraint(CONSTRAINT, _expression(OLD_TYPES))
