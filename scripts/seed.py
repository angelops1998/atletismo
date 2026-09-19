"""Carga datos de ejemplo para poder ver el sistema funcionando.

Sirve para probar y para mostrarle la app al profesor antes de que cargue a su
gente: las pantallas de estadísticas y de alertas no se entienden vacías. Los
datos están armados para que aparezca cada situación que el sistema tiene que
detectar (un atleta que no carga el parte, uno que sube la carga de golpe, uno
con una molestia arrastrada, dos que deben cuotas).

    python scripts/seed.py          # agrega los datos de ejemplo
    python scripts/seed.py --borrar # borra TODO y los vuelve a cargar
"""
import sys
import random
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal                      # noqa: E402
from app.models.user import User                           # noqa: E402
from app.models.parte import ParteSemanal                  # noqa: E402
from app.models.marca import Marca                         # noqa: E402
from app.models.pago import Pago                           # noqa: E402
from app.models.asistencia import Asistencia               # noqa: E402
from app.auth import hash_password                         # noqa: E402
from app.services import cobranza                          # noqa: E402
from app.tiempo import hoy, lunes_actual                   # noqa: E402

SEMANAS = 16
PASSWORD_DEMO = "atletismo123"

# (nombre, usuario, categoría, prueba, cuota, perfil)
# El perfil define qué situación representa cada uno, para que el panel muestre
# todas las alertas que el sistema sabe detectar.
ATLETAS = [
    ("Lucía Fernández",   "lfernandez", "Juveniles", "100m",   150, "solida"),
    ("Mateo Rivas",       "mrivas",     "Mayores",   "400m",   150, "sobrecarga"),
    ("Camila Ortiz",      "cortiz",     "Juveniles", "largo",  150, "molestia"),
    ("Tomás Aguirre",     "taguirre",   "Mayores",   "1500m",  150, "solida"),
    ("Valentina Sosa",    "vsosa",      "Menores",   "100m",   150, "irregular"),
    ("Joaquín Medina",    "jmedina",    "Mayores",   "bala",   150, "duerme_poco"),
    ("Martina Cabrera",   "mcabrera",   "Juveniles", "800m",   150, "solida"),
    ("Benjamín Ledesma",  "bledesma",   "Menores",   "60m",    150, "sin_parte"),
    ("Julieta Paz",       "jpaz",       "Mayores",   "jabalina", 150, "solida"),
    ("Santiago Vera",     "svera",      "Juveniles", "200m",   150, "bajon"),
    ("Renata Molina",     "rmolina",    "Menores",   "alto",   150, "irregular"),
    ("Facundo Ríos",      "frios",      "Mayores",   "5000m",  150, "solida"),
]

# Prueba real de cada atleta para las marcas (la del padrón es texto libre)
PRUEBA_DE = {
    "lfernandez": ("100m", 12.60), "mrivas": ("400m", 51.40),
    "cortiz": ("largo", 5.55), "taguirre": ("1500m", 245.0),
    "vsosa": ("100m", 14.10), "jmedina": ("bala", 11.80),
    "mcabrera": ("800m", 138.0), "bledesma": ("60m", 8.40),
    "jpaz": ("jabalina", 38.60), "svera": ("200m", 24.30),
    "rmolina": ("alto", 1.52), "frios": ("5000m", 1010.0),
}


def nombre_prueba(clave: str) -> str:
    """El nombre que se muestra, igual que el que guarda el formulario de alta."""
    from app.services import pruebas
    return pruebas.nombre(clave)


def limpiar(db) -> None:
    for modelo in (ParteSemanal, Marca, Pago, Asistencia):
        db.query(modelo).delete()
    db.query(User).delete()
    db.commit()
    print("Datos anteriores borrados.")


def crear_usuarios(db) -> dict:
    db.add(User(
        username="profe", email="profe@club.com",
        hashed_password=hash_password("profesor123"),
        full_name="Daniel Valenzuela", role="profesor", fecha_alta=hoy(),
    ))
    creados = {}
    for nombre, usuario, categoria, prueba, cuota, perfil in ATLETAS:
        alta = hoy() - timedelta(days=random.randint(90, 700))
        atleta = User(
            username=usuario,
            email=f"{usuario}@ejemplo.com",
            hashed_password=hash_password(PASSWORD_DEMO),
            full_name=nombre,
            role="atleta",
            fecha_nacimiento=hoy() - timedelta(days=random.randint(3300, 9500)),
            telefono=f"+591 {random.choice([6, 7])}{random.randint(1000000, 9999999)}",
            categoria=categoria,
            prueba_principal=nombre_prueba(prueba),
            fecha_alta=alta,
            contacto_emergencia=f"Familiar — +591 {random.choice([6, 7])}{random.randint(1000000, 9999999)}",
            cuota_mensual=Decimal(cuota),
            # Se cobra desde hace unos meses: así hay historial de pagos que ver.
            cobro_desde=cobranza.primer_dia(max(alta, hoy() - timedelta(days=150))),
        )
        db.add(atleta)
        creados[usuario] = (atleta, perfil)
    db.commit()
    print(f"Creados: 1 profesor y {len(creados)} atletas.")
    return creados


