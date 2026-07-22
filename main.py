import logging
import os
import random
import re
import secrets
from contextlib import asynccontextmanager
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import quote

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from database import SessionLocal, get_db
from models import EstadoEntrega, EstadoPago
from services import ErrorNegocio
from services import clientas as clientas_service
from services import colores as colores_service
from services import inventario as inventario_service
from services import materiales as materiales_service
from services import pedidos as pedidos_service
from services import productos as productos_service
from services import resumen as resumen_service
from services import seguridad as seguridad_service
from services import tasa_cambio as tasa_cambio_service


BASE_DIR = Path(__file__).resolve().parent

MESES_ABREV = [
    "ene", "feb", "mar", "abr", "may", "jun",
    "jul", "ago", "sep", "oct", "nov", "dic",
]

MESES_COMPLETOS = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def _parsear_fecha(valor: str | None) -> date | None:
    if not valor:
        return None

    try:
        return date.fromisoformat(valor)
    except ValueError:
        return None


def _fecha_corta(dia: date) -> str:
    return f"{dia.day} {MESES_ABREV[dia.month - 1]}"


def _fecha_larga(dia: date) -> str:
    return f"{dia.day:02d} {MESES_COMPLETOS[dia.month - 1]} {dia.year}"


def _insignias_cliente(cliente: dict) -> list[dict]:
    insignias = []

    if cliente["etiqueta"] == "Nueva":
        insignias.append({"icono": "🌸", "texto": "Nueva clienta", "tono": "rosa"})

    if cliente["etiqueta"] == "Frecuente":
        insignias.append({"icono": "💖", "texto": "Cliente frecuente", "tono": "fuerte"})

    if cliente["etiqueta"] == "VIP":
        insignias.append({"icono": "⭐", "texto": "VIP", "tono": "dorado"})

    if cliente["pedidos"] >= 15:
        insignias.append({"icono": "👑", "texto": "Top compradora", "tono": "vino"})

    if cliente["pedidos"] > 20:
        insignias.append({"icono": "🏆", "texto": "Más de 20 pedidos", "tono": "vino"})

    nacimiento = _parsear_fecha(cliente.get("fecha_nacimiento"))
    if nacimiento and nacimiento.month == date.today().month:
        insignias.append({"icono": "🎂", "texto": "Cumpleaños este mes", "tono": "dorado"})

    return insignias


def _listar_avatares() -> list[str]:
    carpeta = BASE_DIR / "static" / "images" / "avatar"
    archivos = sorted(
        carpeta.glob("*.png"),
        key=lambda ruta: int(ruta.stem) if ruta.stem.isdigit() else ruta.stem,
    )
    return [f"/static/images/avatar/{archivo.name}" for archivo in archivos]


EXTENSIONES_IMAGEN_VALIDAS = {".png", ".jpg", ".jpeg", ".webp"}


def _estado_producto(stock: int, limite_poco_stock: int) -> dict:
    return inventario_service.estado_producto(stock, limite_poco_stock)


def _parsear_entero_no_negativo(valor: str) -> int | None:
    try:
        numero = int(float(valor))
    except (TypeError, ValueError):
        return None

    return numero if numero >= 0 else None


def _estado_cobro(dias_restantes: int | None) -> dict:
    if dias_restantes is None:
        return {"atrasado": False, "texto": "", "etiqueta": "Pendiente", "pill_class": "pill--pending"}

    if dias_restantes > 0:
        texto = f"Vence en {dias_restantes} día{'s' if dias_restantes != 1 else ''}"
        return {"atrasado": False, "texto": texto, "etiqueta": "Vigente", "pill_class": "pill--pending"}

    if dias_restantes == 0:
        return {"atrasado": False, "texto": "Vence hoy", "etiqueta": "Vigente", "pill_class": "pill--pending"}

    atraso = -dias_restantes
    texto = f"Vencido hace {atraso} día{'s' if atraso != 1 else ''}"
    return {"atrasado": True, "texto": texto, "etiqueta": "Vencido", "pill_class": "pill--due"}


# Diccionarios de presentación (pill/etiqueta) en los tokens en
# minúscula que ya esperan las plantillas y app.js. La VALIDACIÓN de
# transiciones vive únicamente en services/pedidos.py (sobre
# models.EstadoEntrega); esto es solo para mostrar texto/color.
ESTADOS_ENTREGA = {
    "pendiente": {"etiqueta": "Pendiente de entrega", "pill_class": "pill--pending", "prioridad": 1},
    "preparacion": {"etiqueta": "En preparación", "pill_class": "pill--morado", "prioridad": 2},
    "listo": {"etiqueta": "Listo para entregar", "pill_class": "pill--azul", "prioridad": 3},
    "entregado": {"etiqueta": "Entregado", "pill_class": "pill--verde", "prioridad": 4},
    "cancelado": {"etiqueta": "Cancelado", "pill_class": "pill--due", "prioridad": 5},
}

SIGUIENTE_ESTADO_ENTREGA = {
    "pendiente": "preparacion",
    "preparacion": "listo",
    "listo": "entregado",
}

ESTADOS_PAGO = {
    "pendiente": {"etiqueta": "Pendiente de pago", "pill_class": "pill--pending"},
    "pagado": {"etiqueta": "Pagado", "pill_class": "pill--verde"},
    "cancelado": {"etiqueta": "Cancelado", "pill_class": "pill--due"},
}

# Traducción entre el Enum de la base de datos (mayúsculas, ver
# models.py) y los tokens en minúscula del contrato JSON/plantillas
# existente — así ni el HTML ni app.js necesitan cambiar.
MAPA_ENTREGA_A_LEGACY = {
    EstadoEntrega.PENDIENTE: "pendiente",
    EstadoEntrega.EN_PREPARACION: "preparacion",
    EstadoEntrega.LISTO_PARA_ENTREGAR: "listo",
    EstadoEntrega.ENTREGADO: "entregado",
    EstadoEntrega.CANCELADO: "cancelado",
}
MAPA_ENTREGA_DESDE_LEGACY = {v: k for k, v in MAPA_ENTREGA_A_LEGACY.items()}

MAPA_PAGO_A_LEGACY = {
    EstadoPago.PENDIENTE: "pendiente",
    EstadoPago.PAGADO: "pagado",
    EstadoPago.CANCELADO: "cancelado",
}


def _estado_entrega(clave: str) -> dict:
    return ESTADOS_ENTREGA.get(clave, ESTADOS_ENTREGA["pendiente"])


def _estado_pago_info(clave: str) -> dict:
    return ESTADOS_PAGO.get(clave, ESTADOS_PAGO["pendiente"])


def _estado_derivado(venta: dict) -> str:
    if venta["cancelada"]:
        return "Transacción cancelada"

    entregado = venta["estado_entrega"] == "entregado"
    pagado = venta["estado_pago"] == "pagado"

    if entregado and pagado:
        return "Venta completada"

    if entregado and not pagado:
        return "Entregado, falta pagar"

    if not entregado and pagado:
        return "Pagado, falta entregar"

    return "Pedido y cobro pendientes"


def _es_venta_completa(venta: dict) -> bool:
    return (
        not venta["cancelada"]
        and venta["estado_entrega"] == "entregado"
        and venta["estado_pago"] == "pagado"
    )


