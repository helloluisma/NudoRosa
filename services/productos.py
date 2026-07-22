"""
Productos es la ÚNICA fuente de verdad para Mis Lazos, Inventario,
Pedidos y Ventas — ninguna pantalla tiene su propia lista.
"""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Producto, TipoMovimientoInventario
from services import ErrorNegocio, inventario, materiales


def _aplicar_datos_materiales(
    db: Session,
    producto: Producto,
    *,
    lazos_por_metro_tela: int | None,
    lazos_por_barra_silicon: int | None,
    cantidad_ganchos: int | None,
    usa_hilo: bool,
    minutos_elaboracion: int | None,
) -> None:
    """Guarda las respuestas de "Mis materiales" en el producto y
    recalcula costo_produccion a partir de ellas. minutos_elaboracion
    en None significa "seguí con el costo manual de siempre" — no
    toca ninguno de estos campos ni el costo (compatibilidad con
    productos creados antes de esta funcionalidad)."""

    if minutos_elaboracion is None:
        return

    producto.lazos_por_metro_tela = lazos_por_metro_tela
    producto.lazos_por_barra_silicon = lazos_por_barra_silicon
    producto.cantidad_ganchos = cantidad_ganchos
    producto.usa_hilo = usa_hilo
    producto.minutos_elaboracion = minutos_elaboracion

    materiales.recalcular_costo_producto(db, producto)


def get_producto(db: Session, producto_id: int) -> Producto | None:
    return db.get(Producto, producto_id)


def listar_productos_activos(db: Session) -> list[Producto]:
    return list(
        db.scalars(select(Producto).where(Producto.activo.is_(True)).order_by(Producto.nombre))
    )


def crear_producto(
    db: Session,
    nombre: str,
    precio_publico: int,
    stock_inicial: int,
    imagen: str = "",
    costo_produccion: Decimal | int = Decimal("0"),
    lazos_por_metro_tela: int | None = None,
    lazos_por_barra_silicon: int | None = None,
    cantidad_ganchos: int | None = None,
    usa_hilo: bool = True,
    minutos_elaboracion: int | None = None,
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

    _aplicar_datos_materiales(
        db,
        producto,
        lazos_por_metro_tela=lazos_por_metro_tela,
        lazos_por_barra_silicon=lazos_por_barra_silicon,
        cantidad_ganchos=cantidad_ganchos,
        usa_hilo=usa_hilo,
        minutos_elaboracion=minutos_elaboracion,
    )

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
    costo_produccion: Decimal | int,
    precio_publico: int,
) -> Producto | None:
    producto = get_producto(db, producto_id)
    if producto is None:
        return None

    if costo_produccion < 0 or precio_publico < 0 or cantidad_agregar < 0:
        raise ErrorNegocio("Revisá la cantidad, el costo y el precio ingresados.")

    # Un producto que ya usa "Mis materiales" no admite costo manual
    # acá: se recalcula solo a partir de los precios de materiales
    # vigentes, para no dejar costo_produccion desactualizado ni en
    # contradicción con lo que muestra la pantalla de edición.
    costo_para_movimiento = costo_produccion
    if producto.minutos_elaboracion is not None:
        materiales.recalcular_costo_producto(db, producto)
        costo_para_movimiento = producto.costo_produccion
    else:
        producto.costo_produccion = costo_produccion

    if cantidad_agregar > 0:
        inventario.registrar_movimiento(
            db,
            producto,
            TipoMovimientoInventario.ENTRADA,
            cantidad_agregar,
            motivo="Ajuste de inventario",
            costo_unitario=costo_para_movimiento,
        )

    producto.precio_publico = precio_publico

    db.commit()
    db.refresh(producto)
    return producto


def actualizar_producto(
    db: Session,
    producto_id: int,
    nombre: str,
    precio_publico: int,
    stock: int,
    imagen: str = "",
    costo_produccion: Decimal | int = Decimal("0"),
    lazos_por_metro_tela: int | None = None,
    lazos_por_barra_silicon: int | None = None,
    cantidad_ganchos: int | None = None,
    usa_hilo: bool = True,
    minutos_elaboracion: int | None = None,
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
    producto.precio_publico = precio_publico

    if minutos_elaboracion is None:
        # Producto legacy o que se está pasando a costo manual otra
        # vez: se apaga la calculadora y se usa el costo tal cual.
        producto.lazos_por_metro_tela = None
        producto.lazos_por_barra_silicon = None
        producto.cantidad_ganchos = None
        producto.minutos_elaboracion = None
        producto.costo_produccion = costo_produccion
    else:
        _aplicar_datos_materiales(
            db,
            producto,
            lazos_por_metro_tela=lazos_por_metro_tela,
            lazos_por_barra_silicon=lazos_por_barra_silicon,
            cantidad_ganchos=cantidad_ganchos,
            usa_hilo=usa_hilo,
            minutos_elaboracion=minutos_elaboracion,
        )

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
