"""
Pedidos es la operación principal del negocio. Pedidos activos,
Cobros pendientes y Ventas completadas son CONSULTAS sobre esta
misma tabla — nunca se copian a otra tabla (ver CLAUDE.md).

Este servicio trabaja en Enum/mayúsculas (models.EstadoEntrega /
EstadoPago) y con objetos ORM. La traducción a los tokens en
minúscula que ya esperan las plantillas y app.js vive en main.py
(`_venta_enriquecida`), como capa de presentación — no acá.
"""

from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from models import (
    Clienta,
    Color,
    ContadorPedidos,
    EstadoEntrega,
    EstadoPago,
    Pago,
    Pedido,
    PedidoItem,
    Producto,
    SIGUIENTE_ESTADO_ENTREGA,
    ESTADOS_ENTREGA_EDITABLES,
    TipoMovimientoInventario,
)
from services import ErrorNegocio, inventario


def _con_relaciones(query):
    return query.options(
        selectinload(Pedido.clienta),
        selectinload(Pedido.items).selectinload(PedidoItem.producto),
        selectinload(Pedido.items).selectinload(PedidoItem.color),
    )


def get_pedido(db: Session, pedido_id: int) -> Pedido | None:
    return db.get(
        Pedido,
        pedido_id,
        options=[
            selectinload(Pedido.clienta),
            selectinload(Pedido.items).selectinload(PedidoItem.producto),
            selectinload(Pedido.items).selectinload(PedidoItem.color),
        ],
    )


def listar_pedidos_activos(db: Session) -> list[Pedido]:
    query = _con_relaciones(
        select(Pedido).where(
            Pedido.estado_entrega.notin_([EstadoEntrega.ENTREGADO, EstadoEntrega.CANCELADO])
        )
    )
    pedidos = list(db.scalars(query))
    pedidos.sort(key=lambda p: p.fecha_creacion, reverse=True)
    pedidos.sort(key=lambda p: list(EstadoEntrega).index(p.estado_entrega))
    return pedidos


def listar_cobros_pendientes(db: Session) -> list[Pedido]:
    query = _con_relaciones(
        select(Pedido).where(
            Pedido.estado_pago == EstadoPago.PENDIENTE,
            Pedido.estado_entrega != EstadoEntrega.CANCELADO,
        )
    )
    pedidos = list(db.scalars(query))
    pedidos.sort(key=lambda p: p.fecha_vencimiento_pago or date.max)
    return pedidos


def listar_ventas_completadas(db: Session) -> list[Pedido]:
    query = _con_relaciones(
        select(Pedido).where(
            Pedido.estado_entrega == EstadoEntrega.ENTREGADO,
            Pedido.estado_pago == EstadoPago.PAGADO,
        )
    )
    pedidos = list(db.scalars(query))
    pedidos.sort(key=lambda p: p.fecha_creacion, reverse=True)
    return pedidos


def listar_todos(db: Session) -> list[Pedido]:
    return list(_con_relaciones(select(Pedido)).order_by(Pedido.id))


def listar_ventas_recientes_por_producto(db: Session, producto_id: int, limite: int = 5) -> list[dict]:
    filas = db.execute(
        select(Pedido, Clienta)
        .join(PedidoItem, PedidoItem.pedido_id == Pedido.id)
        .join(Clienta, Clienta.id == Pedido.clienta_id)
        .where(PedidoItem.producto_id == producto_id, Pedido.estado_entrega != EstadoEntrega.CANCELADO)
        .order_by(Pedido.fecha_creacion.desc())
        .limit(limite)
    ).all()

    hoy = date.today()
    recientes = []

    for pedido, clienta in filas:
        fecha_texto = "Hoy" if pedido.fecha_creacion == hoy else f"{pedido.fecha_creacion.day:02d}/{pedido.fecha_creacion.month:02d}"
        recientes.append({"cliente": f"{clienta.nombres} {clienta.apellidos}", "fecha": fecha_texto})

    return recientes