def _normalizar_imagen_producto(valor: str | None) -> str:
    """
    Corrige datos viejos guardados como solo el nombre de archivo
    (ej. "dobleconcola.png", de antes de que existiera este selector)
    a la ruta pública real sin tocar la base de datos. Si ya es una
    ruta (`/static/...`) o una URL completa, se deja tal cual.
    """
    if not valor:
        return ""

    if valor.startswith("/") or valor.startswith("http://") or valor.startswith("https://"):
        return valor

    return f"/static/images/producto/{valor}"


def _listar_imagenes_producto_predeterminadas() -> list[str]:
    """
    Imágenes reutilizables para "Elegir imagen" en Nuevo/Editar
    producto. Se leen del disco, nunca a mano (mismo patrón que
    _listar_avatares) — cualquier PNG/JPG/WEBP nuevo que se copie a
    la carpeta aparece solo. Se excluyen los archivos que genera
    _guardar_imagen_producto() (`producto_<id>.<ext>`): esas son fotos
    subidas para un producto puntual, no diseños reutilizables.
    """
    carpeta = BASE_DIR / "static" / "images" / "producto"
    archivos = sorted(
        (
            archivo
            for archivo in carpeta.iterdir()
            if archivo.suffix.lower() in EXTENSIONES_IMAGEN_VALIDAS
            and not re.match(r"^producto_\d+\.", archivo.name)
        ),
        key=lambda archivo: archivo.name,
    )
    return [f"/static/images/producto/{archivo.name}" for archivo in archivos]


def _serializar_producto(producto, tasa_bolivares_actual: Decimal | None = None) -> dict:
    return {
        "id": producto.id,
        "nombre": producto.nombre,
        "imagen": _normalizar_imagen_producto(producto.imagen),
        "stock": producto.stock_actual,
        "costo_produccion": float(producto.costo_produccion),
        "costo_produccion_formateado": tasa_cambio_service.formatear_usd(producto.costo_produccion),
        "costo_produccion_bs": (
            tasa_cambio_service.formatear_bolivares(
                tasa_cambio_service.convertir_usd_a_bolivares(producto.costo_produccion, tasa_bolivares_actual)
            )
            if tasa_bolivares_actual is not None
            else None
        ),
        "precio_publico": producto.precio_publico,
        "ganancia_unitaria_formateada": tasa_cambio_service.formatear_usd(
            producto.precio_publico - producto.costo_produccion
        ),
        "ganancia_unitaria_bs": (
            tasa_cambio_service.formatear_bolivares(
                tasa_cambio_service.convertir_usd_a_bolivares(
                    producto.precio_publico - producto.costo_produccion, tasa_bolivares_actual
                )
            )
            if tasa_bolivares_actual is not None
            else None
        ),
        "usa_calculadora_materiales": producto.minutos_elaboracion is not None,
        "lazos_por_metro_tela": producto.lazos_por_metro_tela,
        "lazos_por_barra_silicon": producto.lazos_por_barra_silicon,
        "cantidad_ganchos": producto.cantidad_ganchos,
        "usa_hilo": producto.usa_hilo,
        "minutos_elaboracion": producto.minutos_elaboracion,
    }


def _serializar_tasa_bcv(tasa) -> dict | None:
    if tasa is None:
        return None

    return {
        "tasa": float(tasa.tasa_bolivares),
        "tasa_formateada": tasa_cambio_service.formatear_bolivares(tasa.tasa_bolivares),
        "fuente": tasa.fuente,
        "fecha_vigencia": tasa.fecha_vigencia.isoformat(),
        "fecha_vigencia_texto": _fecha_larga(tasa.fecha_vigencia),
        "fecha_actualizacion": tasa.fecha_actualizacion.isoformat(),
        "fecha_actualizacion_texto": _fecha_larga(tasa.fecha_actualizacion.date()),
        "actualizada_automaticamente": tasa.actualizada_automaticamente,
    }


def _tasa_bolivares_actual(db: Session) -> Decimal | None:
    tasa_activa = tasa_cambio_service.obtener_tasa_activa(db)
    return tasa_activa.tasa_bolivares if tasa_activa else None


def _venta_enriquecida(pedido, tasa_bolivares_actual: Decimal | None = None) -> dict | None:
    if pedido is None or not pedido.items:
        return None

    item = pedido.items[0]
    cliente = pedido.clienta
    producto = item.producto

    if cliente is None or producto is None:
        return None

    hoy = date.today()
    estado_entrega_legacy = MAPA_ENTREGA_A_LEGACY[pedido.estado_entrega]
    estado_pago_legacy = MAPA_PAGO_A_LEGACY[pedido.estado_pago]

    siguiente_enum = pedidos_service.SIGUIENTE_ESTADO_ENTREGA.get(pedido.estado_entrega)
    siguiente = MAPA_ENTREGA_A_LEGACY.get(siguiente_enum) if siguiente_enum else None

    dias_restantes = (pedido.fecha_vencimiento_pago - hoy).days if pedido.fecha_vencimiento_pago else None
    estado_cobro = _estado_cobro(dias_restantes)

    if pedido.estado_pago == EstadoPago.PAGADO:
        # Congelados al pagar (ver services/pedidos.py::marcar_pago) —
        # una tasa BCV nueva nunca puede tocar una venta ya cobrada.
        tasa_bcv_mostrada = pedido.tasa_bcv_aplicada
        total_bolivares_mostrado = pedido.total_bolivares
    else:
        # Pendiente de pago (o cancelada): el equivalente en bolívares
        # se recalcula con la tasa BCV vigente en cada lectura — recién
        # queda fijo cuando de verdad se paga (ver models.Pedido).
        tasa_bcv_mostrada = tasa_bolivares_actual
        total_bolivares_mostrado = tasa_cambio_service.convertir_usd_a_bolivares(pedido.total, tasa_bolivares_actual)

    venta_base = {
        "id": pedido.id,
        "numero_venta": pedido.numero_pedido,
        "cliente_id": pedido.clienta_id,
        "producto_id": item.producto_id,
        "color": item.color.nombre if item.color else "",
        "cantidad": item.cantidad,
        "precio_unitario": item.precio_unitario,
        "subtotal": item.subtotal,
        "total": pedido.total,
        "tasa_bcv_aplicada": float(tasa_bcv_mostrada) if tasa_bcv_mostrada is not None else None,
        "total_bolivares": float(total_bolivares_mostrado) if total_bolivares_mostrado is not None else None,
        "total_bolivares_formateado": (
            tasa_cambio_service.formatear_bolivares(total_bolivares_mostrado)
            if total_bolivares_mostrado is not None
            else None
        ),
        "estado_entrega": estado_entrega_legacy,
        "estado_pago": estado_pago_legacy,
        "fecha_creacion": pedido.fecha_creacion.isoformat(),
        "fecha_entrega": pedido.fecha_entrega.isoformat() if pedido.fecha_entrega else None,
        "fecha_pago": pedido.fecha_pago.isoformat() if pedido.fecha_pago else None,
        "fecha_vencimiento_pago": pedido.fecha_vencimiento_pago.isoformat() if pedido.fecha_vencimiento_pago else None,
        "notas": pedido.notas or "",
        "cancelada": pedido.estado_entrega == EstadoEntrega.CANCELADO,
    }

    # float(): item.costo_unitario/pedido.costo_total/ganancia_total
    # son Numeric desde que existe "Mis materiales" (ver models.py) —
    # json.dumps no sabe serializar Decimal, así que todo lo que sale
    # en la respuesta JSON tiene que cruzar a float acá.
    ganancia_unitaria = float(item.precio_unitario - item.costo_unitario)
    costo_total = float(pedido.costo_total)
    ganancia_total = float(pedido.ganancia_total)

    return {
        **venta_base,
        "cliente": {
            "id": cliente.id,
            "nombre": cliente.nombres,
            "apellido": cliente.apellidos,
            "avatar": cliente.avatar or "",
            "telefono": cliente.telefono or "",
        },
        "producto": _serializar_producto(producto, tasa_bolivares_actual),
        "estado_entrega_info": _estado_entrega(estado_entrega_legacy),
        "estado_pago_info": _estado_pago_info(estado_pago_legacy),
        "estado_derivado": _estado_derivado(venta_base),
        "es_completa": _es_venta_completa(venta_base),
        "fecha_creacion_texto": _fecha_larga(pedido.fecha_creacion),
        "fecha_entrega_texto": _fecha_larga(pedido.fecha_entrega) if pedido.fecha_entrega else None,
        "fecha_pago_texto": _fecha_larga(pedido.fecha_pago) if pedido.fecha_pago else None,
        "fecha_vencimiento_texto": _fecha_larga(pedido.fecha_vencimiento_pago) if pedido.fecha_vencimiento_pago else None,
        "dias_restantes": dias_restantes,
        "estado_cobro": estado_cobro,
        "siguiente_estado_entrega": siguiente,
        "siguiente_estado_entrega_etiqueta": _estado_entrega(siguiente)["etiqueta"] if siguiente else None,
        "editable": (
            pedido.estado_entrega in pedidos_service.ESTADOS_ENTREGA_EDITABLES
            and pedido.estado_entrega != EstadoEntrega.CANCELADO
        ),
        "ganancia_unitaria": ganancia_unitaria,
        "costo_total": costo_total,
        "costo_total_formateado": tasa_cambio_service.formatear_usd(costo_total),
        "ganancia_total": ganancia_total,
        "ganancia_total_formateado": tasa_cambio_service.formatear_usd(ganancia_total),
        "whatsapp_url": (
            _whatsapp_url(cliente.telefono or "", cliente.nombres, pedido.total)
            if estado_cobro["atrasado"] else None
        ),
    }


