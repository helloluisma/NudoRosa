"""
Datos de ejemplo para las pantallas de Nudo Rosa.

Estos datos son de muestra: cuando exista una base de datos real,
las funciones get_* de este módulo son el único lugar que hay que
reemplazar — las rutas en main.py y las plantillas no deberían
necesitar cambios.
"""

import hashlib
import hmac
import json
import secrets
from datetime import date, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# VENTAS es la ÚNICA transacción del negocio: Pedidos y Cobros son
# vistas filtradas de esta misma lista (por estado_entrega / por
# estado_pago), nunca datos propios — ver _listar_ventas_pedidos()
# y _listar_ventas_cobros() en main.py. "entrega" y "pago" son
# independientes a propósito: una clienta puede tener el lazo y
# todavía deber el pago, o haber pagado por adelantado.
VENTAS = [
    {
        "id": 1,
        "numero_venta": "1041",
        "cliente_id": 7,
        "producto_id": 3,
        "color": "Lila",
        "cantidad": 1,
        "precio_unitario": 90,
        "subtotal": 90,
        "total": 90,
        "estado_entrega": "cancelado",
        "estado_pago": "cancelado",
        "fecha_creacion": (date.today() - timedelta(days=6)).isoformat(),
        "fecha_entrega": None,
        "fecha_pago": None,
        "fecha_vencimiento_pago": None,
        "notas": "La clienta cambió de decisión.",
        "cancelada": True,
    },
    {
        "id": 2,
        "numero_venta": "1042",
        "cliente_id": 2,
        "producto_id": 1,
        "color": "Rosa pastel",
        "cantidad": 1,
        "precio_unitario": 150,
        "subtotal": 150,
        "total": 150,
        "estado_entrega": "entregado",
        "estado_pago": "pagado",
        "fecha_creacion": (date.today() - timedelta(days=5)).isoformat(),
        "fecha_entrega": (date.today() - timedelta(days=5)).isoformat(),
        "fecha_pago": (date.today() - timedelta(days=5)).isoformat(),
        "fecha_vencimiento_pago": None,
        "notas": "",
        "cancelada": False,
    },
    {
        "id": 3,
        "numero_venta": "1043",
        "cliente_id": 4,
        "producto_id": 4,
        "color": "Blanco",
        "cantidad": 3,
        "precio_unitario": 140,
        "subtotal": 420,
        "total": 420,
        "estado_entrega": "listo",
        "estado_pago": "pendiente",
        "fecha_creacion": (date.today() - timedelta(days=2)).isoformat(),
        "fecha_entrega": None,
        "fecha_pago": None,
        "fecha_vencimiento_pago": (date.today() + timedelta(days=3)).isoformat(),
        "notas": "",
        "cancelada": False,
    },
    {
        "id": 4,
        "numero_venta": "1044",
        "cliente_id": 3,
        "producto_id": 2,
        "color": "Vino",
        "cantidad": 1,
        "precio_unitario": 120,
        "subtotal": 120,
        "total": 120,
        "estado_entrega": "preparacion",
        "estado_pago": "pendiente",
        "fecha_creacion": (date.today() - timedelta(days=1)).isoformat(),
        "fecha_entrega": None,
        "fecha_pago": None,
        "fecha_vencimiento_pago": (date.today() + timedelta(days=4)).isoformat(),
        "notas": "",
        "cancelada": False,
    },
    {
        "id": 5,
        "numero_venta": "1045",
        "cliente_id": 7,
        "producto_id": 4,
        "color": "Azul",
        "cantidad": 1,
        "precio_unitario": 140,
        "subtotal": 140,
        "total": 140,
        "estado_entrega": "pendiente",
        "estado_pago": "pendiente",
        "fecha_creacion": (date.today() - timedelta(days=3)).isoformat(),
        "fecha_entrega": None,
        "fecha_pago": None,
        "fecha_vencimiento_pago": (date.today() + timedelta(days=2)).isoformat(),
        "notas": "",
        "cancelada": False,
    },
    {
        "id": 6,
        "numero_venta": "1046",
        "cliente_id": 1,
        "producto_id": 1,
        "color": "Rosa fuerte",
        "cantidad": 2,
        "precio_unitario": 150,
        "subtotal": 300,
        "total": 300,
        "estado_entrega": "pendiente",
        "estado_pago": "pagado",
        "fecha_creacion": date.today().isoformat(),
        "fecha_entrega": None,
        "fecha_pago": date.today().isoformat(),
        "fecha_vencimiento_pago": None,
        "notas": "Entregar antes del sábado si es posible.",
        "cancelada": False,
    },
    {
        "id": 7,
        "numero_venta": "1047",
        "cliente_id": 6,
        "producto_id": 2,
        "color": "Rojo",
        "cantidad": 2,
        "precio_unitario": 120,
        "subtotal": 240,
        "total": 240,
        "estado_entrega": "entregado",
        "estado_pago": "pendiente",
        "fecha_creacion": (date.today() - timedelta(days=8)).isoformat(),
        "fecha_entrega": (date.today() - timedelta(days=8)).isoformat(),
        "fecha_pago": None,
        "fecha_vencimiento_pago": (date.today() - timedelta(days=3)).isoformat(),
        "notas": "",
        "cancelada": False,
    },
]

