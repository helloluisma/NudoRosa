"""
Tasa de cambio USD → Bs. (Banco Central de Venezuela).

La consulta al BCV corre siempre acá, del lado del servidor — nunca
desde el navegador (ver las rutas POST /configuracion/tasa-bcv/* en
main.py). Así se evita CORS contra bcv.org.ve y el mecanismo de
extracción (qué selector, qué forma tiene el HTML) no queda expuesto
ni depende del cliente.

bcv.org.ve no tiene una API: se lee el valor publicado en la portada
con BeautifulSoup, así que un rediseño del sitio puede romper el
parseo — ver `_extraer_tasa_html`, que documenta el selector exacto.
"""

import logging
import os
import re
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import TasaCambio
from services import ErrorNegocio

logger = logging.getLogger("nudorosa")

URL_BCV = "https://www.bcv.org.ve/"
TIMEOUT_SEGUNDOS = 10.0
MONEDA_USD = "USD"

# bcv.org.ve sirve su certificado sin la cadena intermedia completa —
# la verificación TLS falla ahí con cualquier cliente estricto
# (confirmado en vivo al construir esto), no es un problema de esta
# app ni de la red local. Es un compromiso deliberado y acotado a
# este único host público: no viaja ninguna credencial ni dato
# sensible, solo se lee la tasa publicada. Si el BCV corrige su
# certificado, esto puede volver a True sin cambiar nada más.
_VERIFY_TLS_BCV = False


class ErrorConsultaBCV(Exception):
    """Fallo de red, timeout o HTML con una forma inesperada al
    consultar bcv.org.ve. `actualizar_tasa_automatica` la atrapa y la
    traduce a un mensaje claro — nunca se deja propagar tal cual, y
    nunca modifica la tasa activa cuando ocurre."""


def obtener_tasa_activa(db: Session, moneda: str = MONEDA_USD) -> TasaCambio | None:
    """Única tasa vigente para los cálculos actuales (ver models.TasaCambio)."""

    return db.scalar(
        select(TasaCambio)
        .where(TasaCambio.moneda == moneda, TasaCambio.activa.is_(True))
        .order_by(TasaCambio.id.desc())
    )


# --------------------------------------------------------------------
# Conversión y formato — funciones puras, reutilizadas desde main.py
# (Jinja globals) y desde cualquier servicio que necesite mostrar un
# monto en bolívares.
# --------------------------------------------------------------------

def convertir_usd_a_bolivares(
    monto_usd: int | float | Decimal, tasa_bolivares: Decimal | int | float | None
) -> Decimal | None:
    """None si no hay tasa (nunca se inventa una) — quien llama decide
    qué mostrar en ese caso (ver formatear_bolivares)."""

    if tasa_bolivares is None:
        return None

    return (Decimal(str(monto_usd)) * Decimal(str(tasa_bolivares))).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def _formatear_numero(valor: Decimal | int | float, decimales: int = 2) -> str:
    """Formato numérico venezolano: punto de miles, coma decimal
    (ej. 1.210,74) — el que usa el BCV y el que pidió Ivanna."""

    cuantizador = Decimal(1).scaleb(-decimales)
    valor_decimal = Decimal(str(valor)).quantize(cuantizador, rounding=ROUND_HALF_UP)

    signo = "-" if valor_decimal < 0 else ""
    entero, _, fraccion = f"{abs(valor_decimal):.{decimales}f}".partition(".")

    grupos = []
    while len(entero) > 3:
        grupos.insert(0, entero[-3:])
        entero = entero[:-3]
    grupos.insert(0, entero)

    numero = ".".join(grupos)
    return f"{signo}{numero},{fraccion}" if decimales else f"{signo}{numero}"


def formatear_usd(monto: int | float | Decimal) -> str:
    return f"${_formatear_numero(monto)}"


def formatear_bolivares(monto: int | float | Decimal | None) -> str:
    if monto is None:
        return "—"
    return f"Bs. {_formatear_numero(monto)}"


# --------------------------------------------------------------------
# Consulta al BCV
# --------------------------------------------------------------------

