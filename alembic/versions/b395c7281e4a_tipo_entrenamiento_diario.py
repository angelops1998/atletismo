"""Add an independent daily training classification without changing history."""
from alembic import op
import sqlalchemy as sa

revision = "b395c7281e4a"
down_revision = "a82d51f4c930"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("partes_diarios") as batch:
        batch.add_column(sa.Column("tipo_entrenamiento_diario", sa.String(16), nullable=True))
        batch.create_check_constraint(
            "ck_partes_tipo_entrenamiento_diario",
            "tipo_entrenamiento_diario IS NULL OR tipo_entrenamiento_diario IN ('aerobico','lactico','velocidad','fuerza')",
        )


def downgrade():
    raise RuntimeError("Downgrade bloqueado para conservar las clasificaciones diarias.")
