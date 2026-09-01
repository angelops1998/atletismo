"""Validación de los destinos de redirección que llegan por formulario.

Varias pantallas mandan adónde volver después de guardar (`volver`), y el login
recibe adónde iba la persona antes de que se le pidiera la contraseña (`next`).
Si eso se usa tal cual, el login queda convertido en un trampolín: el link se
manda por WhatsApp con la dirección del club a la vista, la persona entra con su
usuario y termina en otro sitio que le pide la contraseña de nuevo.
"""

# Los caracteres de control no llegan a la URL final: el navegador los descarta
# antes de interpretarla. Si el chequeo se hace sobre el texto crudo, "/\x09/otro"
# lo pasa y el navegador termina navegando a "//otro".
_CONTROL = {chr(c) for c in range(0x20)} | {"\x7f"}


def ruta_interna(destino: str | None, por_defecto: str) -> str:
    """`destino` si es una ruta de esta misma app; si no, `por_defecto`.

    No alcanza con pedir que empiece con "/" y no con "//": los navegadores
    normalizan la barra invertida a barra común, así que "/\\otrositio.com" se
    resuelve como "//otrositio.com" y sale de la app. Por eso se rechaza
    cualquier segunda posición que sea "/" o "\\".
    """
    ruta = "".join(c for c in (destino or "") if c not in _CONTROL).strip()
    if not ruta.startswith("/"):
        return por_defecto
    if len(ruta) > 1 and ruta[1] in "/\\":
        return por_defecto
    return ruta
