"""Remove redundant explicit unique index for principal workout.

Revision ID: e8a4f670c11d
Revises: b67a104e9c32
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e8a4f670c11d"
down_revision: Union[str, None] = "b67a104e9c32"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "entrenamientos_principales"
COLUMN = "parte_diaria_id"
REDUNDANT_INDEX = "ix_entrenamientos_principales_parte_diaria_id"


def _verify_one_to_one_and_table() -> sa.Inspector:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if TABLE not in inspector.get_table_names():
        raise RuntimeError(
            f"No se encuentra {TABLE}; se cancela la corrección de unicidad."
        )

    unique_constraints = inspector.get_unique_constraints(TABLE)
    has_unique = any(item.get("column_names") == [COLUMN]
                     for item in unique_constraints)
    if not has_unique:
        raise RuntimeError(
            f"{TABLE}.{COLUMN} no tiene la restricción UNIQUE esperada; "
            "se conserva el esquema para evitar perder la cardinalidad uno-a-uno."
        )
    return inspector


def upgrade() -> None:
    inspector = _verify_one_to_one_and_table()
    index_names = {item.get("name") for item in inspector.get_indexes(TABLE)}
    if REDUNDANT_INDEX not in index_names:
        raise RuntimeError(
            f"No se encuentra el índice esperado {REDUNDANT_INDEX}; "
            "no se modifica el esquema inesperado."
        )
    op.drop_index(REDUNDANT_INDEX, table_name=TABLE)


def downgrade() -> None:
    inspector = _verify_one_to_one_and_table()
    index_names = {item.get("name") for item in inspector.get_indexes(TABLE)}
    if REDUNDANT_INDEX in index_names:
        raise RuntimeError(
            f"El índice {REDUNDANT_INDEX} ya existe; no se altera el esquema."
        )
    op.create_index(REDUNDANT_INDEX, TABLE, [COLUMN], unique=True)
