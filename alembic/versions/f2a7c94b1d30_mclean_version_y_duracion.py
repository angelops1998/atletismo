"""Prepare separate McLean answers and identify session duration semantics.

Revision ID: f2a7c94b1d30
Revises: e8a4f670c11d
"""
from alembic import op
import sqlalchemy as sa

revision = "f2a7c94b1d30"
down_revision = "e8a4f670c11d"
branch_labels = None
depends_on = None

LEGACY_FIELDS = ("sueno_calidad", "fatiga", "dolor_muscular", "estres", "animo")
MCLEAN_FIELDS = ("mclean_sueno", "mclean_fatiga", "mclean_dolor_muscular", "mclean_estres", "mclean_animo")


def upgrade():
    with op.batch_alter_table("partes_diarios") as batch:
        batch.add_column(sa.Column("version_cuestionario", sa.String(20), nullable=False,
                                   server_default="historico_1_10"))
        for field in MCLEAN_FIELDS:
            batch.add_column(sa.Column(field, sa.Integer(), nullable=True))
        for field in LEGACY_FIELDS:
            batch.alter_column(field, existing_type=sa.Integer(), nullable=True)
        legacy_required = " AND ".join(f"{f} IS NOT NULL" for f in LEGACY_FIELDS)
        legacy_empty = " AND ".join(f"{f} IS NULL" for f in LEGACY_FIELDS)
        mclean_empty = " AND ".join(f"{f} IS NULL" for f in MCLEAN_FIELDS)
        mclean_valid = " AND ".join(f"{f} IS NOT NULL AND {f} BETWEEN 1 AND 5" for f in MCLEAN_FIELDS)
        batch.create_check_constraint(
            "ck_partes_diarios_version_bienestar",
            f"(version_cuestionario = 'historico_1_10' AND {legacy_required} AND {mclean_empty}) OR "
            f"(version_cuestionario = 'mclean_1_5' AND {legacy_empty} AND {mclean_valid})",
        )
    with op.batch_alter_table("sesiones_entrenamiento") as batch:
        batch.add_column(sa.Column("tipo_duracion", sa.String(20), nullable=False,
                                   server_default="no_especificada"))
        batch.create_check_constraint(
            "ck_sesiones_tipo_duracion",
            "tipo_duracion IN ('no_especificada', 'trabajo_principal')",
        )


def downgrade():
    # Removing either column family could silently discard real answers or meaning.
    raise RuntimeError("Downgrade no disponible: conservar respuestas y semántica de duración; requiere una migración de recuperación explícita.")