CLIENTES = [
    {"id": 1, "nombre": "Valentina", "apellido": "Ríos", "pedidos": 12, "etiqueta": "Frecuente", "gastado": 3820, "desde": "marzo 2024", "telefono": "0412 555 0101", "fecha_nacimiento": "", "direccion": "", "email": "", "notas": "", "avatar": "/static/images/avatar/5.png"},
    {"id": 2, "nombre": "Camila", "apellido": "Torres", "pedidos": 8, "etiqueta": None, "gastado": 2140, "desde": "junio 2024", "telefono": "0412 555 0102", "fecha_nacimiento": "", "direccion": "", "email": "", "notas": "", "avatar": "/static/images/avatar/12.png"},
    {"id": 3, "nombre": "Sofía", "apellido": "Medina", "pedidos": 3, "etiqueta": None, "gastado": 890, "desde": "enero 2025", "telefono": "0412 555 0103", "fecha_nacimiento": "", "direccion": "", "email": "", "notas": "", "avatar": "/static/images/avatar/19.png"},
    {"id": 4, "nombre": "Martina", "apellido": "López", "pedidos": 15, "etiqueta": "VIP", "gastado": 5460, "desde": "noviembre 2023", "telefono": "0412 555 0104", "fecha_nacimiento": "", "direccion": "", "email": "", "notas": "", "avatar": "/static/images/avatar/27.png"},
    {"id": 5, "nombre": "Emilia", "apellido": "Cruz", "pedidos": 1, "etiqueta": "Nueva", "gastado": 260, "desde": "esta semana", "telefono": "0412 555 0105", "fecha_nacimiento": "", "direccion": "", "email": "", "notas": "", "avatar": "/static/images/avatar/8.png"},
    {"id": 6, "nombre": "Isabella", "apellido": "Nuñez", "pedidos": 6, "etiqueta": None, "gastado": 1510, "desde": "agosto 2024", "telefono": "0412 555 0106", "fecha_nacimiento": "", "direccion": "", "email": "", "notas": "", "avatar": "/static/images/avatar/33.png"},
    {"id": 7, "nombre": "Renata", "apellido": "Paz", "pedidos": 4, "etiqueta": None, "gastado": 1120, "desde": "abril 2024", "telefono": "0412 555 0107", "fecha_nacimiento": "", "direccion": "", "email": "", "notas": "", "avatar": "/static/images/avatar/21.png"},
]

CLIENTES_HISTORIAL = {
    1: [
        {"producto": "Lazo Clásico Rosa", "monto": 350, "fecha": "Hoy, 10:20"},
        {"producto": "Set Pastel x3", "monto": 890, "fecha": "22 jun"},
        {"producto": "Diadema Floral", "monto": 480, "fecha": "10 may"},
    ],
    2: [
        {"producto": "Set Pastel x3", "monto": 890, "fecha": "Hoy, 09:05"},
        {"producto": "Lazo Mini Corazón", "monto": 260, "fecha": "2 jun"},
    ],
    3: [
        {"producto": "Lazo Broche Perla", "monto": 410, "fecha": "Ayer"},
    ],
    4: [
        {"producto": "Diadema + Lazo", "monto": 520, "fecha": "Ayer"},
        {"producto": "Moño Doble Satín", "monto": 390, "fecha": "15 may"},
    ],
    5: [
        {"producto": "Lazo Mini Corazón", "monto": 260, "fecha": "Lun 12"},
    ],
    6: [
        {"producto": "Moño Doble Satín", "monto": 390, "fecha": "Lun 12"},
    ],
}