def _descargar_html_bcv() -> str:
    try:
        respuesta = httpx.get(
            URL_BCV,
            timeout=TIMEOUT_SEGUNDOS,
            verify=_VERIFY_TLS_BCV,
            headers={"User-Agent": "Mozilla/5.0 (compatible; NudoRosa/1.0)"},
        )
        respuesta.raise_for_status()
    except httpx.TimeoutException as error:
        raise ErrorConsultaBCV("El BCV no respondió a tiempo.") from error
    except httpx.HTTPError as error:
        raise ErrorConsultaBCV("No se pudo conectar con el BCV.") from error

    return respuesta.text


def _extraer_tasa_html(html: str) -> tuple[Decimal, date]:
    """
    Selector real de bcv.org.ve (verificado contra el sitio en vivo al
    construir esto): el dólar vive en `<div id="dolar">`, dentro de un
    `<strong class="strong-tb">` con el número en formato venezolano
    ("737,23210000" — coma decimal, sin separador de miles). La fecha
    de vigencia es la que acompaña al único texto "Fecha Valor:" de la
    página, en el `content` (ISO 8601) del `<span
    class="date-display-single">` que le sigue.

    Si el BCV cambia esta estructura (el id, la clase, el texto de la
    etiqueta), esto deja de encontrar el nodo esperado y levanta
    ErrorConsultaBCV — nunca intenta adivinar un valor a partir de un
    HTML que no reconoce.
    """

    soup = BeautifulSoup(html, "html.parser")

    div_dolar = soup.find("div", id="dolar")
    if div_dolar is None:
        raise ErrorConsultaBCV("El BCV cambió el formato de su página (no se encontró el bloque del dólar).")

    strong = div_dolar.find("strong", class_="strong-tb")
    if strong is None:
        raise ErrorConsultaBCV("El BCV cambió el formato de su página (no se encontró el valor del dólar).")

    texto_tasa = strong.get_text(strip=True)

    try:
        tasa = Decimal(texto_tasa.replace(".", "").replace(",", "."))
    except InvalidOperation as error:
        raise ErrorConsultaBCV(f"El BCV devolvió un valor no numérico: {texto_tasa!r}.") from error

    if tasa <= 0:
        raise ErrorConsultaBCV(f"El BCV devolvió una tasa inválida: {tasa}.")

    nodo_etiqueta = soup.find(string=re.compile("Fecha Valor"))
    span_fecha = nodo_etiqueta.find_next("span", class_="date-display-single") if nodo_etiqueta else None

    if span_fecha is None or not span_fecha.get("content"):
        # La tasa en sí ya es válida — no vale la pena descartarla
        # solo porque no se pudo leer la fecha de vigencia.
        fecha_vigencia = date.today()
    else:
        try:
            fecha_vigencia = datetime.fromisoformat(span_fecha["content"]).date()
        except ValueError:
            fecha_vigencia = date.today()

    return tasa, fecha_vigencia


def _guardar_nueva_tasa(
    db: Session,
    tasa_bolivares: Decimal,
    fecha_vigencia: date,
    fuente: str,
    actualizada_automaticamente: bool,
    moneda: str = MONEDA_USD,
) -> TasaCambio:
    """Nunca sobreescribe: desactiva la fila anterior y agrega una
    nueva, en la misma transacción (ver models.TasaCambio)."""

    anterior = obtener_tasa_activa(db, moneda)
    if anterior is not None:
        anterior.activa = False

    nueva = TasaCambio(
        moneda=moneda,
        tasa_bolivares=tasa_bolivares,
        fuente=fuente,
        fecha_vigencia=fecha_vigencia,
        fecha_actualizacion=datetime.utcnow(),
        actualizada_automaticamente=actualizada_automaticamente,
        activa=True,
    )
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva


def _resultado(tasa: TasaCambio | None, ok: bool, mensaje: str) -> dict:
    return {
        "ok": ok,
        "tasa": float(tasa.tasa_bolivares) if tasa else None,
        "tasa_formateada": formatear_bolivares(tasa.tasa_bolivares) if tasa else None,
        "fecha_vigencia": tasa.fecha_vigencia.isoformat() if tasa else None,
        "fecha_actualizacion": tasa.fecha_actualizacion.isoformat() if tasa else None,
        "fuente": tasa.fuente if tasa else None,
        "actualizada_automaticamente": tasa.actualizada_automaticamente if tasa else None,
        "mensaje": mensaje,
    }


