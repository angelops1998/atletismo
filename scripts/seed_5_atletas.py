"""Agrega 5 atletas de prueba a una base que YA tiene datos.

Existe porque `seed.py` es todo o nada: si encuentra usuarios cargados corta con
"Ya hay datos cargados. Usá --borrar para empezar de cero", y --borrar vacía el
club entero. Cuando lo que hace falta es sumar unos atletas a una base que ya
está poblada —para probar una pantalla con más gente, o para mostrarle la app al
profesor sobre sus propios datos— hay que usar este.

Carga menos que seed.py a propósito: cinco atletas y ocho semanas de partes, sin
marcas, asistencias ni pagos. Para ver el sistema completo con todas las
situaciones que detecta, el que sirve es seed.py sobre una base vacía.

    python scripts/seed_5_atletas.py

Los usuarios son los mismos cinco primeros de seed.py, así que si ya corriste
seed.py este va a chocar con los nombres. **No usar en producción.**
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
from app.auth import hash_password                         # noqa: E402
from app.services import cobranza, pruebas                 # noqa: E402
from app.tiempo import hoy, lunes_actual                   # noqa: E402

SEMANAS = 8
PASSWORD_DEMO = "atletismo123"

# (nombre, usuario, categoría, prueba, cuota)
ATLETAS = [
    ("Lucía Fernández", "lfernandez", "Juveniles", "100m", 150),
    ("Mateo Rivas",     "mrivas",     "Mayores",   "400m", 150),
    ("Camila Ortiz",    "cortiz",     "Juveniles", "largo", 150),
    ("Tomás Aguirre",   "taguirre",   "Mayores",   "1500m", 150),
    ("Valentina Sosa",  "vsosa",      "Menores",   "100m",  150),
]


def crear_usuarios(db) -> dict:
    creados = {}
    for nombre, usuario, categoria, prueba, cuota in ATLETAS:
        if db.query(User).filter(User.username == usuario).first():
            print(f"Ya existe {usuario}, se lo salta.")
            continue
        alta = hoy() - timedelta(days=random.randint(30, 200))
        atleta = User(
            username=usuario,
            email=f"{usuario}@ejemplo.com",
            hashed_password=hash_password(PASSWORD_DEMO),
            full_name=nombre,
            role="atleta",
            fecha_nacimiento=hoy() - timedelta(days=random.randint(3300, 9500)),
            telefono=f"+591 {random.choice([6, 7])}{random.randint(1000000, 9999999)}",
            categoria=categoria,
            prueba_principal=pruebas.nombre(prueba),
            fecha_alta=alta,
            contacto_emergencia=f"Familiar — +591 {random.choice([6, 7])}{random.randint(1000000, 9999999)}",
            cuota_mensual=Decimal(cuota),
            cobro_desde=cobranza.primer_dia(max(alta, hoy() - timedelta(days=60))),
        )
        db.add(atleta)
        creados[usuario] = atleta
    db.commit()
    print(f"Creados {len(creados)} atletas nuevos.")
    return creados


def crear_partes(db, creados: dict) -> None:
    lunes = lunes_actual()
    total = 0
    for usuario, atleta in creados.items():
        peso = round(random.uniform(52, 88), 1)
        for i in range(SEMANAS):
            semana = lunes - timedelta(weeks=SEMANAS - 1 - i)
            peso = round(peso + random.uniform(-0.4, 0.4), 1)
            db.add(ParteSemanal(
                atleta_id=atleta.id, semana=semana,
                sueno_calidad=random.randint(3, 5),
                dolor_muscular=random.randint(3, 5), estres=random.randint(3, 5),
                animo=random.randint(3, 5),
                horas_sueno=Decimal(str(round(random.uniform(7.0, 8.5), 1))),
                comidas_dia=random.randint(3, 5),
                alimentacion_calidad=random.randint(3, 5),
                hidratacion_litros=Decimal(str(round(random.uniform(1.5, 3.0), 1))),
                come_antes_entrenar=random.random() > 0.2,
                peso_kg=Decimal(str(peso)),
                sesiones=random.randint(4, 5),
                minutos_totales=random.randint(280, 360),
                rpe=random.randint(5, 7),
                molestias=False,
            ))
            total += 1
    db.commit()
    print(f"Cargados {total} partes semanales.")


def main() -> None:
    random.seed(7)
    db = SessionLocal()
    try:
        creados = crear_usuarios(db)
        if creados:
            crear_partes(db, creados)
        print("\nListo. Atletas de prueba (contraseña «atletismo123»):")
        for _n, usuario, *_ in ATLETAS:
            print(f"  - {usuario}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