# Catálogo de productos: Inventario y Mis Lazos leen y escriben
# sobre este mismo registro (stock/costo/precio son del producto,
# no de una lista aparte).
PRODUCTOS = [
    {
        "id": 1,
        "nombre": "Lazo Doble Con Cola",
        "imagen": "/static/images/producto/dobleconcola.png",
        "stock": 18,
        "costo_produccion": 80,
        "precio_publico": 150,
    },
    {
        "id": 2,
        "nombre": "Lazo Con Cola",
        "imagen": "/static/images/producto/sencilloconcola.png",
        "stock": 4,
        "costo_produccion": 60,
        "precio_publico": 120,
    },
    {
        "id": 3,
        "nombre": "Lazo Sencillo",
        "imagen": "/static/images/producto/sencillo.png",
        "stock": 0,
        "costo_produccion": 40,
        "precio_publico": 90,
    },
    {
        "id": 4,
        "nombre": "Lazo Sencillo Doble",
        "imagen": "/static/images/producto/parsencillo.png",
        "stock": 9,
        "costo_produccion": 70,
        "precio_publico": 140,
    },
]

PRODUCTOS_VENTAS_RECIENTES = {
    1: [{"cliente": "Valentina Ríos", "fecha": "Hoy, 10:20"}],
    2: [{"cliente": "Camila Torres", "fecha": "Ayer"}],
    3: [],
    4: [{"cliente": "Martina López", "fecha": "15 may"}],
}

# Colores de producto disponibles para un pedido (atributo del
# lazo pedido, no de la interfaz — por eso viven acá y no como
# variables CSS de marca).
COLORES_DISPONIBLES = [
    {"nombre": "Rosa pastel", "hex": "#f9c9dd"},
    {"nombre": "Rosa fuerte", "hex": "#f55387"},
    {"nombre": "Vino", "hex": "#861742"},
    {"nombre": "Rojo", "hex": "#e63946"},
    {"nombre": "Lila", "hex": "#c9a6e0"},
    {"nombre": "Blanco", "hex": "#ffffff"},
    {"nombre": "Azul", "hex": "#a8d8f0"},
    {"nombre": "Amarillo", "hex": "#ffc94e"},
]

RESUMEN_SEMANA = [
    {"dia": "Lun", "monto": 1240},
    {"dia": "Mar", "monto": 1860},
    {"dia": "Mié", "monto": 980},
    {"dia": "Jue", "monto": 2110},
    {"dia": "Vie", "monto": 1650},
    {"dia": "Sáb", "monto": 2960},
    {"dia": "Hoy", "monto": 4350},
]

AJUSTES = [
    {"titulo": "Mi negocio", "subtitulo": "Datos de Nudo Rosa", "icono": "🏬"},
    {"titulo": "Notificaciones", "subtitulo": "Pedidos, cobros y recordatorios", "icono": "🔔"},
    {"titulo": "Métodos de cobro", "subtitulo": "Transferencia, efectivo", "icono": "💳"},
    {"titulo": "Ayuda y soporte", "subtitulo": "¿Necesitás una mano?", "icono": "💬"},
]


def get_cliente(cliente_id: int):
    return next((c for c in CLIENTES if c["id"] == cliente_id), None)


def crear_cliente(
    nombre: str,
    apellido: str,
    telefono: str,
    fecha_nacimiento: str = "",
    direccion: str = "",
    email: str = "",
    notas: str = "",
    avatar: str = "",
):
    nuevo_id = max((c["id"] for c in CLIENTES), default=0) + 1

    cliente = {
        "id": nuevo_id,
        "nombre": nombre,
        "apellido": apellido,
        "pedidos": 0,
        "etiqueta": "Nueva",
        "gastado": 0,
        "desde": "esta semana",
        "telefono": telefono,
        "fecha_nacimiento": fecha_nacimiento,
        "direccion": direccion,
        "email": email,
        "notas": notas,
        "avatar": avatar,
    }

    CLIENTES.append(cliente)
    return cliente


def actualizar_cliente(
    cliente_id: int,
    nombre: str,
    apellido: str,
    telefono: str,
    fecha_nacimiento: str = "",
    direccion: str = "",
    email: str = "",
    notas: str = "",
    avatar: str = "",
):
    cliente = get_cliente(cliente_id)
    if cliente is None:
        return None

    cliente.update({
        "nombre": nombre,
        "apellido": apellido,
        "telefono": telefono,
        "fecha_nacimiento": fecha_nacimiento,
        "direccion": direccion,
        "email": email,
        "notas": notas,
        "avatar": avatar,
    })
    return cliente


