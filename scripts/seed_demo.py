"""Inicializador idempotente de datos del entorno demo local.

Crea las cuentas de demostración y un conjunto reducido de datos de ejemplo
sobre la base de datos dedicada ``atletismo_demo``. Nunca toca registros ajenos:
solo crea o actualiza registros cuya titularidad es claramente demo.

La titularidad demo se marca con el dominio de email dedicado
``@atletismo.demo.local`` (campo soportado, unico e indexado), combinado con los
nombres de usuario estables definidos abajo. Nunca se asume titularidad solo
por el nombre de usuario.

Uso:
    python scripts/seed_demo.py                 # crea/actualiza los datos demo
    python scripts/seed_demo.py --borrar-demo   # borra SOLO los datos demo
                                                 (requiere --confirmar-borrar-demo)

No modifica el flujo semanal existente (scripts/seed.py) ni datos ajenos al demo.
"""

import random
import sys
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal                      # noqa: E402
from app.models.user import User                           # noqa: E402
from app.models.parte import ParteSemanal                  # noqa: E402
from app.models.parte_diaria import ParteDiaria            # noqa: E402
from app.models.sesion_entrenamiento import SesionEntrenamiento  # noqa: E402
from app.models.marca import Marca                         # noqa: E402
from app.models.asistencia import Asistencia               # noqa: E402
from app.models.pago import Pago                           # noqa: E402
from app.auth import hash_password                         # noqa: E402
from app.services import cobranza                          # noqa: E402
from app.tiempo import hoy, lunes_actual                   # noqa: E402

# --- Titularidad demo (marcador explícito, campo soportado) ---------------
DEMO_EMAIL_DOMAIN = "@atletismo.demo.local"

DEMO_PROFESOR = {
    "username": "demo_profesor",
    "password": "DemoProfe2026!",
    "full_name": "Profesor Demo",
    "role": "profesor",
}

DEMO_ATLETAS = [
    {
        "username": "demo_atleta1",
        "password": "DemoAtleta2026!",
        "full_name": "Lucía Demo",
        "categoria": "Juveniles",
        "prueba_principal": "100 m llanos",
        "cuota_mensual": Decimal("150.00"),
    },
    {
        "username": "demo_atleta2",
        "password": "DemoAtleta2026!",
        "full_name": "Mateo Demo",
        "categoria": "Mayores",
        "prueba_principal": "400 m llanos",
        "cuota_mensual": Decimal("150.00"),
    },
    {
        "username": "demo_atleta3",
        "password": "DemoAtleta2026!",
        "full_name": "Camila Demo",
        "categoria": "Juveniles",
        "prueba_principal": "Salto en largo",
        "cuota_mensual": Decimal("150.00"),
    },
]

DEMO_USERNAMES = {DEMO_PROFESOR["username"]} | {a["username"] for a in DEMO_ATLETAS}

HOY = hoy()
AYER = HOY - timedelta(days=1)
MES_ACTUAL = cobranza.primer_dia(HOY)


def _email_de(username: str) -> str:
    """Email de dominio dedicado: el marcador de titularidad demo."""
    return f"{username}{DEMO_EMAIL_DOMAIN}"


def _es_entorno_demo(db) -> None:
    """Valida que la base de destino sea la dedicada al demo.

    Se llama antes de borrar o escribir. Rechaza cualquier base que no sea
    atletismo_demo en localhost, para nunca tocar una base ajena o de produccion.
    """
    from app.config import get_settings
    settings = get_settings()
    url = settings.database_url
    if "atletismo_demo" not in url:
        raise SystemExit(
            f"[ERROR] La base configurada no es la dedicada al demo: {url}\n"
            "El initializer solo escribe sobre la base de demostracion."
        )
    if "localhost" not in url and "127.0.0.1" not in url:
        raise SystemExit(
            f"[ERROR] La base no pertenece a una instancia local aprobada: {url}"
        )


def _es_demo(usuario: User) -> bool:
    """Un registro es demo si su email usa el dominio dedicado y su usuario es
    uno de los estables de demostracion (doble chequeo, nunca solo por username)."""
    email = (usuario.email or "").lower()
    return email.endswith(DEMO_EMAIL_DOMAIN) and usuario.username in DEMO_USERNAMES


def _ids_atletas_demo(db) -> list[int]:
    """IDs de atletas demo, identificados por el dominio de email dedicado."""
    return [
        u.id for u in db.query(User)
        .filter(User.email.like(f"%{DEMO_EMAIL_DOMAIN}"))
        .filter(User.role == "atleta")
        .all()
    ]