def _whatsapp_url(telefono: str, nombre: str, monto: int) -> str:
    numero = re.sub(r"\D", "", telefono)
    mensaje = (
        f"Hola {nombre} 🌸, te escribimos de Nudo Rosa para recordarte que tu pago "
        f"de ${monto:,} ya está atrasado. ¿Podrías confirmarnos cuándo podrías "
        f"realizarlo? ¡Gracias! 💕"
    )
    return f"https://wa.me/{numero}?text={quote(mensaje)}"


def _guardar_imagen_producto(producto_id: int, imagen: UploadFile, contenido: bytes) -> str:
    extension = Path(imagen.filename or "").suffix.lower()
    if extension not in EXTENSIONES_IMAGEN_VALIDAS:
        extension = ".png"

    nombre_archivo = f"producto_{producto_id}{extension}"
    ruta = BASE_DIR / "static" / "images" / "producto" / nombre_archivo
    ruta.write_bytes(contenido)

    return f"/static/images/producto/{nombre_archivo}"


def _etiqueta_rango(inicio: date, fin: date, hoy: date) -> str:
    if inicio == fin:
        if inicio == hoy:
            return f"Hoy, {_fecha_corta(inicio)}"
        return _fecha_corta(inicio)

    return f"{_fecha_corta(inicio)} — {_fecha_corta(fin)}"


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("nudorosa")


def _aplicar_migraciones() -> None:
    """
    Corre `alembic upgrade head` contra la base activa (SQLite local o
    la que indique DATABASE_URL en producción) en cada arranque del
    proceso — nunca `Base.metadata.create_all()`.

    Por qué: create_all() solo CREA tablas que todavía no existen,
    nunca agrega una columna a una tabla que ya existe. Eso es
    exactamente lo que rompió `pedidos.tasa_bcv_aplicada` en Neon —
    Render arranca el proceso sin correr las migraciones a mano en
    ningún paso del deploy, create_all() ve que `pedidos` ya existe y
    no hace nada, y la app arranca "bien" con columnas faltantes hasta
    que el primer INSERT/SELECT que las toca revienta.

    Alembic sí resuelve ambos casos: contra una base nueva corre toda
    la cadena de migraciones desde cero (equivalente a create_all),
    y contra una base existente aplica solo las que falten. Es
    idempotente — si ya está en head, no hace nada — así que correrlo
    en cada arranque es seguro y no depende de configurar un comando
    de build/release aparte en el dashboard de Render.
    """
    config = AlembicConfig(str(BASE_DIR / "alembic.ini"))
    alembic_command.upgrade(config, "head")


@asynccontextmanager
async def _lifespan(app: FastAPI):
    _aplicar_migraciones()
    logger.info("Migraciones de base de datos aplicadas.")

    db = SessionLocal()
    try:
        habia_administrador = seguridad_service.obtener_administrador(db) is not None
        seguridad_service.asegurar_datos_iniciales(db)
        logger.info(
            "Usuario administrador ya existente."
            if habia_administrador
            else "Usuario administrador creado."
        )

        tasa_cambio_service.asegurar_tasa_inicial(db)
        materiales_service.asegurar_materiales_iniciales(db)
    finally:
        db.close()

    yield


app = FastAPI(title="Nudo Rosa by Ivanna", lifespan=_lifespan)

app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static",
)

templates = Jinja2Templates(directory=BASE_DIR / "templates")

# /service-worker.js tiene que poder pedirse sin sesión iniciada (p.
# ej. Chrome revisando si el sitio es instalable desde /login) — no es
# información de negocio, solo el script de caché de estáticos.
RUTAS_PUBLICAS = {"/login", "/service-worker.js"}


@app.middleware("http")
async def _requerir_sesion(request: Request, call_next):
    ruta = request.url.path

    if ruta in RUTAS_PUBLICAS or ruta.startswith("/static/"):
        return await call_next(request)

    if not request.session.get("usuario"):
        return RedirectResponse(url="/login", status_code=303)

    return await call_next(request)


# IMPORTANTE: Starlette antepone cada middleware nuevo (insert(0, ...))
# en vez de agregarlo al final, así que para que SessionMiddleware
# corra ANTES que _requerir_sesion (y así request.session ya exista
# cuando el segundo se ejecuta) tiene que registrarse DESPUÉS acá,
# no antes. Cambiar este orden rompe request.session en toda la app.
#
# El secret_key tiene que ser estable entre reinicios del proceso (por
# eso viene de una variable de entorno, no de secrets.token_hex() en
# cada arranque): si cambia, toda cookie de sesión firmada con el valor
# anterior queda inválida y la sesión se cierra sola. En Render eso
# pasa en cada deploy y, en el plan free, cada vez que el servicio
# despierta de una siesta por inactividad — hay que configurar
# SECRET_KEY ahí para que iniciar sesión "dure" de verdad.
app.add_middleware(
    SessionMiddleware, secret_key=os.environ.get("SECRET_KEY", secrets.token_hex(32))
)


def _contar_cobros_pendientes_global() -> int:
    from database import SessionLocal

    db = SessionLocal()
    try:
        return len(pedidos_service.listar_cobros_pendientes(db))
    finally:
        db.close()


def _contar_poco_stock_global() -> int:
    from database import SessionLocal

    db = SessionLocal()
    try:
        configuracion = seguridad_service.obtener_configuracion(db)
        return sum(
            1
            for p in productos_service.listar_productos_activos(db)
            if _estado_producto(p.stock_actual, configuracion.limite_poco_stock)["clave"] != "disponible"
        )
    finally:
        db.close()


