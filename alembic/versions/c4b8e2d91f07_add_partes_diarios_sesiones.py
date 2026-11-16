"""agrega partes diarias y sesiones de entrenamiento (aditivo)

Fase 1 del reemplazo del parte semanal por seguimiento diario. Crea
``partes_diarios`` y ``sesiones_entrenamiento`` con constraints/índices.
No modifica ni elimina ``partes_semanales`` ni datos históricos.

Revision ID: c4b8e2d91f07
Revises: a3f1c9e27b04
Create Date: 2026-11-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c4b8e2d91f07"
down_revision: Union[str, None] = "a3f1c9e27b04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "partes_diarios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("atleta_id", sa.Integer(), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("sueno_calidad", sa.Integer(), nullable=False),
        sa.Column("fatiga", sa.Integer(), nullable=False),
        sa.Column("dolor_muscular", sa.Integer(), nullable=False),
        sa.Column("estres", sa.Integer(), nullable=False),
        sa.Column("animo", sa.Integer(), nullable=False),
        sa.Column("horas_sueno", sa.Numeric(precision=4, scale=1), nullable=False),
        sa.Column(
            "hay_molestia",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("molestia_zona", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("molestia_zona_otra", sa.String(length=120), nullable=True),
        sa.Column("molestia_dolor", sa.Integer(), nullable=True),
        sa.Column("afecta_entrenamiento", sa.Integer(), nullable=True),
        sa.Column(
            "sintomas_enfermedad",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("detalle_sintomas", sa.Text(), nullable=True),
        sa.Column("comentarios", sa.Text(), nullable=True),
        sa.Column("entreno_hoy", sa.Boolean(), nullable=False),
        sa.Column(
            "enviado",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("actualizado", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("sueno_calidad BETWEEN 1 AND 10", name="ck_partes_diarios_sueno_calidad"),
        sa.CheckConstraint("fatiga BETWEEN 1 AND 10", name="ck_partes_diarios_fatiga"),
        sa.CheckConstraint("dolor_muscular BETWEEN 1 AND 10", name="ck_partes_diarios_dolor_muscular"),
        sa.CheckConstraint("estres BETWEEN 1 AND 10", name="ck_partes_diarios_estres"),
        sa.CheckConstraint("animo BETWEEN 1 AND 10", name="ck_partes_diarios_animo"),
        sa.CheckConstraint(
            "horas_sueno >= 0 AND horas_sueno <= 24",
            name="ck_partes_diarios_horas_sueno",
        ),
        sa.CheckConstraint(
            "molestia_dolor IS NULL OR (molestia_dolor BETWEEN 1 AND 10)",
            name="ck_partes_diarios_molestia_dolor",
        ),
        sa.CheckConstraint(
            "afecta_entrenamiento IS NULL OR (afecta_entrenamiento BETWEEN 0 AND 3)",
            name="ck_partes_diarios_afecta_entrenamiento",
        ),
        sa.ForeignKeyConstraint(["atleta_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("atleta_id", "fecha", name="uq_parte_diaria_atleta_fecha"),
    )
    op.create_index(op.f("ix_partes_diarios_atleta_id"), "partes_diarios", ["atleta_id"], unique=False)
    op.create_index("ix_partes_diarios_atleta_fecha", "partes_diarios", ["atleta_id", "fecha"], unique=False)
    op.create_index("ix_partes_diarios_fecha", "partes_diarios", ["fecha"], unique=False)

    op.create_table(
        "sesiones_entrenamiento",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("parte_diaria_id", sa.Integer(), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("tipo_entrenamiento", sa.String(length=40), nullable=False),
        sa.Column("duracion_min", sa.Integer(), nullable=False),
        sa.Column("rpe", sa.Integer(), nullable=False),
        sa.Column("carga_sesion", sa.Integer(), nullable=False),
        sa.Column("comentarios_entrenamiento", sa.Text(), nullable=True),
        sa.Column(
            "creado",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("duracion_min > 0", name="ck_sesiones_entrenamiento_duracion_min"),
        sa.CheckConstraint("rpe BETWEEN 1 AND 10", name="ck_sesiones_entrenamiento_rpe"),
        sa.CheckConstraint("carga_sesion >= 0", name="ck_sesiones_entrenamiento_carga_sesion"),
        sa.CheckConstraint(
            "tipo_entrenamiento IN ("
            "'velocidad_sprint','resistencia','fuerza','tecnica_coordinacion',"
            "'movilidad_recuperacion','competencia','entrenamiento_mixto','otro'"
            ")",
            name="ck_sesiones_entrenamiento_tipo",
        ),
        sa.ForeignKeyConstraint(["parte_diaria_id"], ["partes_diarios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_sesiones_entrenamiento_parte_diaria",
        "sesiones_entrenamiento",
        ["parte_diaria_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_sesiones_entrenamiento_parte_diaria", table_name="sesiones_entrenamiento")
    op.drop_table("sesiones_entrenamiento")
    op.drop_index("ix_partes_diarios_fecha", table_name="partes_diarios")
    op.drop_index("ix_partes_diarios_atleta_fecha", table_name="partes_diarios")
    op.drop_index(op.f("ix_partes_diarios_atleta_id"), table_name="partes_diarios")
    op.drop_table("partes_diarios")