def eliminar_cliente(cliente_id: int):
    cliente = get_cliente(cliente_id)
    if cliente is not None:
        CLIENTES.remove(cliente)
    return cliente


def get_producto(producto_id: int):
    return next((p for p in PRODUCTOS if p["id"] == producto_id), None)


def crear_producto(
    nombre: str,
    costo_produccion: int,
    precio_publico: int,
    stock_inicial: int,
    imagen: str = "",
):
    nuevo_id = max((p["id"] for p in PRODUCTOS), default=0) + 1

    producto = {
        "id": nuevo_id,
        "nombre": nombre,
        "imagen": imagen,
        "stock": stock_inicial,
        "costo_produccion": costo_produccion,
        "precio_publico": precio_publico,
    }

    PRODUCTOS.append(producto)
    return producto


def ajustar_producto(
    producto_id: int,
    cantidad_agregar: int,
    costo_produccion: int,
    precio_publico: int,
):
    producto = get_producto(producto_id)
    if producto is None:
        return None

    producto["stock"] += cantidad_agregar
    producto["costo_produccion"] = costo_produccion
    producto["precio_publico"] = precio_publico
    return producto


def actualizar_producto(
    producto_id: int,
    nombre: str,
    costo_produccion: int,
    precio_publico: int,
    stock: int,
    imagen: str = "",
):
    producto = get_producto(producto_id)
    if producto is None:
        return None

    producto["nombre"] = nombre
    producto["costo_produccion"] = costo_produccion
    producto["precio_publico"] = precio_publico
    producto["stock"] = stock

    if imagen:
        producto["imagen"] = imagen

    return producto


def eliminar_producto(producto_id: int):
    producto = get_producto(producto_id)
    if producto is not None:
        PRODUCTOS.remove(producto)
    return producto


def get_venta(venta_id: int):
    return next((v for v in VENTAS if v["id"] == venta_id), None)


def _siguiente_numero_venta() -> str:
    numeros = [int(v["numero_venta"]) for v in VENTAS if v["numero_venta"].isdigit()]
    return str(max(numeros, default=1040) + 1)


def crear_venta(
    cliente_id: int,
    producto_id: int,
    color: str,
    cantidad: int,
    entrega_ahora: bool,
    pago_ahora: bool,
    notas: str = "",
    fecha_vencimiento_pago: str | None = None,
):
    producto = get_producto(producto_id)
    if producto is None or cantidad < 1 or producto["stock"] < cantidad:
        return None

    producto["stock"] -= cantidad

    hoy = date.today()
    nuevo_id = max((v["id"] for v in VENTAS), default=0) + 1

    fecha_entrega = hoy.isoformat() if entrega_ahora else None
    fecha_pago = hoy.isoformat() if pago_ahora else None

    if pago_ahora:
        fecha_vencimiento_pago = None
    elif not fecha_vencimiento_pago:
        # Si ya se entregó, el vencimiento se cuenta desde la
        # entrega real; si no, se usa fecha_creacion como estimado
        # (queda listo para reemplazarse por una fecha de entrega
        # planeada cuando el flujo la tenga). La clienta puede
        # editar esta fecha sugerida antes de guardar la venta.
        base = date.fromisoformat(fecha_entrega) if fecha_entrega else hoy
        fecha_vencimiento_pago = (base + timedelta(days=5)).isoformat()

    venta = {
        "id": nuevo_id,
        "numero_venta": _siguiente_numero_venta(),
        "cliente_id": cliente_id,
        "producto_id": producto_id,
        "color": color,
        "cantidad": cantidad,
        "precio_unitario": producto["precio_publico"],
        "subtotal": producto["precio_publico"] * cantidad,
        "total": producto["precio_publico"] * cantidad,
        "estado_entrega": "entregado" if entrega_ahora else "pendiente",
        "estado_pago": "pagado" if pago_ahora else "pendiente",
        "fecha_creacion": hoy.isoformat(),
        "fecha_entrega": fecha_entrega,
        "fecha_pago": fecha_pago,
        "fecha_vencimiento_pago": fecha_vencimiento_pago,
        "notas": notas,
        "cancelada": False,
    }

    VENTAS.append(venta)
    return venta