def _tasa_bcv_valor_global() -> float | None:
    from database import SessionLocal

    db = SessionLocal()
    try:
        tasa = _tasa_bolivares_actual(db)
        return float(tasa) if tasa is not None else None
    finally:
        db.close()


# Expuestos como funciones globales de Jinja para que el popover del
# Centro de Administración (incluido en _bottom_nav.html en TODAS las
# pantallas) pueda mostrar sus badges sin tener que agregar estos
# valores al contexto de cada ruta existente. Abren su propia sesión
# corta porque _bottom_nav.html no participa del Depends(get_db) de
# la ruta que lo incluye.
templates.env.globals["contar_cobros_pendientes"] = _contar_cobros_pendientes_global
templates.env.globals["contar_poco_stock"] = _contar_poco_stock_global

# Misma idea para el equivalente en bolívares de un precio en dólares:
# cualquier plantilla puede pedir `{% set tasa_actual = tasa_bcv_valor() %}`
# una vez y reusarla en un loop, sin que cada ruta tenga que acordarse
# de agregarla a su contexto. convertir_usd_a_bolivares/formatear_usd/
# formatear_bolivares son las mismas funciones puras que usa
# services/tasa_cambio.py — una sola fuente de verdad para el formato.
templates.env.globals["tasa_bcv_valor"] = _tasa_bcv_valor_global
templates.env.globals["formatear_usd"] = tasa_cambio_service.formatear_usd
templates.env.globals["formatear_bolivares"] = tasa_cambio_service.formatear_bolivares
templates.env.globals["convertir_usd_a_bolivares"] = tasa_cambio_service.convertir_usd_a_bolivares


# Copy estático de la pantalla legacy /mas (reemplazada por el
# Centro de Administración en el popover de "Más"), no es dato de
# negocio — no vive en la base de datos.
AJUSTES = [
    {"titulo": "Mi negocio", "subtitulo": "Datos de Nudo Rosa", "icono": "🏬"},
    {"titulo": "Notificaciones", "subtitulo": "Pedidos, cobros y recordatorios", "icono": "🔔"},
    {"titulo": "Métodos de cobro", "subtitulo": "Transferencia, efectivo", "icono": "💳"},
    {"titulo": "Ayuda y soporte", "subtitulo": "¿Necesitás una mano?", "icono": "💬"},
]

FRASES_IVANNA = [
    "🌸 Hoy será un gran día.",
    "💕 ¡Gracias por hacer felices a tantas niñas!",
    "🎀 Cada moño lleva un pedacito de amor.",
    "✨ ¡Vamos por muchas ventas!",
    "🌷 Tus clientas te están esperando.",
    "💖 Hoy puedes crear algo hermoso.",
    "🎁 Cada pedido cuenta una historia.",
    "🌈 Nunca dejes de crear.",
    "👑 Tú haces sonreír a muchas niñas.",
    "🎀 ¡Bienvenida nuevamente!",
]

FRASES_EXITO_LOGIN = [
    "¡Qué emoción verte de nuevo! 💕",
    "¡Vamos a trabajar juntas! 🎀",
]


def _saludo_ivanna(hora: int) -> list[str]:
    if 5 <= hora < 12:
        return ["¡Buenos días! 🌸", "Soy Ivanna.", "¡Vamos a crear moños hermosos hoy!"]

    if 12 <= hora < 19:
        return ["¡Buenas tardes! 💕", "¡Qué gusto verte!", "¿Lista para atender a tus clientas?"]

    return ["¡Buenas noches! 🎀", "Terminemos los pedidos del día."]


RUTA_SERVICE_WORKER = BASE_DIR / "static" / "js" / "service-worker.js"


@app.get("/service-worker.js")
async def service_worker():
    # Se sirve desde la raíz (no /static/service-worker.js) para que
    # su alcance por defecto cubra toda la app ("/"), no solo /static/.
    # Cache-Control: no-cache fuerza a que el navegador siempre
    # revalide el script contra el servidor antes de usarlo, para que
    # una actualización del Service Worker se detecte de inmediato.
    return FileResponse(
        RUTA_SERVICE_WORKER,
        media_type="application/javascript",
        headers={
            "Service-Worker-Allowed": "/",
            "Cache-Control": "no-cache",
        },
    )


@app.get("/login")
async def login_pantalla(request: Request, db: Session = Depends(get_db)):
    if request.session.get("usuario"):
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "saludo": _saludo_ivanna(datetime.now().hour),
            "frase": random.choice(FRASES_IVANNA),
            "frase_exito": random.choice(FRASES_EXITO_LOGIN),
        },
    )


@app.post("/login")
async def login_enviar(
    request: Request,
    usuario: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    usuario = usuario.strip()

    if seguridad_service.verificar_credenciales(db, usuario, password) is None:
        return JSONResponse(
            status_code=401,
            content={"error": "Usuario o contraseña incorrectos."},
        )

    request.session["usuario"] = usuario
    return JSONResponse(content={"ok": True})


@app.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


@app.get("/")
async def inicio(request: Request, db: Session = Depends(get_db)):
    configuracion = seguridad_service.obtener_configuracion(db)
    resumen = resumen_service.resumen_dia(db, configuracion.limite_poco_stock)
    productos_count = len(productos_service.listar_productos_activos(db))

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "nombre": configuracion.nombre_administrador,
            "estrellas": 80,
            "nivel": "Pequeña diseñadora",
            "active_nav": "inicio",
            "resumen": resumen,
            "productos_count": productos_count,
        },
    )


@app.get("/ventas")
async def ventas(
    request: Request,
    fecha_inicio: str | None = None,
    fecha_fin: str | None = None,
    db: Session = Depends(get_db),
):
    hoy = date.today()

    inicio = _parsear_fecha(fecha_inicio) or hoy
    fin = _parsear_fecha(fecha_fin) or hoy

    if fin < inicio:
        inicio, fin = fin, inicio

    tasa_actual = _tasa_bolivares_actual(db)
    completas = [_venta_enriquecida(p, tasa_actual) for p in pedidos_service.listar_ventas_completadas(db)]
    completas = [v for v in completas if v is not None]
    activas = [_venta_enriquecida(p, tasa_actual) for p in pedidos_service.listar_pedidos_activos(db)]
    activas += [_venta_enriquecida(p, tasa_actual) for p in pedidos_service.listar_cobros_pendientes(db)]
    ids_activas = {v["id"] for v in activas if v is not None}

    configuracion = seguridad_service.obtener_configuracion(db)
    productos_con_estado = [
        {**_serializar_producto(p, tasa_actual), "estado": _estado_producto(p.stock_actual, configuracion.limite_poco_stock)}
        for p in productos_service.listar_productos_activos(db)
    ]
    clientes = [clientas_service.serializar_clienta(db, c) for c in clientas_service.listar_clientas_activas(db)]
    colores = [{"nombre": c.nombre, "hex": c.codigo_hex} for c in colores_service.listar_colores_activos(db)]

    return templates.TemplateResponse(
        request=request,
        name="ventas.html",
        context={
            "active_nav": None,
            "ventas": completas,
            "ultimas_ventas": completas[:3],
            "total_ventas": sum(v["total"] for v in completas),
            "ganancia_total": sum(v["ganancia_total"] for v in completas),
            "transacciones_activas": len(ids_activas),
            "fecha_inicio": inicio.isoformat(),
            "fecha_fin": fin.isoformat(),
            "rango_texto": _etiqueta_rango(inicio, fin, hoy),
            "clientes": clientes,
            "productos": productos_con_estado,
            "colores": colores,
        },
    )


