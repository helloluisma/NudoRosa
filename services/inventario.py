"""
Todo cambio de stock pasa por acá: nunca se escribe
producto.stock_actual directamente desde otro servicio o ruta, para
que ningún movimiento quede sin registrar en el historial.
"""

from sqlalchemy.orm import Session

from models import MovimientoInventario, Producto, TipoMovimientoInventario
from services import ErrorNegocio


def registrar_movimiento(
    db: Session,
    producto: Producto,
    tipo_movimiento: TipoMovimientoInventario,
    cantidad: int,
    motivo: str = "",
    pedido_id: int | None = None,
    costo_unitario: int | None = None,
    usuario_id: int | None = None,
) -> MovimientoInventario:
    """cantidad positiva = entrada, negativa = salida (ver
    models.MovimientoInventario)."""

    stock_anterior = producto.stock_actual
    stock_nuevo = stock_anterior + cantidad

    if stock_nuevo < 0:
        raise ErrorNegocio(f"Solo quedan {stock_anterior} en stock de {producto.nombre}.")

    producto.stock_actual = stock_nuevo

    movimiento = MovimientoInventario(
        producto_id=producto.id,
        pedido_id=pedido_id,
        tipo_movimiento=tipo_movimiento,
        cantidad=cantidad,
        stock_anterior=stock_anterior,
        stock_nuevo=stock_nuevo,
        costo_unitario=costo_unitario,
        motivo=motivo,
        usuario_id=usuario_id,
    )
    db.add(movimiento)
    return movimiento


def estado_producto(stock: int, limite_poco_stock: int) -> dict:
    if stock == 0:
        return {"clave": "agotado", "etiqueta": "Agotado", "pill_class": "pill--due"}

    if stock <= limite_poco_stock:
        return {"clave": "poco", "etiqueta": "Poco stock", "pill_class": "pill--pending"}

    return {"clave": "disponible", "etiqueta": "Disponible", "pill_class": "pill--ok"}