def _ensure_user(db, data: dict) -> User:
    """Crea o actualiza una cuenta demo. La contraseña se hashea con el
    mecanismo real de la app (bcrypt, app.auth.hash_password)."""
    usuario = db.query(User).filter(User.username == data["username"]).first()
    es_nuevo = usuario is None
    if es_nuevo:
        usuario = User(username=data["username"], role=data["role"])
        db.add(usuario)

    # Titularidad explícita: email de dominio dedicado.
    usuario.email = _email_de(data["username"])
    usuario.hashed_password = hash_password(data["password"])
    usuario.full_name = data["full_name"]
    usuario.role = data["role"]
    usuario.is_active = True
    # Contraseña real de demo: no se exige cambio al entrar.
    usuario.debe_cambiar_password = False
    if es_nuevo:
        usuario.fecha_alta = HOY

    if data["role"] == "atleta":
        usuario.fecha_nacimiento = HOY - timedelta(days=365 * 17)
        usuario.documento = "12345678"
        usuario.telefono = "+591 70000000"
        usuario.categoria = data["categoria"]
        usuario.prueba_principal = data["prueba_principal"]
        usuario.contacto_emergencia = "Familiar Demo — +591 70000001"
        usuario.observaciones_medicas = "Cuenta de demostración del entorno local."
        usuario.cuota_mensual = data["cuota_mensual"]
        # Se empieza a cobrar este mes: la deuda se ve clara en el estado de cuenta.
        usuario.cobro_desde = MES_ACTUAL

    return usuario


def _borrar_datos_demo(db, atleta_ids: list[int], borrar_usuarios: bool = False) -> None:
    """Borra SOLO registros pertenecientes a atletas demo (titularidad explícita).

    Nunca borra registros ajenos. ParteDiaria borra sus sesiones en cascada a
    nivel de base de datos (ondelete=CASCADE).
    """
    if not atleta_ids:
        return
    for modelo in (ParteDiaria, Marca, Pago, Asistencia, ParteSemanal):
        db.query(modelo).filter(
            modelo.atleta_id.in_(atleta_ids)
        ).delete(synchronize_session=False)
    if borrar_usuarios:
        for uid in atleta_ids:
            u = db.query(User).get(uid)
            if u is not None and _es_demo(u):
                db.delete(u)
        profesor = db.query(User).filter(
            User.username == DEMO_PROFESOR["username"],
            User.email.like(f"%{DEMO_EMAIL_DOMAIN}"),
        ).first()
        if profesor is not None and _es_demo(profesor):
            db.delete(profesor)


def _crear_partes_diarios(db, atletas: dict) -> None:
    """Registros diarios de hoy (y uno ayer) que cubren los escenarios de demo.

    1. demo_atleta1: parte completo, entrenó, múltiples sesiones + molestia.
    2. demo_atleta2: parte sin entrenamiento (entreno_hoy = false).
    3. demo_atleta3: SIN parte hoy (falta de reporte); sí reportó síntomas ayer.
    """
    a1 = atletas["demo_atleta1"]
    a2 = atletas["demo_atleta2"]
    a3 = atletas["demo_atleta3"]

    # 1. Parte completo, varios entrenamientos y una molestia.
    p1 = ParteDiaria(
        atleta_id=a1.id, fecha=HOY,
        sueno_calidad=7, fatiga=4, dolor_muscular=3, estres=4, animo=6,
        horas_sueno=Decimal("7.5"),
        hay_molestia=True, molestia_zona=["rodillas"], molestia_zona_otra=None,
        molestia_dolor=6, afecta_entrenamiento=2,
        sintomas_enfermedad=False, detalle_sintomas=None,
        comentarios="Sesión de velocidad y fuerza. Rodillas cargadas al final.",
        entreno_hoy=True,
    )
    db.add(p1)
    db.flush()
    db.add_all([
        SesionEntrenamiento(
            parte_diaria_id=p1.id, orden=1,
            tipo_entrenamiento="velocidad_sprint", duracion_min=45, rpe=7,
            carga_sesion=45 * 7, comentarios_entrenamiento="Series de 60 m.",
        ),
        SesionEntrenamiento(
            parte_diaria_id=p1.id, orden=2,
            tipo_entrenamiento="fuerza", duracion_min=60, rpe=6,
            carga_sesion=60 * 6, comentarios_entrenamiento="Tren inferior.",
        ),
    ])

    # 2. Parte sin entrenamiento.
    p2 = ParteDiaria(
        atleta_id=a2.id, fecha=HOY,
        sueno_calidad=8, fatiga=2, dolor_muscular=2, estres=3, animo=7,
        horas_sueno=Decimal("8.0"),
        hay_molestia=False, molestia_zona=None, molestia_zona_otra=None,
        molestia_dolor=None, afecta_entrenamiento=None,
        sintomas_enfermedad=False, detalle_sintomas=None,
        comentarios="Día de descanso, no entrené.",
        entreno_hoy=False,
    )
    db.add(p2)

    # 3. Sin parte hoy (falta de reporte). Ayer sí reportó síntomas.
    p3 = ParteDiaria(
        atleta_id=a3.id, fecha=AYER,
        sueno_calidad=4, fatiga=8, dolor_muscular=4, estres=5, animo=3,
        horas_sueno=Decimal("5.5"),
        hay_molestia=False, molestia_zona=None, molestia_zona_otra=None,
        molestia_dolor=None, afecta_entrenamiento=None,
        sintomas_enfermedad=True, detalle_sintomas="Fiebre y tos leve.",
        comentarios="No entrené por malestar.",
        entreno_hoy=False,
    )
    db.add(p3)


