"""Add optional principal workout structure to training sessions.

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
    for name in (
        "estructura_tipo", "series", "repeticiones_por_serie", "distancia_m",
        "descanso_micro_min_s", "descanso_micro_max_s", "descanso_macro_min_s",
        "descanso_macro_max_s", "tiempo_rep_min_s", "tiempo_rep_max_s",
    ):
        op.add_column("sesiones_entrenamiento", sa.Column(name, sa.Integer(), nullable=True))
    op.alter_column("sesiones_entrenamiento", "estructura_tipo", type_=sa.String(16))
    op.create_check_constraint(
        "ck_sesiones_estructura_tipo",
        "sesiones_entrenamiento",
        "estructura_tipo IS NULL OR estructura_tipo IN ('aerobico', 'velocidad')",
    )
    for name in ("series", "repeticiones_por_serie", "distancia_m"):
        op.create_check_constraint(
            f"ck_sesiones_{name}_positivo",
            "sesiones_entrenamiento",
            f"{name} IS NULL OR {name} > 0",
        )
    for low, high in (
        ("descanso_micro_min_s", "descanso_micro_max_s"),
        ("descanso_macro_min_s", "descanso_macro_max_s"),
        ("tiempo_rep_min_s", "tiempo_rep_max_s"),
    ):
        op.create_check_constraint(
            f"ck_sesiones_{low}_rango",
            "sesiones_entrenamiento",
            f"({low} IS NULL AND {high} IS NULL) OR ({low} >= 0 AND {high} >= {low})",
        )


def downgrade() -> None:
    for name in ("descanso_micro_min_s", "descanso_macro_min_s", "tiempo_rep_min_s"):
        op.drop_constraint(f"ck_sesiones_{name}_rango", "sesiones_entrenamiento", type_="check")
    for name in ("series", "repeticiones_por_serie", "distancia_m"):
        op.drop_constraint(f"ck_sesiones_{name}_positivo", "sesiones_entrenamiento", type_="check")
    op.drop_constraint("ck_sesiones_estructura_tipo", "sesiones_entrenamiento", type_="check")
    for name in (
        "estructura_tipo", "series", "repeticiones_por_serie", "distancia_m",
        "descanso_micro_min_s", "descanso_micro_max_s", "descanso_macro_min_s",
        "descanso_macro_max_s", "tiempo_rep_min_s", "tiempo_rep_max_s",
    ):
        op.drop_column("sesiones_entrenamiento", name)
