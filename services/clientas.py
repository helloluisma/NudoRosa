"""
Clientas: la tabla guarda solo datos propios de la clienta.
"pedidos", "gastado", "etiqueta" y "desde" NO se guardan — se
calculan acá a partir de sus pedidos reales, para que nunca queden
desincronizados de la operación real (ver CLAUDE.md).
"""

from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import Clienta, EstadoEntrega, EstadoPago, Pedido, PedidoItem, Producto

MESES_COMPLETOS = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def get_clienta(db: Session, clienta_id: int) -> Clienta | None:
    return db.get(Clienta, clienta_id)


def listar_clientas_activas(db: Session) -> list[Clienta]:
    return list(
        db.scalars(
            select(Clienta).where(Clienta.activa.is_(True)).order_by(Clienta.nombres)
        )
    )


def crear_clienta(
    db: Session,
    nombre: str,
    apellido: str,
    telefono: str = "",
    fecha_nacimiento: str = "",
    direccion: str = "",
    email: str = "",
    notas: str = "",
    avatar: str = "",
) -> Clienta:
    clienta = Clienta(
        nombres=nombre,
        apellidos=apellido,
        telefono=telefono or None,
        fecha_nacimiento=_parsear_fecha(fecha_nacimiento),
        direccion=direccion or None,
        email=email or None,
        notas=notas or None,
        avatar=avatar or None,
    )
    db.add(clienta)
    db.commit()
    db.refresh(clienta)
    return clienta


def actualizar_clienta(
    db: Session,
    clienta_id: int,
    nombre: str,
    apellido: str,
    telefono: str = "",
    fecha_nacimiento: str = "",
    direccion: str = "",
    email: str = "",
    notas: str = "",
    avatar: str = "",
) -> Clienta | None:
    clienta = get_clienta(db, clienta_id)
    if clienta is None:
        return None

    clienta.nombres = nombre
    clienta.apellidos = apellido
    clienta.telefono = telefono or None
    clienta.fecha_nacimiento = _parsear_fecha(fecha_nacimiento)
    clienta.direccion = direccion or None
    clienta.email = email or None
    clienta.notas = notas or None
    clienta.avatar = avatar or None

    db.commit()
    db.refresh(clienta)
    return clienta


def desactivar_clienta(db: Session, clienta_id: int) -> Clienta | None:
    """Baja lógica: una clienta con pedidos históricos nunca se
    borra físicamente."""

    clienta = get_clienta(db, clienta_id)
    if clienta is None:
        return None

    clienta.activa = False
    db.commit()
    db.refresh(clienta)
    return clienta


def _parsear_fecha(valor: str | None) -> date | None:
    if not valor:
        return None
    try:
        return date.fromisoformat(valor)
    except ValueError:
        return None


def contar_pedidos(db: Session, clienta_id: int) -> int:
    return db.scalar(
        select(func.count(Pedido.id)).where(
            Pedido.clienta_id == clienta_id,
            Pedido.estado_entrega != EstadoEntrega.CANCELADO,
        )
    ) or 0


def calcular_gastado(db: Session, clienta_id: int) -> int:
    total = db.scalar(
        select(func.coalesce(func.sum(Pedido.total), 0)).where(
            Pedido.clienta_id == clienta_id,
            Pedido.estado_entrega == EstadoEntrega.ENTREGADO,
            Pedido.estado_pago == EstadoPago.PAGADO,
        )
    )
    return total or 0


def etiqueta_clienta(pedidos_count: int, creada_en: datetime) -> str | None:
    if datetime.utcnow() - creada_en <= timedelta(days=7):
        return "Nueva"
    if pedidos_count >= 10:
        return "VIP"
    if pedidos_count >= 5:
        return "Frecuente"
    return None


def texto_desde(creada_en: datetime) -> str:
    if datetime.utcnow() - creada_en <= timedelta(days=7):
        return "esta semana"
    return f"{MESES_COMPLETOS[creada_en.month - 1]} {creada_en.year}"


def serializar_clienta(db: Session, clienta: Clienta) -> dict:
    pedidos_count = contar_pedidos(db, clienta.id)

    return {
        "id": clienta.id,
        "nombre": clienta.nombres,
        "apellido": clienta.apellidos,
        "telefono": clienta.telefono or "",
        "email": clienta.email or "",
        "direccion": clienta.direccion or "",
        "fecha_nacimiento": clienta.fecha_nacimiento.isoformat() if clienta.fecha_nacimiento else "",
        "avatar": clienta.avatar or "",
        "notas": clienta.notas or "",
        "pedidos": pedidos_count,
        "gastado": calcular_gastado(db, clienta.id),
        "etiqueta": etiqueta_clienta(pedidos_count, clienta.creada_en),
        "desde": texto_desde(clienta.creada_en),
    }


def listar_historial_compras(db: Session, clienta_id: int) -> list[dict]:
    filas = db.execute(
        select(Pedido, PedidoItem, Producto)
        .join(PedidoItem, PedidoItem.pedido_id == Pedido.id)
        .join(Producto, Producto.id == PedidoItem.producto_id)
        .where(Pedido.clienta_id == clienta_id, Pedido.estado_entrega != EstadoEntrega.CANCELADO)
        .order_by(Pedido.fecha_creacion.desc())
    ).all()

    hoy = date.today()
    historial = []

    for pedido, item, producto in filas:
        if pedido.fecha_creacion == hoy:
            fecha_texto = "Hoy"
        else:
            fecha_texto = f"{pedido.fecha_creacion.day} {MESES_COMPLETOS[pedido.fecha_creacion.month - 1][:3]}"

        historial.append({
            "producto": producto.nombre,
            "monto": item.subtotal,
            "fecha": fecha_texto,
        })

    return historial