def marcar_entrega(venta_id: int, nuevo_estado: str):
    venta = get_venta(venta_id)
    if venta is None:
        return None

    venta["estado_entrega"] = nuevo_estado

    if nuevo_estado == "entregado":
        venta["fecha_entrega"] = date.today().isoformat()

        # El vencimiento estimado desde fecha_creacion se recalcula
        # ahora que ya existe una fecha_entrega real.
        if venta["estado_pago"] == "pendiente":
            venta["fecha_vencimiento_pago"] = (date.today() + timedelta(days=5)).isoformat()

    return venta


def marcar_pago(venta_id: int):
    venta = get_venta(venta_id)
    if venta is None:
        return None

    venta["estado_pago"] = "pagado"
    venta["fecha_pago"] = date.today().isoformat()
    venta["fecha_vencimiento_pago"] = None
    return venta


def editar_venta(venta_id: int, color: str, cantidad: int, notas: str = ""):
    venta = get_venta(venta_id)
    if venta is None:
        return None

    producto = get_producto(venta["producto_id"])
    if producto is None:
        return None

    diferencia = cantidad - venta["cantidad"]
    if diferencia > 0 and producto["stock"] < diferencia:
        return None

    producto["stock"] -= diferencia
    venta["color"] = color
    venta["cantidad"] = cantidad
    venta["precio_unitario"] = producto["precio_publico"]
    venta["subtotal"] = producto["precio_publico"] * cantidad
    venta["total"] = venta["subtotal"]
    venta["notas"] = notas
    return venta


def cancelar_venta(venta_id: int):
    venta = get_venta(venta_id)
    if venta is None or venta["cancelada"]:
        return venta

    producto = get_producto(venta["producto_id"])
    if producto is not None:
        producto["stock"] += venta["cantidad"]

    venta["cancelada"] = True
    venta["estado_entrega"] = "cancelado"
    venta["estado_pago"] = "cancelado"
    return venta


# =========================================================
# SEGURIDAD (usuario administrador)
# =========================================================
# A diferencia del resto de este módulo (que se reinicia con datos
# de muestra en cada arranque), las credenciales SÍ deben sobrevivir
# a un reinicio — por eso viven en un archivo aparte (seguridad.json)
# en vez de solo en memoria. La contraseña nunca se guarda en texto
# plano: se guarda un hash PBKDF2 + su salt. Hoy solo existe un
# administrador; el archivo ya queda en forma de diccionario (no de
# valores sueltos) para poder pasar a una lista de usuarios más
# adelante sin cambiar el formato en disco.

RUTA_SEGURIDAD = BASE_DIR / "seguridad.json"

USUARIO_ADMIN_POR_DEFECTO = "admin"
PASSWORD_ADMIN_POR_DEFECTO = "Ivanna**0102"
ITERACIONES_HASH = 200_000


def _hashear_password(password: str, salt_hex: str | None = None) -> tuple[str, str]:
    salt_hex = salt_hex or secrets.token_hex(16)
    hash_ = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), ITERACIONES_HASH
    ).hex()
    return hash_, salt_hex


def _guardar_seguridad(config: dict) -> None:
    RUTA_SEGURIDAD.write_text(
        json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _cargar_seguridad() -> dict:
    if RUTA_SEGURIDAD.exists():
        return json.loads(RUTA_SEGURIDAD.read_text(encoding="utf-8"))

    password_hash, salt = _hashear_password(PASSWORD_ADMIN_POR_DEFECTO)
    config = {
        "nombre_administrador": "Ivanna",
        "usuario": USUARIO_ADMIN_POR_DEFECTO,
        "password_hash": password_hash,
        "password_salt": salt,
    }
    _guardar_seguridad(config)
    return config


CONFIGURACION_SEGURIDAD = _cargar_seguridad()


def verificar_credenciales(usuario: str, password: str) -> bool:
    if usuario != CONFIGURACION_SEGURIDAD["usuario"]:
        return False

    hash_calculado, _ = _hashear_password(password, CONFIGURACION_SEGURIDAD["password_salt"])
    return hmac.compare_digest(hash_calculado, CONFIGURACION_SEGURIDAD["password_hash"])


def actualizar_seguridad(nombre_administrador: str, usuario: str, password: str = "") -> None:
    CONFIGURACION_SEGURIDAD["nombre_administrador"] = nombre_administrador
    CONFIGURACION_SEGURIDAD["usuario"] = usuario

    if password:
        password_hash, salt = _hashear_password(password)
        CONFIGURACION_SEGURIDAD["password_hash"] = password_hash
        CONFIGURACION_SEGURIDAD["password_salt"] = salt

    _guardar_seguridad(CONFIGURACION_SEGURIDAD)