def actualizar_tasa_automatica(db: Session) -> dict:
    """
    Consulta el BCV y guarda la tasa nueva si todo sale bien. Si falla
    cualquier paso (red, timeout, HTML con otra forma, valor
    inválido) NO toca la tasa activa existente — se limita a informar
    el error y devolver la tasa anterior tal cual estaba, para que la
    pantalla nunca se quede sin un número que mostrar.
    """

    try:
        tasa_bolivares, fecha_vigencia = _extraer_tasa_html(_descargar_html_bcv())
    except ErrorConsultaBCV as error:
        logger.warning("Actualización automática de tasa BCV falló: %s", error)
        return _resultado(
            obtener_tasa_activa(db),
            ok=False,
            mensaje="No se pudo consultar el BCV. Se mantiene la tasa anterior.",
        )

    nueva = _guardar_nueva_tasa(
        db,
        tasa_bolivares=tasa_bolivares,
        fecha_vigencia=fecha_vigencia,
        fuente="BCV",
        actualizada_automaticamente=True,
    )
    return _resultado(nueva, ok=True, mensaje="Tasa BCV actualizada correctamente.")


def guardar_tasa_manual(db: Session, tasa_bolivares: Decimal) -> dict:
    """Respaldo para cuando el BCV no responde: la administradora
    carga el valor a mano. Queda registrada como no automática, nunca
    se confunde con una lectura real del BCV."""

    if tasa_bolivares <= 0:
        raise ErrorNegocio("La tasa debe ser mayor que cero.")

    nueva = _guardar_nueva_tasa(
        db,
        tasa_bolivares=tasa_bolivares,
        fecha_vigencia=date.today(),
        fuente="MANUAL",
        actualizada_automaticamente=False,
    )
    return _resultado(nueva, ok=True, mensaje="Tasa actualizada manualmente.")


def asegurar_tasa_inicial(db: Session, moneda: str = MONEDA_USD) -> None:
    """
    Se llama una sola vez al arrancar la app (ver el lifespan en
    main.py) y solo actúa si todavía no hay ninguna tasa guardada —
    nunca pisa una que ya exista.

    Primero intenta traer la tasa real del BCV (para no tener que
    escribir un número "actual" fijo en el código, que envejece mal).
    Si el arranque no tiene red o el BCV no responde, cae a la
    variable de entorno TASA_BCV_INICIAL (opcional) como último
    recurso. Si tampoco existe, la app queda sin tasa hasta que se
    actualice desde Configuración — nunca se inventa un valor ni se
    guarda un cero.
    """

    if obtener_tasa_activa(db, moneda) is not None:
        return

    resultado = actualizar_tasa_automatica(db)
    if resultado["ok"]:
        logger.info("Tasa BCV inicial obtenida del sitio oficial: %s", resultado["tasa"])
        return

    tasa_inicial_env = os.environ.get("TASA_BCV_INICIAL")
    if not tasa_inicial_env:
        logger.warning(
            "No se pudo obtener la tasa BCV inicial y no hay TASA_BCV_INICIAL configurada; "
            "la app queda sin tasa hasta que se actualice desde Configuración."
        )
        return

    try:
        tasa_bolivares = Decimal(tasa_inicial_env)
    except InvalidOperation:
        logger.warning("TASA_BCV_INICIAL=%r no es un número válido; se ignora.", tasa_inicial_env)
        return

    if tasa_bolivares <= 0:
        logger.warning("TASA_BCV_INICIAL=%r debe ser mayor que cero; se ignora.", tasa_inicial_env)
        return

    _guardar_nueva_tasa(
        db,
        tasa_bolivares=tasa_bolivares,
        fecha_vigencia=date.today(),
        fuente="MANUAL",
        actualizada_automaticamente=False,
    )
    logger.info("Tasa BCV inicial cargada desde TASA_BCV_INICIAL: %s", tasa_bolivares)