def _crear_partes_semanales(db, atletas: dict) -> None:
    """Partes semanales de las últimas 4 semanas para el panel del profesor."""
    lunes = lunes_actual()
    total = 0
    for atleta in atletas.values():
        peso = Decimal("70.0")
        for i in range(4):
            semana = lunes - timedelta(weeks=3 - i)
            peso = (peso + Decimal(str(round(__import__("random").uniform(-0.4, 0.4), 1)))).quantize(
                Decimal("0.1"), rounding=ROUND_HALF_UP)
            db.add(ParteSemanal(
                atleta_id=atleta.id, semana=semana,
                sueno_calidad=4, fatiga=3, dolor_muscular=4, estres=4, animo=4,
                horas_sueno=Decimal("7.5"),
                comidas_dia=4, alimentacion_calidad=4, hidratacion_litros=Decimal("2.0"),
                come_antes_entrenar=True, suplementos=None,
                peso_kg=peso, sesiones=4, minutos_totales=300, rpe=6,
                molestias=False, molestia_zona=None, molestia_dolor=None,
                comentarios=None,
            ))
            total += 1
    print(f"Partes semanales creados/actualizados: {total}.")


def _crear_marcas(db, atletas: dict) -> None:
    """Unas marcas recientes por atleta (fechas pasadas, nunca futuras)."""
    plan = {
        "demo_atleta1": [("100m", Decimal("12.60"), HOY - timedelta(days=10))],
        "demo_atleta2": [("400m", Decimal("51.40"), HOY - timedelta(days=12))],
        "demo_atleta3": [("largo", Decimal("5.55"), HOY - timedelta(days=14))],
    }
    total = 0
    for username, items in plan.items():
        atleta = atletas[username]
        for prueba, valor, fecha in items:
            if not pruebas.existe(prueba):
                continue
            db.add(Marca(
                atleta_id=atleta.id, prueba=prueba, fecha=fecha,
                valor=valor, viento=None,
                es_competencia=False, competencia=None,
                lugar="Pista municipal", nota="Demo",
            ))
            total += 1
    print(f"Marcas creadas/actualizadas: {total}.")


def _crear_asistencias(db, atletas: dict) -> None:
    """Asistencias de los últimos días de entrenamiento (lun/mié/vié)."""
    total = 0
    for dias_atras in range(1, 11):
        dia = HOY - timedelta(days=dias_atras)
        if dia.weekday() not in (0, 2, 4):  # lunes, miércoles, viernes
            continue
        for atleta in atletas.values():
            db.add(Asistencia(atleta_id=atleta.id, fecha=dia, estado="presente"))
            total += 1
    print(f"Asistencias creadas/actualizadas: {total}.")


def _crear_pagos(db, atletas: dict) -> None:
    """Pagos del mes en curso.

    demo_atleta1 y demo_atleta3 al día; demo_atleta2 debe el mes en curso, para
    mostrar una deuda pendiente en el estado de cuenta.
    """
    pagados = {"demo_atleta1", "demo_atleta3"}
    total = 0
    for username, atleta in atletas.items():
        if username in pagados:
            db.add(Pago(
                atleta_id=atleta.id, periodo=MES_ACTUAL,
                fecha_pago=min(MES_ACTUAL + timedelta(days=5), HOY),
                monto=atleta.cuota_mensual, metodo="transferencia", nota="Demo",
            ))
            total += 1
    print(f"Pagos creados/actualizados: {total}.")


def main() -> None:
    borrar = "--borrar-demo" in sys.argv
    confirmar = "--confirmar-borrar-demo" in sys.argv

    if borrar and not confirmar:
        raise SystemExit(
            "El borrado de datos demo requiere --confirmar-borrar-demo.\n"
            "Uso: python scripts/seed_demo.py --borrar-demo --confirmar-borrar-demo"
        )

    db = SessionLocal()
    try:
        _es_entorno_demo(db)

        if borrar:
            atleta_ids = _ids_atletas_demo(db)
            _borrar_datos_demo(db, atleta_ids, borrar_usuarios=True)
            db.commit()
            print("Datos de demostración borrados (solo registros titularidad demo).")
            return

        # Cuentas de demostración (idempotente: crea o actualiza).
        profesor = _ensure_user(db, DEMO_PROFESOR)
        atletas = {a["username"]: _ensure_user(db, a) for a in DEMO_ATLETAS}
        db.commit()

        # Registros relacionados de demo: se reinician a un estado conocido.
        atleta_ids = [a.id for a in atletas.values()]
        _borrar_datos_demo(db, atleta_ids, borrar_usuarios=False)
        db.commit()

        _crear_partes_diarios(db, atletas)
        _crear_partes_semanales(db, atletas)
        _crear_marcas(db, atletas)
        _crear_asistencias(db, atletas)
        _crear_pagos(db, atletas)
        db.commit()

        print("\nDatos de demostración listos (base atletismo_demo, solo registros demo).")
        print("Cuentas de demostración (sin cambio de contraseña forzado):")
        print(f"  Profesor: {DEMO_PROFESOR['username']} (rol profesor)")
        for a in DEMO_ATLETAS:
            print(f"  Atleta:   {a['username']} (rol atleta)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