def perfil_semana(perfil: str, i: int, total: int) -> dict | None:
    """Los valores del parte de una semana según el perfil del atleta.

    `i` va de 0 (la semana más vieja) a total-1 (la actual).
    Devuelve None cuando ese atleta no cargó esa semana.
    """
    es_actual = i == total - 1
    base = {
        "sueno": random.randint(3, 5),
        "dolor": random.randint(3, 5), "estres": random.randint(3, 5),
        "animo": random.randint(3, 5),
        "horas": round(random.uniform(7.0, 8.5), 1),
        "sesiones": random.randint(4, 5),
        "minutos": random.randint(280, 360),
        "rpe": random.randint(5, 7),
        "molestia": None,
    }

    if perfil == "sin_parte" and es_actual:
        return None
    if perfil == "irregular" and random.random() < 0.45:
        return None

    if perfil == "duerme_poco":
        base["horas"] = round(random.uniform(5.2, 6.6), 1)
        base["sueno"] = random.randint(2, 3)

    if perfil == "sobrecarga":
        # Sube la carga de a poco y pega un salto en las últimas dos semanas:
        # es el caso que tiene que disparar la alerta de ratio de carga.
        if i >= total - 2:
            base["minutos"] = random.randint(520, 600)
            base["rpe"] = random.randint(8, 9)
            base["dolor"] = 2
        else:
            base["minutos"] = random.randint(260, 320)
            base["rpe"] = random.randint(5, 6)

    if perfil == "molestia" and i >= total - 3:
        base["molestia"] = (random.choice(["Isquiotibial derecho", "Tobillo izquierdo",
                                           "Aductor derecho"]), random.randint(5, 7))
        base["dolor"] = 2

    if perfil == "bajon" and i >= total - 2:
        base.update({"sueno": 2, "dolor": 1, "estres": 2, "animo": 2,
                     "horas": round(random.uniform(5.0, 6.0), 1)})

    return base


def crear_partes(db, creados: dict) -> None:
    lunes = lunes_actual()
    total = 0
    for usuario, (atleta, perfil) in creados.items():
        peso = round(random.uniform(52, 88), 1)
        for i in range(SEMANAS):
            semana = lunes - timedelta(weeks=SEMANAS - 1 - i)
            datos = perfil_semana(perfil, i, SEMANAS)
            if datos is None:
                continue
            peso = round(peso + random.uniform(-0.4, 0.4), 1)
            molestia = datos["molestia"]
            db.add(ParteSemanal(
                atleta_id=atleta.id, semana=semana,
                sueno_calidad=datos["sueno"],
                dolor_muscular=datos["dolor"], estres=datos["estres"],
                animo=datos["animo"],
                horas_sueno=Decimal(str(datos["horas"])),
                comidas_dia=random.randint(3, 5),
                alimentacion_calidad=random.randint(3, 5),
                hidratacion_litros=Decimal(str(round(random.uniform(1.5, 3.0), 1))),
                come_antes_entrenar=random.random() > 0.2,
                peso_kg=Decimal(str(peso)),
                sesiones=datos["sesiones"], minutos_totales=datos["minutos"],
                rpe=datos["rpe"],
                molestias=molestia is not None,
                molestia_zona=molestia[0] if molestia else None,
                molestia_dolor=molestia[1] if molestia else None,
                comentarios=("Semana de parciales, dormí mal." if datos["sueno"] <= 2
                             else None),
            ))
            total += 1
    db.commit()
    print(f"Cargados {total} partes semanales.")


