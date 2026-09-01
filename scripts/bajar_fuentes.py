"""Rearma las tipografías locales a partir de Google Fonts.

Las fuentes se sirven desde `app/static/fonts` y no desde Google (ver el
encabezado de `app/static/css/fuentes.css`). Este script es lo que las trae: se
corre una sola vez, y de nuevo solo si hay que cambiar una familia o un peso.
Los archivos que genera van al repo; en el servidor no se ejecuta nada de esto.

    python scripts/bajar_fuentes.py

Necesita salida a internet. Si falla, la app sigue andando con las que ya están
en el repo: no es parte del despliegue.
"""
import re
import sys
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FUENTES = RAIZ / "app" / "static" / "fonts"
HOJA = RAIZ / "app" / "static" / "css" / "fuentes.css"

# Google devuelve el CSS según el navegador que dice ser quien pregunta: con un
# user-agent viejo manda formatos antiguos y pesados en vez de woff2.
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

# El castellano —acentos y ñ incluidos— entra entero en estos dos subsets. Traer
# cirílico o vietnamita sería triplicar el peso para caracteres que el club no usa.
SUBSETS = {"latin", "latin-ext"}

# (familia tal como la pide Google, prefijo de los archivos)
# Hanken Grotesk se pide como rango (400..800) porque tiene versión variable: un
# archivo cubre todos los pesos. Barlow Condensed no la tiene, así que van los
# dos pesos sueltos que usa el CSS.
FAMILIAS = [
    ("Hanken+Grotesk:wght@400..800", "hanken-grotesk"),
    ("Barlow+Condensed:wght@600;700", "barlow-condensed"),
]

ENCABEZADO = """/* Tipografías del club, servidas desde acá y no desde Google.

   Es el mismo criterio por el que los gráficos son SVG generados en el servidor:
   la app se abre sobre todo desde el celular del atleta y del profesor, muchas
   veces en la pista y con mala señal. Pedirle la hoja de estilos a un tercero
   agrega dos handshakes (DNS + TLS contra fonts.googleapis.com y contra
   fonts.gstatic.com) antes de poder dibujar la primera letra, y esa cadena
   bloquea el render. Sirviéndolas desde el mismo origen viajan en la conexión
   que ya está abierta, y de paso ninguna visita de un atleta llega a Google.

   Hanken Grotesk va en su versión variable: un archivo por subset cubre de 400
   a 800 y pesa menos que las cinco estáticas por separado. Barlow Condensed no
   tiene variable, así que van los dos pesos que usa el CSS (600 y 700).

   Solo los subsets latin y latin-ext: el castellano, con acentos y ñ, entra
   entero ahí. El unicode-range es el de Google, así que el navegador baja
   latin-ext únicamente si la página tiene algún carácter que lo necesite.

   ESTE ARCHIVO SE GENERA: no lo edites a mano, corré scripts/bajar_fuentes.py.
   Ambas familias son SIL Open Font License 1.1 (ver LICENSE-fuentes.txt). */

"""


def bajar(url: str) -> bytes:
    return urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30).read()


def main() -> None:
    FUENTES.mkdir(parents=True, exist_ok=True)
    bloques, total = [], 0

    for familia, prefijo in FAMILIAS:
        css = bajar(f"https://fonts.googleapis.com/css2?family={familia}"
                    "&display=swap").decode("utf-8")
        if "@font-face" not in css:
            sys.exit(f"Google no devolvió CSS para «{familia}». "
                     "¿Cambió el nombre de la familia o el rango de pesos?")
        # Cada @font-face viene precedido de un comentario con su subset.
        for subset, cuerpo in re.findall(r"/\* ([a-z-]+) \*/\s*(@font-face \{.*?\})",
                                         css, re.S):
            if subset not in SUBSETS:
                continue
            url = re.search(r"url\((https://[^)]+\.woff2)\)", cuerpo).group(1)
            peso = re.search(r"font-weight: ([^;]+);", cuerpo).group(1).strip()
            nombre = f"{prefijo}-{peso.replace(' ', '-')}-{subset}.woff2"
            datos = bajar(url)
            (FUENTES / nombre).write_bytes(datos)
            total += len(datos)
            print(f"  {nombre:48} {len(datos) / 1024:6.1f} kB")
            bloques.append(cuerpo.replace(f"url({url})", f"url(/static/fonts/{nombre})"))

    if not bloques:
        sys.exit("No se bajó ninguna fuente: revisá SUBSETS y FAMILIAS.")
    HOJA.write_text(ENCABEZADO + "\n\n".join(bloques) + "\n")
    print(f"  {'TOTAL':48} {total / 1024:6.1f} kB")
    print(f"\nListo: {len(bloques)} caras en {FUENTES} y la hoja en {HOJA.name}.")


if __name__ == "__main__":
    main()