def generar_numero_pedido(db: Session) -> str:
    """Incrementa el contador dentro de la MISMA transacción de
    creación del pedido — evita duplicados por contar filas."""

    contador = db.get(ContadorPedidos, 1)
    if contador is None:
        contador = ContadorPedidos(id=1, siguiente_valor=1)
        db.add(contador)
        db.flush()

    numero = contador.siguiente_valor
    contador.siguiente_valor = numero + 1
    return f"PED-{numero:06d}"


def crear_pedido(
    db: Session,
    clienta_id: int,
    producto_id: int,
    color_nombre: str,
    cantidad: int,
    entrega_ahora: bool,
    pago_ahora: bool,
    notas: str = "",
    fecha_vencimiento_pago: date | None = None,
    dias_credito: int = 5,
) -> Pedido:
    clienta = db.get(Clienta, clienta_id)
    if clienta is None or not clienta.activa:
        raise ErrorNegocio("Elegí una clienta para la venta.")

    producto = db.get(Producto, producto_id)
    if producto is None or not producto.activo:
        raise ErrorNegocio("Elegí un producto para la venta.")

    if cantidad < 1:
        raise ErrorNegocio("La cantidad debe ser al menos 1.")

    if producto.stock_actual < cantidad:
        raise ErrorNegocio(f"Solo quedan {producto.stock_actual} en stock de {producto.nombre}.")

    color = db.scalar(select(Color).where(Color.nombre == color_nombre))

    hoy = date.today()
    subtotal = producto.precio_publico * cantidad
    costo_subtotal = producto.costo_produccion * cantidad

    fecha_entrega = hoy if entrega_ahora else None
    fecha_pago = hoy if pago_ahora else None

    if pago_ahora:
        vencimiento = None
    elif fecha_vencimiento_pago:
        vencimiento = fecha_vencimiento_pago
    else:
        # Igual que antes: si ya se entregó, el vencimiento se cuenta
        # desde la entrega real; si no, se estima desde la creación
        # (se recalcula al marcar Entregado).
        base = fecha_entrega or hoy
        vencimiento = base + timedelta(days=dias_credito)

    pedido = Pedido(
        numero_pedido=generar_numero_pedido(db),
        clienta_id=clienta_id,
        estado_entrega=EstadoEntrega.ENTREGADO if entrega_ahora else EstadoEntrega.PENDIENTE,
        estado_pago=EstadoPago.PAGADO if pago_ahora else EstadoPago.PENDIENTE,
        fecha_creacion=hoy,
        fecha_entrega=fecha_entrega,
        fecha_pago=fecha_pago,
        fecha_vencimiento_pago=vencimiento,
        subtotal=subtotal,
        total=subtotal,
        costo_total=costo_subtotal,
        ganancia_total=subtotal - costo_subtotal,
        notas=notas or None,
    )
    db.add(pedido)
    db.flush()

    item = PedidoItem(
        pedido_id=pedido.id,
        producto_id=producto_id,
        color_id=color.id if color else None,
        cantidad=cantidad,
        precio_unitario=producto.precio_publico,
        costo_unitario=producto.costo_produccion,
        subtotal=subtotal,
        costo_subtotal=costo_subtotal,
    )
    db.add(item)

    inventario.registrar_movimiento(
        db,
        producto,
        TipoMovimientoInventario.SALIDA_PEDIDO,
        -cantidad,
        motivo=f"Venta {pedido.numero_pedido}",
        pedido_id=pedido.id,
        costo_unitario=producto.costo_produccion,
    )

    if pago_ahora:
        db.add(Pago(pedido_id=pedido.id, monto=subtotal, fecha_pago=hoy, metodo_pago="efectivo"))

    db.commit()
    return get_pedido(db, pedido.id)