def crear_marcas(db, creados: dict) -> None:
    """Marcas cada tres semanas, mejor cuando el bienestar de esa semana fue mejor.

    La relación se mete a propósito: es lo que la pantalla de estadísticas tiene
    que ser capaz de encontrar. Con datos al azar el gráfico de cruce no muestra
    nada y no se puede verificar que funcione.
    """
    lunes = lunes_actual()
    total = 0
    for usuario, (atleta, _perfil) in creados.items():
        prueba, referencia = PRUEBA_DE[usuario]
        menor_es_mejor = prueba not in ("largo", "alto", "bala", "jabalina", "disco")
        for i in range(0, SEMANAS, 3):
            semana = lunes - timedelta(weeks=SEMANAS - 1 - i)
            parte = (db.query(ParteSemanal)
                     .filter(ParteSemanal.atleta_id == atleta.id,
                             ParteSemanal.semana == semana).first())
            if parte is None:
                continue
            bienestar = sum([parte.sueno_calidad, parte.dolor_muscular,
                             parte.estres, parte.animo])
            # De 4 a 20 -> de -1.6% a +1.6% sobre la marca de referencia, más la
            # mejora natural por entrenar, más un poco de ruido.
            efecto = (bienestar - 12) / 8 * 1.6
            progreso = i / SEMANAS * 2.0
            ruido = random.uniform(-0.5, 0.5)
            pct = efecto + progreso + ruido
            valor = referencia * (1 - pct / 100) if menor_es_mejor else referencia * (1 + pct / 100)
            db.add(Marca(
                atleta_id=atleta.id, prueba=prueba,
                # Nunca en el futuro: la semana en curso todavía no terminó.
                fecha=min(semana + timedelta(days=5), hoy()),
                valor=Decimal(str(round(valor, 2))),
                viento=Decimal(str(round(random.uniform(-1.5, 1.9), 1)))
                       if prueba in ("100m", "200m", "60m", "largo") else None,
                es_competencia=i % 6 == 0,
                competencia="Torneo Federativo" if i % 6 == 0 else None,
                lugar="Pista municipal",
            ))
            total += 1
    db.commit()
    print(f"Cargadas {total} marcas.")


def crear_asistencias(db, creados: dict) -> None:
    total = 0
    for dias_atras in range(1, 43):
        dia = hoy() - timedelta(days=dias_atras)
        if dia.weekday() not in (0, 2, 4):      # lunes, miércoles y viernes
            continue
        for usuario, (atleta, perfil) in creados.items():
            if perfil == "irregular" and random.random() < 0.4:
                estado = random.choice(["ausente", "justificado"])
            elif random.random() < 0.12:
                estado = random.choice(["ausente", "justificado"])
            else:
                estado = "presente"
            db.add(Asistencia(atleta_id=atleta.id, fecha=dia, estado=estado))
            total += 1
    db.commit()
    print(f"Cargadas {total} asistencias.")


def crear_pagos(db, creados: dict) -> None:
    """Paga casi todo el mundo, menos tres: así se ve la pantalla de cobranza
    con deudores de uno, dos y tres meses."""
    morosos = {"vsosa": 1, "svera": 2, "rmolina": 3}
    total = 0
    for usuario, (atleta, _perfil) in creados.items():
        meses = cobranza.meses_entre(atleta.cobro_desde, hoy())
        saltear = morosos.get(usuario, 0)
        a_pagar = meses[:-saltear] if saltear else meses
        for mes in a_pagar:
            db.add(Pago(
                atleta_id=atleta.id, periodo=mes,
                # Sin el tope, la cuota del mes en curso quedaba pagada en el futuro.
                fecha_pago=min(mes + timedelta(days=random.randint(1, 8)), hoy()),
                monto=atleta.cuota_mensual,
                metodo=random.choice(["efectivo", "transferencia"]),
            ))
            total += 1
    db.commit()
    print(f"Cargados {total} pagos.")


def main() -> None:
    random.seed(7)      # los mismos datos en cada corrida, para poder comparar
    db = SessionLocal()
    try:
        if "--borrar" in sys.argv:
            limpiar(db)
        elif db.query(User).count():
            sys.exit("Ya hay datos cargados. Usá --borrar para empezar de cero.")

        creados = crear_usuarios(db)
        crear_partes(db, creados)
        crear_marcas(db, creados)
        crear_asistencias(db, creados)
        crear_pagos(db, creados)

        print("\nListo. Entrá con:")
        print("  profesor -> usuario «profe», contraseña «profesor123»")
        print(f"  atleta   -> usuario «lfernandez», contraseña «{PASSWORD_DEMO}»")
    finally:
        db.close()


if __name__ == "__main__":
    main()