@app.get("/ventas/todas")
async def ventas_todas(request: Request, db: Session = Depends(get_db)):
    tasa_actual = _tasa_bolivares_actual(db)
    todas = [_venta_enriquecida(p, tasa_actual) for p in pedidos_service.listar_ventas_completadas(db)]
    todas = [v for v in todas if v is not None]

    configuracion = seguridad_service.obtener_configuracion(db)
    productos_con_estado = [
        {**_serializar_producto(p, tasa_actual), "estado": _estado_producto(p.stock_actual, configuracion.limite_poco_stock)}
        for p in productos_service.listar_productos_activos(db)
    ]
    clientes = [clientas_service.serializar_clienta(db, c) for c in clientas_service.listar_clientas_activas(db)]
    colores = [{"nombre": c.nombre, "hex": c.codigo_hex} for c in colores_service.listar_colores_activos(db)]

    return templates.TemplateResponse(
        request=request,
        name="ventas_todas.html",
        context={
            "active_nav": None,
            "ventas": todas,
            "clientes": clientes,
            "productos": productos_con_estado,
            "colores": colores,
        },
    )


@app.get("/clientes")
async def clientes(request: Request, db: Session = Depends(get_db)):
    clientes_serializados = [
        clientas_service.serializar_clienta(db, c) for c in clientas_service.listar_clientas_activas(db)
    ]
    favorita = max(clientes_serializados, key=lambda c: c["pedidos"], default=None)

    return templates.TemplateResponse(
        request=request,
        name="clientes.html",
        context={
            "active_nav": None,
            "clientes": clientes_serializados,
            "favorita_id": favorita["id"] if favorita else None,
        },
    )


@app.get("/clientes/nueva")
async def cliente_nueva(request: Request, volver_a: str = ""):
    return templates.TemplateResponse(
        request=request,
        name="cliente_nueva.html",
        context={
            "active_nav": None,
            "cliente": None,
            "avatares_disponibles": _listar_avatares(),
            "volver_a": volver_a,
        },
    )


@app.post("/clientes/nueva")
async def cliente_nueva_guardar(
    nombre: str = Form(...),
    apellido: str = Form(...),
    telefono: str = Form(...),
    fecha_nacimiento: str = Form(""),
    direccion: str = Form(""),
    email: str = Form(""),
    notas: str = Form(""),
    avatar: str = Form(""),
    volver_a: str = Form(""),
    db: Session = Depends(get_db),
):
    cliente = clientas_service.crear_clienta(
        db,
        nombre=nombre.strip(),
        apellido=apellido.strip(),
        telefono=telefono.strip(),
        fecha_nacimiento=fecha_nacimiento,
        direccion=direccion.strip(),
        email=email.strip(),
        notas=notas.strip(),
        avatar=avatar.strip(),
    )

    # Si la clienta se registró desde el flujo de "Nueva venta" (ya
    # sea abierto desde Ventas o desde Pedidos), se vuelve a esa
    # misma pantalla con la clienta ya seleccionada en vez del
    # destino habitual (la ficha de la clienta).
    if volver_a in ("pedidos", "ventas"):
        return RedirectResponse(url=f"/{volver_a}?nueva_clienta={cliente.id}", status_code=303)

    return RedirectResponse(url=f"/clientes/{cliente.id}", status_code=303)


@app.get("/clientes/{cliente_id}")
async def cliente_detalle(request: Request, cliente_id: int, db: Session = Depends(get_db)):
    cliente = clientas_service.get_clienta(db, cliente_id)
    if cliente is None:
        raise HTTPException(status_code=404, detail="Clienta no encontrada")

    cliente_serializado = clientas_service.serializar_clienta(db, cliente)

    return templates.TemplateResponse(
        request=request,
        name="cliente_detalle.html",
        context={
            "active_nav": None,
            "cliente": cliente_serializado,
            "historial": clientas_service.listar_historial_compras(db, cliente_id),
            "insignias": _insignias_cliente(cliente_serializado),
        },
    )


@app.get("/clientes/{cliente_id}/editar")
async def cliente_editar(request: Request, cliente_id: int, db: Session = Depends(get_db)):
    cliente = clientas_service.get_clienta(db, cliente_id)
    if cliente is None:
        raise HTTPException(status_code=404, detail="Clienta no encontrada")

    return templates.TemplateResponse(
        request=request,
        name="cliente_nueva.html",
        context={
            "active_nav": None,
            "cliente": clientas_service.serializar_clienta(db, cliente),
            "avatares_disponibles": _listar_avatares(),
        },
    )


@app.post("/clientes/{cliente_id}/editar")
async def cliente_editar_guardar(
    cliente_id: int,
    nombre: str = Form(...),
    apellido: str = Form(...),
    telefono: str = Form(...),
    fecha_nacimiento: str = Form(""),
    direccion: str = Form(""),
    email: str = Form(""),
    notas: str = Form(""),
    avatar: str = Form(""),
    db: Session = Depends(get_db),
):
    cliente = clientas_service.actualizar_clienta(
        db,
        cliente_id,
        nombre=nombre.strip(),
        apellido=apellido.strip(),
        telefono=telefono.strip(),
        fecha_nacimiento=fecha_nacimiento,
        direccion=direccion.strip(),
        email=email.strip(),
        notas=notas.strip(),
        avatar=avatar.strip(),
    )
    if cliente is None:
        raise HTTPException(status_code=404, detail="Clienta no encontrada")

    return RedirectResponse(url=f"/clientes/{cliente_id}", status_code=303)


@app.post("/clientes/{cliente_id}/eliminar")
async def cliente_eliminar(cliente_id: int, db: Session = Depends(get_db)):
    cliente = clientas_service.desactivar_clienta(db, cliente_id)
    if cliente is None:
        raise HTTPException(status_code=404, detail="Clienta no encontrada")

    return RedirectResponse(url="/clientes", status_code=303)


@app.get("/inventario")
async def inventario(request: Request, db: Session = Depends(get_db)):
    configuracion = seguridad_service.obtener_configuracion(db)
    tasa_actual = _tasa_bolivares_actual(db)
    productos_con_estado = [
        {**_serializar_producto(p, tasa_actual), "estado": _estado_producto(p.stock_actual, configuracion.limite_poco_stock)}
        for p in productos_service.listar_productos_activos(db)
    ]

    return templates.TemplateResponse(
        request=request,
        name="inventario.html",
        context={
            "active_nav": None,
            "productos": productos_con_estado,
            "imagenes_producto_disponibles": _listar_imagenes_producto_predeterminadas(),
        },
    )


@app.get("/cobros")
async def cobros(request: Request, db: Session = Depends(get_db)):
    tasa_actual = _tasa_bolivares_actual(db)
    cobros_lista = [_venta_enriquecida(p, tasa_actual) for p in pedidos_service.listar_cobros_pendientes(db)]
    cobros_lista = [c for c in cobros_lista if c is not None]
    colores = [{"nombre": c.nombre, "hex": c.codigo_hex} for c in colores_service.listar_colores_activos(db)]

    return templates.TemplateResponse(
        request=request,
        name="cobros.html",
        context={
            "active_nav": None,
            "cobros": cobros_lista,
            "total_pendiente": sum(c["total"] for c in cobros_lista),
            "colores": colores,
        },
    )