def marcar_entrega(db: Session, pedido_id: int, nuevo_estado: EstadoEntrega, dias_credito: int = 5) -> Pedido:
    pedido = get_pedido(db, pedido_id)
    if pedido is None:
        raise ErrorNegocio("Venta no encontrada.")

    if pedido.estado_entrega == EstadoEntrega.CANCELADO:
        raise ErrorNegocio("Esta venta está cancelada.")

    if SIGUIENTE_ESTADO_ENTREGA.get(pedido.estado_entrega) != nuevo_estado:
        raise ErrorNegocio("Ese cambio de estado no es válido.")

    pedido.estado_entrega = nuevo_estado

    if nuevo_estado == EstadoEntrega.ENTREGADO:
        hoy = date.today()
        pedido.fecha_entrega = hoy

        if pedido.estado_pago == EstadoPago.PENDIENTE:
            pedido.fecha_vencimiento_pago = hoy + timedelta(days=dias_credito)

    db.commit()
    db.refresh(pedido)
    return pedido


def marcar_pago(db: Session, pedido_id: int) -> Pedido:
    pedido = get_pedido(db, pedido_id)
    if pedido is None:
        raise ErrorNegocio("Venta no encontrada.")

    if pedido.estado_pago != EstadoPago.PENDIENTE:
        raise ErrorNegocio("Esta venta ya no admite ese cambio.")

    hoy = date.today()
    db.add(Pago(pedido_id=pedido.id, monto=pedido.total, fecha_pago=hoy, metodo_pago="efectivo"))

    pedido.estado_pago = EstadoPago.PAGADO
    pedido.fecha_pago = hoy
    pedido.fecha_vencimiento_pago = None

    db.commit()
    db.refresh(pedido)
    return pedido


def editar_pedido(db: Session, pedido_id: int, color_nombre: str, cantidad: int, notas: str = "") -> Pedido:
    pedido = get_pedido(db, pedido_id)
    if pedido is None:
        raise ErrorNegocio("Venta no encontrada.")

    if pedido.estado_entrega not in ESTADOS_ENTREGA_EDITABLES or pedido.estado_entrega == EstadoEntrega.CANCELADO:
        raise ErrorNegocio("Esta venta ya no se puede editar.")

    if cantidad < 1:
        raise ErrorNegocio("La cantidad debe ser al menos 1.")

    item = pedido.items[0]
    producto = item.producto
    color = db.scalar(select(Color).where(Color.nombre == color_nombre))

    diferencia = cantidad - item.cantidad
    disponible = producto.stock_actual + item.cantidad
    if cantidad > disponible:
        raise ErrorNegocio(f"Solo hay {disponible} disponibles para este producto.")

    if diferencia != 0:
        inventario.registrar_movimiento(
            db,
            producto,
            TipoMovimientoInventario.SALIDA_PEDIDO if diferencia > 0 else TipoMovimientoInventario.DEVOLUCION_CANCELACION,
            -diferencia,
            motivo=f"Edición de {pedido.numero_pedido}",
            pedido_id=pedido.id,
        )

    item.color_id = color.id if color else None
    item.cantidad = cantidad
    item.precio_unitario = producto.precio_publico
    item.costo_unitario = producto.costo_produccion
    item.subtotal = producto.precio_publico * cantidad
    item.costo_subtotal = producto.costo_produccion * cantidad

    pedido.subtotal = item.subtotal
    pedido.total = item.subtotal
    pedido.costo_total = item.costo_subtotal
    pedido.ganancia_total = item.subtotal - item.costo_subtotal
    pedido.notas = notas or None

    db.commit()
    db.refresh(pedido)
    return pedido


def cancelar_pedido(db: Session, pedido_id: int) -> Pedido:
    pedido = get_pedido(db, pedido_id)
    if pedido is None:
        raise ErrorNegocio("Venta no encontrada.")

    if pedido.estado_entrega == EstadoEntrega.CANCELADO:
        # Idempotente: cancelar dos veces no devuelve stock dos veces.
        return pedido

    for item in pedido.items:
        inventario.registrar_movimiento(
            db,
            item.producto,
            TipoMovimientoInventario.DEVOLUCION_CANCELACION,
            item.cantidad,
            motivo=f"Cancelación de {pedido.numero_pedido}",
            pedido_id=pedido.id,
        )

    pedido.estado_entrega = EstadoEntrega.CANCELADO
    pedido.estado_pago = EstadoPago.CANCELADO
    pedido.cancelado_en = datetime.utcnow()

    db.commit()
    db.refresh(pedido)
    return pedido
