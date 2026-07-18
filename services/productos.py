"""
Productos es la ÚNICA fuente de verdad para Mis Lazos, Inventario,
Pedidos y Ventas — ninguna pantalla tiene su propia lista.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Producto, TipoMovimientoInventario
from services import ErrorNegocio, inventario


def get_producto(db: Session, producto_id: int) -> Producto | None:
    return db.get(Producto, producto_id)


def listar_productos_activos(db: Session) -> list[Producto]:
    return list(
        db.scalars(select(Producto).where(Producto.activo.is_(True)).order_by(Producto.nombre))
    )


def crear_producto(
    db: Session,
    nombre: str,
    costo_produccion: int,
    precio_publico: int,
    stock_inicial: int,
    imagen: str = "",
) -> Producto:
    if costo_produccion < 0 or precio_publico < 0 or stock_inicial < 0:
        raise ErrorNegocio("El costo, el precio y el stock no pueden ser negativos.")

    producto = Producto(
        nombre=nombre,
        imagen=imagen or None,
        costo_produccion=costo_produccion,
        precio_publico=precio_publico,
        stock_actual=0,
    )
    db.add(producto)
    db.flush()  # asigna producto.id sin cerrar la transacción

    if stock_inicial > 0:
        inventario.registrar_movimiento(
            db,
            producto,
            TipoMovimientoInventario.STOCK_INICIAL,
            stock_inicial,
            motivo="Alta de producto",
        )

    db.commit()
    db.refresh(producto)
    return producto


def ajustar_producto(
    db: Session,
    producto_id: int,
    cantidad_agregar: int,
    costo_produccion: int,
    precio_publico: int,
) -> Producto | None:
    producto = get_producto(db, producto_id)
    if producto is None:
        return None

    if costo_produccion < 0 or precio_publico < 0 or cantidad_agregar < 0:
        raise ErrorNegocio("Revisá la cantidad, el costo y el precio ingresados.")

    if cantidad_agregar > 0:
        inventario.registrar_movimiento(
            db,
            producto,
            TipoMovimientoInventario.ENTRADA,
            cantidad_agregar,
            motivo="Ajuste de inventario",
            costo_unitario=costo_produccion,
        )

    producto.costo_produccion = costo_produccion
    producto.precio_publico = precio_publico

    db.commit()
    db.refresh(producto)
    return producto


def actualizar_producto(
    db: Session,
    producto_id: int,
    nombre: str,
    costo_produccion: int,
    precio_publico: int,
    stock: int,
    imagen: str = "",
) -> Producto | None:
    producto = get_producto(db, producto_id)
    if producto is None:
        return None

    if costo_produccion < 0 or precio_publico < 0 or stock < 0:
        raise ErrorNegocio("El costo, el precio y el stock no pueden ser negativos.")

    diferencia = stock - producto.stock_actual
    if diferencia != 0:
        inventario.registrar_movimiento(
            db,
            producto,
            TipoMovimientoInventario.CORRECCION,
            diferencia,
            motivo="Edición manual del producto",
        )

    producto.nombre = nombre
    producto.costo_produccion = costo_produccion
    producto.precio_publico = precio_publico

    if imagen:
        producto.imagen = imagen

    db.commit()
    db.refresh(producto)
    return producto


def desactivar_producto(db: Session, producto_id: int) -> Producto | None:
    """Baja lógica: un producto con pedidos históricos nunca se
    borra físicamente."""

    producto = get_producto(db, producto_id)
    if producto is None:
        return None

    producto.activo = False
    db.commit()
    db.refresh(producto)
    return producto
