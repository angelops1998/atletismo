"""El parte diario: lo que el atleta carga cada dia.

Fase 3: reemplaza el flujo semanal del /parte por el seguimiento diario,
delegando validacion, concurrencia y descarte en los servicios de Phase 2.
"""
from datetime import date, timedelta

import pytest

from app.models.parte import ParteSemanal
from app.models.parte_diaria import ParteDiaria
from app.services import parte_diaria as pd
from conftest import con_csrf, crear_parte, crearadius, entrar


def _session_str(items):
    return "\n".join(
        f"{s.get('id','')}|{s.get('orden',1)}|{s.get('tipo_entrenamiento','resistencia')}"
        f"|{s.get('duracion_min',45)}|{s.get('rpe',6)}|{s.get('comentarios_entrenamiento','')}"
        for s in items
    )


def completo(client, **campos):
    datos = {
        "csrf_token": con_csrf(client, "/parte"),
        "sueno_calidad": "7", "horas_sueno": "7.5", "fatiga": "4",
        "dolor_muscular": "3", "estres": "4", "animo": "8",
        "entreno_hoy": "1",
        "sessions": _session_str([{"orden": 1, "tipo_entrenamiento": "resistencia",
                                   "duracion_min": 45, "rpe": 6}]),
    }
    datos.update(campos)
    return datos


@pytest.fixture
def atleta(db):
    return crearadius(db, username="atleta1", full_name="Un Atleta")