@app.get("/productos")
async def productos(request: Request, db: Session = Depends(get_db)):
    tasa_actual = _tasa_bolivares_actual(db)
    productos_serializados = [
        _serializar_producto(p, tasa_actual) for p in productos_service.listar_productos_activos(db)
    ]

    return templates.TemplateResponse(
        request=request,
        name="productos.html",
        context={
            "active_nav": "productos",
            "productos": productos_serializados,
            "imagenes_producto_disponibles": _listar_imagenes_producto_predeterminadas(),
        },
    )


@app.get("/productos/{producto_id}")
async def producto_detalle(request: Request, producto_id: int, db: Session = Depends(get_db)):
    producto = productos_service.get_producto(db, producto_id)
    if producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    configuracion = seguridad_service.obtener_configuracion(db)
    tasa_actual = _tasa_bolivares_actual(db)

    return templates.TemplateResponse(
        request=request,
        name="producto_detalle.html",
        context={
            "active_nav": "productos",
            "producto": _serializar_producto(producto, tasa_actual),
            "estado": _estado_producto(producto.stock_actual, configuracion.limite_poco_stock),
            "ventas_recientes": pedidos_service.listar_ventas_recientes_por_producto(db, producto_id),
        },
    )


def _parsear_datos_materiales_form(
    lazos_por_metro_tela: str,
    lazos_por_barra_silicon: str,
    cantidad_ganchos: str,
    usa_hilo: str,
    minutos_elaboracion: str,
) -> dict | None:
    """Las 5 preguntas de "Mis materiales" del formulario de
    producto — reemplazan la entrada manual de costo (ver
    CLAUDE.md). None si algún valor requerido no es un número
    válido, para que la ruta devuelva un error claro."""

    tela = _parsear_entero_no_negativo(lazos_por_metro_tela)
    silicon = _parsear_entero_no_negativo(lazos_por_barra_silicon)
    ganchos = _parsear_entero_no_negativo(cantidad_ganchos)
    minutos = _parsear_entero_no_negativo(minutos_elaboracion)

    if tela is None or silicon is None or ganchos is None or minutos is None:
        return None

    return {
        "lazos_por_metro_tela": tela,
        "lazos_por_barra_silicon": silicon,
        "cantidad_ganchos": ganchos,
        "usa_hilo": usa_hilo in ("on", "true", "1"),
        "minutos_elaboracion": minutos,
    }


@app.post("/productos/nuevo")
async def productos_nuevo_guardar(
    nombre: str = Form(...),
    precio_publico: str = Form(...),
    stock_inicial: str = Form("0"),
    lazos_por_metro_tela: str = Form(...),
    lazos_por_barra_silicon: str = Form(...),
    cantidad_ganchos: str = Form(...),
    usa_hilo: str = Form(""),
    minutos_elaboracion: str = Form(...),
    imagen: UploadFile | None = File(None),
    imagen_predeterminada: str = Form(""),
    db: Session = Depends(get_db),
):
    nombre = nombre.strip()
    precio = _parsear_entero_no_negativo(precio_publico)
    stock = _parsear_entero_no_negativo(stock_inicial)
    datos_materiales = _parsear_datos_materiales_form(
        lazos_por_metro_tela, lazos_por_barra_silicon, cantidad_ganchos, usa_hilo, minutos_elaboracion
    )

    if not nombre or precio is None or stock is None or datos_materiales is None:
        return JSONResponse(
            status_code=422,
            content={"error": "Revisá el nombre, el precio, el stock inicial y los datos de materiales."},
        )

    try:
        producto = productos_service.crear_producto(
            db,
            nombre=nombre,
            precio_publico=precio,
            stock_inicial=stock,
            **datos_materiales,
        )
    except ErrorNegocio as error:
        return JSONResponse(status_code=422, content={"error": str(error)})

    if imagen is not None and imagen.filename:
        contenido = await imagen.read()
        if contenido:
            producto.imagen = _guardar_imagen_producto(producto.id, imagen, contenido)
            db.commit()
            db.refresh(producto)
    elif imagen_predeterminada and imagen_predeterminada in _listar_imagenes_producto_predeterminadas():
        # Imagen ya existente en static/images/producto/: se guarda la
        # ruta tal cual, sin copiar ni volver a subir el archivo.
        producto.imagen = imagen_predeterminada
        db.commit()
        db.refresh(producto)

    configuracion = seguridad_service.obtener_configuracion(db)
    tasa_actual = _tasa_bolivares_actual(db)
    return JSONResponse(content={
        "producto": _serializar_producto(producto, tasa_actual),
        "estado": _estado_producto(producto.stock_actual, configuracion.limite_poco_stock),
    })


@app.post("/productos/{producto_id}/ajustar")
async def productos_ajustar_guardar(
    producto_id: int,
    cantidad_agregar: str = Form(...),
    costo_produccion: str = Form(...),
    precio_publico: str = Form(...),
    db: Session = Depends(get_db),
):
    cantidad = _parsear_entero_no_negativo(cantidad_agregar)
    costo = _parsear_entero_no_negativo(costo_produccion)
    precio = _parsear_entero_no_negativo(precio_publico)

    if cantidad is None or costo is None or precio is None:
        return JSONResponse(
            status_code=422,
            content={"error": "Revisá la cantidad, el costo y el precio ingresados."},
        )

    try:
        producto = productos_service.ajustar_producto(
            db,
            producto_id,
            cantidad_agregar=cantidad,
            costo_produccion=costo,
            precio_publico=precio,
        )
    except ErrorNegocio as error:
        return JSONResponse(status_code=422, content={"error": str(error)})

    if producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    configuracion = seguridad_service.obtener_configuracion(db)
    tasa_actual = _tasa_bolivares_actual(db)
    return JSONResponse(content={
        "producto": _serializar_producto(producto, tasa_actual),
        "estado": _estado_producto(producto.stock_actual, configuracion.limite_poco_stock),
    })


@app.post("/productos/{producto_id}/editar")
async def productos_editar_guardar(
    producto_id: int,
    nombre: str = Form(...),
    precio_publico: str = Form(...),
    stock: str = Form(...),
    lazos_por_metro_tela: str = Form(...),
    lazos_por_barra_silicon: str = Form(...),
    cantidad_ganchos: str = Form(...),
    usa_hilo: str = Form(""),
    minutos_elaboracion: str = Form(...),
    imagen: UploadFile | None = File(None),
    imagen_predeterminada: str = Form(""),
    db: Session = Depends(get_db),
):
    nombre = nombre.strip()
    precio = _parsear_entero_no_negativo(precio_publico)
    stock_valor = _parsear_entero_no_negativo(stock)
    datos_materiales = _parsear_datos_materiales_form(
        lazos_por_metro_tela, lazos_por_barra_silicon, cantidad_ganchos, usa_hilo, minutos_elaboracion
    )

    if not nombre or precio is None or stock_valor is None or datos_materiales is None:
        return JSONResponse(
            status_code=422,
            content={"error": "Revisá el nombre, el precio, el stock y los datos de materiales."},
        )

    imagen_final = ""
    if imagen is not None and imagen.filename:
        contenido = await imagen.read()
        if contenido:
            imagen_final = _guardar_imagen_producto(producto_id, imagen, contenido)
    elif imagen_predeterminada and imagen_predeterminada in _listar_imagenes_producto_predeterminadas():
        # Imagen ya existente en static/images/producto/: se guarda la
        # ruta tal cual, sin copiar ni volver a subir el archivo.
        imagen_final = imagen_predeterminada

    try:
        producto = productos_service.actualizar_producto(
            db,
            producto_id,
            nombre=nombre,
            precio_publico=precio,
            stock=stock_valor,
            imagen=imagen_final,
            **datos_materiales,
        )
    except ErrorNegocio as error:
        return JSONResponse(status_code=422, content={"error": str(error)})

    if producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    configuracion = seguridad_service.obtener_configuracion(db)
    tasa_actual = _tasa_bolivares_actual(db)
    return JSONResponse(content={
        "producto": _serializar_producto(producto, tasa_actual),
        "estado": _estado_producto(producto.stock_actual, configuracion.limite_poco_stock),
    })


