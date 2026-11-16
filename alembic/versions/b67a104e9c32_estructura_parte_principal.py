"""Add structured principal workout per daily record.

Revision ID: b67a104e9c32
Revises: c4b8e2d91f07
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "b67a104e9c32"
down_revision: Union[str, None] = "c4b8e2d91f07"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "entrenamientos_principales",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("parte_diaria_id", sa.Integer(), sa.ForeignKey("partes_diarios.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("estructura_tipo", sa.String(16), nullable=False),
        sa.Column("series", sa.Integer(), nullable=False),
        sa.Column("repeticiones_por_serie", sa.Integer(), nullable=False),
        sa.Column("distancia_m", sa.Integer(), nullable=False),
        sa.Column("descanso_micro_min_s", sa.Integer(), nullable=False),
        sa.Column("descanso_micro_max_s", sa.Integer(), nullable=False),
        sa.Column("descanso_macro_min_s", sa.Integer(), nullable=False),
        sa.Column("descanso_macro_max_s", sa.Integer(), nullable=False),
        sa.Column("tiempo_rep_min_s", sa.Integer(), nullable=False),
        sa.Column("tiempo_rep_max_s", sa.Integer(), nullable=False),
        sa.CheckConstraint("estructura_tipo IN ('aerobico','velocidad')", name="ck_entrenamiento_principal_tipo"),
        sa.CheckConstraint("series > 0 AND repeticiones_por_serie > 0 AND distancia_m > 0", name="ck_entrenamiento_principal_cantidades"),
        sa.CheckConstraint("descanso_micro_min_s >= 0 AND descanso_micro_max_s >= descanso_micro_min_s", name="ck_entrenamiento_principal_micro"),
        sa.CheckConstraint("descanso_macro_min_s >= 0 AND descanso_macro_max_s >= descanso_macro_min_s", name="ck_entrenamiento_principal_macro"),
        sa.CheckConstraint("tiempo_rep_min_s >= 0 AND tiempo_rep_max_s >= tiempo_rep_min_s", name="ck_entrenamiento_principal_tiempo"),
    )
    op.create_index("ix_entrenamientos_principales_parte_diaria_id", "entrenamientos_principales", ["parte_diaria_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_entrenamientos_principales_parte_diaria_id", table_name="entrenamientos_principales")
    op.drop_table("entrenamientos_principales")
