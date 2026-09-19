"""fatiga opcional: el RPE reemplaza al ítem de energía del parte

El club pidió sacar la pregunta "Energía" del parte semanal y que el atleta
registre en su lugar el RPE (1–10). La columna `fatiga` se conserva con lo que
ya se cargó, pero los partes nuevos no la completan, así que deja de ser NOT NULL.

Revision ID: a3f1c9e27b04
Revises: d61e48816ec5
Create Date: 2026-09-19 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a3f1c9e27b04'
down_revision: Union[str, None] = 'd61e48816ec5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('partes_semanales', 'fatiga',
                    existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    # Los partes cargados sin energía no pueden volver a NOT NULL: se les pone
    # un 3 ("normal") para que la restricción se pueda restaurar.
    op.execute("UPDATE partes_semanales SET fatiga = 3 WHERE fatiga IS NULL")
    op.alter_column('partes_semanales', 'fatiga',
                    existing_type=sa.Integer(), nullable=False)