@app.post("/productos/{producto_id}/eliminar")
async def productos_eliminar_guardar(producto_id: int, db: Session = Depends(get_db)):
    producto = productos_service.desactivar_producto(db, producto_id)

    if producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    return JSONResponse(content={"ok": True})


@app.get("/pedidos")
async def pedidos(request: Request, db: Session = Depends(get_db)):
    configuracion = seguridad_service.obtener_configuracion(db)
    tasa_actual = _tasa_bolivares_actual(db)
    productos_con_estado = [
        {**_serializar_producto(p, tasa_actual), "estado": _estado_producto(p.stock_actual, configuracion.limite_poco_stock)}
        for p in productos_service.listar_productos_activos(db)
    ]
    pedidos_lista = [_venta_enriquecida(p, tasa_actual) for p in pedidos_service.listar_pedidos_activos(db)]
    pedidos_lista = [p for p in pedidos_lista if p is not None]
    clientes = [clientas_service.serializar_clienta(db, c) for c in clientas_service.listar_clientas_activas(db)]
    colores = [{"nombre": c.nombre, "hex": c.codigo_hex} for c in colores_service.listar_colores_activos(db)]

    return templates.TemplateResponse(
        request=request,
        name="pedidos.html",
        context={
            "active_nav": "pedidos",
            "pedidos": pedidos_lista,
            "clientes": clientes,
            "productos": productos_con_estado,
            "colores": colores,
        },
    )


@app.post("/ventas/nueva")
async def ventas_nueva_guardar(
    cliente_id: str = Form(...),
    producto_id: str = Form(...),
    color: str = Form(...),
    cantidad: str = Form(...),
    entrega_ahora: str = Form(""),
    pago_ahora: str = Form(""),
    fecha_vencimiento_pago: str = Form(""),
    notas: str = Form(""),
    db: Session = Depends(get_db),
):
    cliente_id_num = _parsear_entero_no_negativo(cliente_id)
    producto_id_num = _parsear_entero_no_negativo(producto_id)
    cantidad_num = _parsear_entero_no_negativo(cantidad)
    color = color.strip()

    if cliente_id_num is None:
        return JSONResponse(status_code=422, content={"error": "Elegí una clienta para la venta."})

    if producto_id_num is None:
        return JSONResponse(status_code=422, content={"error": "Elegí un producto para la venta."})

    if not color:
        return JSONResponse(status_code=422, content={"error": "Elegí un color."})

    if cantidad_num is None or cantidad_num < 1:
        return JSONResponse(status_code=422, content={"error": "La cantidad debe ser al menos 1."})

    configuracion = seguridad_service.obtener_configuracion(db)

    try:
        pedido = pedidos_service.crear_pedido(
            db,
            clienta_id=cliente_id_num,
            producto_id=producto_id_num,
            color_nombre=color,
            cantidad=cantidad_num,
            entrega_ahora=entrega_ahora == "1",
            pago_ahora=pago_ahora == "1",
            notas=notas.strip(),
            fecha_vencimiento_pago=_parsear_fecha(fecha_vencimiento_pago),
            dias_credito=configuracion.dias_credito,
        )
    except ErrorNegocio as error:
        return JSONResponse(status_code=422, content={"error": str(error)})

    return JSONResponse(content={"venta": _venta_enriquecida(pedido, _tasa_bolivares_actual(db))})


@app.post("/ventas/{venta_id}/entrega")
async def ventas_cambiar_entrega_guardar(venta_id: int, estado: str = Form(...), db: Session = Depends(get_db)):
    nuevo_estado_enum = MAPA_ENTREGA_DESDE_LEGACY.get(estado)
    if nuevo_estado_enum is None or nuevo_estado_enum == EstadoEntrega.CANCELADO:
        return JSONResponse(status_code=422, content={"error": "Estado inválido."})

    configuracion = seguridad_service.obtener_configuracion(db)

    try:
        pedido = pedidos_service.marcar_entrega(db, venta_id, nuevo_estado_enum, configuracion.dias_credito)
    except ErrorNegocio as error:
        return JSONResponse(status_code=422, content={"error": str(error)})

    return JSONResponse(content={"venta": _venta_enriquecida(pedido, _tasa_bolivares_actual(db))})


@app.post("/ventas/{venta_id}/pago")
async def ventas_marcar_pago_guardar(venta_id: int, db: Session = Depends(get_db)):
    try:
        pedido = pedidos_service.marcar_pago(db, venta_id)
    except ErrorNegocio as error:
        return JSONResponse(status_code=422, content={"error": str(error)})

    return JSONResponse(content={"venta": _venta_enriquecida(pedido, _tasa_bolivares_actual(db))})


@app.post("/ventas/{venta_id}/editar")
async def ventas_editar_guardar(
    venta_id: int,
    color: str = Form(...),
    cantidad: str = Form(...),
    notas: str = Form(""),
    db: Session = Depends(get_db),
):
    color = color.strip()
    cantidad_num = _parsear_entero_no_negativo(cantidad)

    if not color:
        return JSONResponse(status_code=422, content={"error": "Elegí un color."})

    if cantidad_num is None or cantidad_num < 1:
        return JSONResponse(status_code=422, content={"error": "La cantidad debe ser al menos 1."})

    try:
        pedido = pedidos_service.editar_pedido(db, venta_id, color_nombre=color, cantidad=cantidad_num, notas=notas.strip())
    except ErrorNegocio as error:
        return JSONResponse(status_code=422, content={"error": str(error)})

    return JSONResponse(content={"venta": _venta_enriquecida(pedido, _tasa_bolivares_actual(db))})


@app.post("/ventas/{venta_id}/cancelar")
async def ventas_cancelar_guardar(venta_id: int, db: Session = Depends(get_db)):
    try:
        pedido = pedidos_service.cancelar_pedido(db, venta_id)
    except ErrorNegocio as error:
        return JSONResponse(status_code=422, content={"error": str(error)})

    return JSONResponse(content={"venta": _venta_enriquecida(pedido, _tasa_bolivares_actual(db))})


@app.get("/resumen")
async def resumen(request: Request, db: Session = Depends(get_db)):
    semana = resumen_service.resumen_semana(db)
    configuracion = seguridad_service.obtener_configuracion(db)
    resumen_hoy = resumen_service.resumen_dia(db, configuracion.limite_poco_stock)

    return templates.TemplateResponse(
        request=request,
        name="resumen.html",
        context={
            "active_nav": None,
            "semana": semana,
            "max_monto": max((d["monto"] for d in semana), default=0) or 1,
            "resumen": resumen_hoy,
        },
    )


@app.get("/mas")
async def mas(request: Request, db: Session = Depends(get_db)):
    configuracion = seguridad_service.obtener_configuracion(db)

    return templates.TemplateResponse(
        request=request,
        name="mas.html",
        context={
            "active_nav": "mas",
            "nombre": configuracion.nombre_administrador,
            "ajustes": AJUSTES,
        },
    )


@app.get("/reportes")
async def reportes(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="reportes.html",
        context={"active_nav": None},
    )


@app.get("/configuracion")
async def configuracion(request: Request, db: Session = Depends(get_db)):
    usuario = seguridad_service.obtener_administrador(db)
    configuracion_actual = seguridad_service.obtener_configuracion(db)
    tasa_bcv = _serializar_tasa_bcv(tasa_cambio_service.obtener_tasa_activa(db))

    return templates.TemplateResponse(
        request=request,
        name="configuracion.html",
        context={
            "active_nav": None,
            "seguridad": {
                "nombre_administrador": usuario.nombre,
                "usuario": usuario.nombre_usuario,
            },
            "configuracion": configuracion_actual,
            "tasa_bcv": tasa_bcv,
        },
    )


@app.post("/configuracion/seguridad")
async def configuracion_seguridad_guardar(
    nombre_administrador: str = Form(...),
    usuario: str = Form(...),
    password: str = Form(""),
    db: Session = Depends(get_db),
):
    nombre_administrador = nombre_administrador.strip()
    usuario = usuario.strip()

    if not nombre_administrador or not usuario:
        return JSONResponse(
            status_code=422,
            content={"error": "Completa el nombre y el usuario."},
        )

    usuario_actualizado = seguridad_service.actualizar_seguridad(db, nombre_administrador, usuario, password.strip())

    return JSONResponse(content={
        "ok": True,
        "nombre_administrador": usuario_actualizado.nombre,
        "usuario": usuario_actualizado.nombre_usuario,
    })


@app.post("/configuracion/tasa-bcv/actualizar")
async def configuracion_tasa_bcv_actualizar(db: Session = Depends(get_db)):
    # tasa_cambio_service ya nunca deja la ruta sin datos que devolver
    # (ni con la consulta al BCV ok, ni si falla y hay que mantener la
    # tasa anterior) — acá solo se traduce el resultado a JSON.
    resultado = tasa_cambio_service.actualizar_tasa_automatica(db)
    if resultado["ok"]:
        # El costo de los productos que usan "Mis materiales" está en
        # bolívares y se convierte a dólares con esta tasa — una tasa
        # nueva los deja desactualizados hasta que se recalculan acá.
        materiales_service.recalcular_productos_con_materiales(db)
    return JSONResponse(content=resultado)


@app.post("/configuracion/tasa-bcv/manual")
async def configuracion_tasa_bcv_manual(
    tasa_bolivares: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        tasa_decimal = Decimal(tasa_bolivares.strip().replace(",", "."))
    except InvalidOperation:
        return JSONResponse(
            status_code=422,
            content={"ok": False, "error": "Ingresá un número válido para la tasa."},
        )

    try:
        resultado = tasa_cambio_service.guardar_tasa_manual(db, tasa_decimal)
    except ErrorNegocio as error:
        return JSONResponse(status_code=422, content={"ok": False, "error": str(error)})

    materiales_service.recalcular_productos_con_materiales(db)
    return JSONResponse(content=resultado)


def _serializar_material(material) -> dict:
    meta = materiales_service.METADATA_MATERIAL[material.tipo]
    return {
        "tipo": material.tipo,
        "nombre": material.nombre,
        "unidad_compra": material.unidad_compra,
        "usa_rendimiento": meta["usa_rendimiento"],
        "precio": float(material.precio),
        "precio_formateado": tasa_cambio_service.formatear_bolivares(material.precio),
        "rendimiento": material.rendimiento,
    }


@app.get("/materiales")
async def materiales_pantalla(request: Request, db: Session = Depends(get_db)):
    configuracion_actual = seguridad_service.obtener_configuracion(db)

    return templates.TemplateResponse(
        request=request,
        name="materiales.html",
        context={
            "active_nav": None,
            "materiales": [_serializar_material(m) for m in materiales_service.listar_materiales(db)],
            "configuracion": configuracion_actual,
        },
    )


@app.post("/materiales/{tipo}/actualizar")
async def materiales_actualizar(
    tipo: str,
    precio: str = Form(...),
    rendimiento: str = Form(""),
    db: Session = Depends(get_db),
):
    try:
        precio_decimal = Decimal(precio.strip().replace(",", "."))
    except InvalidOperation:
        return JSONResponse(status_code=422, content={"error": "Ingresá un precio válido."})

    rendimiento_num = _parsear_entero_no_negativo(rendimiento) if rendimiento.strip() else None

    try:
        material = materiales_service.actualizar_material(db, tipo, precio_decimal, rendimiento_num)
    except ErrorNegocio as error:
        return JSONResponse(status_code=422, content={"error": str(error)})

    return JSONResponse(content={"material": _serializar_material(material)})


@app.post("/configuracion/produccion")
async def configuracion_produccion_guardar(
    porcentaje_pequenos_materiales: str = Form(...),
    valor_hora_trabajo: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        porcentaje = Decimal(porcentaje_pequenos_materiales.strip().replace(",", "."))
        valor_hora = Decimal(valor_hora_trabajo.strip().replace(",", "."))
    except InvalidOperation:
        return JSONResponse(status_code=422, content={"error": "Ingresá valores numéricos válidos."})

    if porcentaje < 0 or valor_hora < 0:
        return JSONResponse(status_code=422, content={"error": "Los valores no pueden ser negativos."})

    configuracion_actual = seguridad_service.obtener_configuracion(db)
    configuracion_actual.porcentaje_pequenos_materiales = porcentaje
    configuracion_actual.valor_hora_trabajo = valor_hora
    db.commit()

    materiales_service.recalcular_productos_con_materiales(db)

    return JSONResponse(content={
        "ok": True,
        "porcentaje_pequenos_materiales": float(porcentaje),
        "valor_hora_trabajo": float(valor_hora),
    })


@app.post("/materiales/calcular-costo")
async def materiales_calcular_costo(
    lazos_por_metro_tela: str = Form(...),
    lazos_por_barra_silicon: str = Form(...),
    cantidad_ganchos: str = Form(...),
    usa_hilo: str = Form(""),
    minutos_elaboracion: str = Form(...),
    db: Session = Depends(get_db),
):
    """Vista previa en vivo para el formulario de producto (ver
    "Lo que costó hacerlo" en app.js) — no guarda nada."""

    datos = _parsear_datos_materiales_form(
        lazos_por_metro_tela, lazos_por_barra_silicon, cantidad_ganchos, usa_hilo, minutos_elaboracion
    )
    if datos is None:
        return JSONResponse(status_code=422, content={"error": "Completá los datos de materiales."})

    try:
        desglose = materiales_service.calcular_costo_bs(db, **datos)
    except ErrorNegocio as error:
        return JSONResponse(status_code=422, content={"error": str(error)})

    tasa_activa = tasa_cambio_service.obtener_tasa_activa(db)
    tasa_bolivares = tasa_activa.tasa_bolivares if tasa_activa else None
    total_usd = materiales_service.convertir_bolivares_a_usd(desglose["total_bs"], tasa_bolivares)

    return JSONResponse(content={
        "total_bs": float(desglose["total_bs"]),
        "total_bs_formateado": tasa_cambio_service.formatear_bolivares(desglose["total_bs"]),
        "total_usd": float(total_usd) if total_usd is not None else None,
        "total_usd_formateado": tasa_cambio_service.formatear_usd(total_usd) if total_usd is not None else None,
    })


@app.get("/ayuda")
async def ayuda(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="ayuda.html",
        context={"active_nav": None},
    )
