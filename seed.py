"""
Carga inicial / migración de los datos de muestra de data.py hacia
la base de datos real.

Idempotente: se puede correr varias veces sin duplicar nada — cada
sección se salta si la tabla correspondiente ya tiene filas.

Uso:
    ./.venv/Scripts/python.exe seed.py
"""

from sqlalchemy import func, select

import data
from database import SessionLocal, engine
from models import (
    Base,
    Clienta,
    Color,
    EstadoEntrega,
    EstadoPago,
    Pago,
    Pedido,
    PedidoItem,
    Producto,
    ProductoColor,
    TipoMovimientoInventario,
)
from services import seguridad
from services.inventario import registrar_movimiento
from services.pedidos import generar_numero_pedido

MAPA_ENTREGA_SEED = {
    "pendiente": EstadoEntrega.PENDIENTE,
    "preparacion": EstadoEntrega.EN_PREPARACION,
    "listo": EstadoEntrega.LISTO_PARA_ENTREGAR,
    "entregado": EstadoEntrega.ENTREGADO,
    "cancelado": EstadoEntrega.CANCELADO,
}

MAPA_PAGO_SEED = {
    "pendiente": EstadoPago.PENDIENTE,
    "pagado": EstadoPago.PAGADO,
    "cancelado": EstadoPago.CANCELADO,
}


def _tabla_vacia(db, modelo) -> bool:
    return (db.scalar(select(func.count()).select_from(modelo)) or 0) == 0


def seed_colores(db) -> None:
    if not _tabla_vacia(db, Color):
        return

    for orden, c in enumerate(data.COLORES_DISPONIBLES):
        db.add(Color(nombre=c["nombre"], codigo_hex=c["hex"], orden=orden))

    db.commit()
    print(f"  colores: {len(data.COLORES_DISPONIBLES)} creados")


def seed_productos(db) -> None:
    if not _tabla_vacia(db, Producto):
        return

    for p in data.PRODUCTOS:
        producto = Producto(
            id=p["id"],
            nombre=p["nombre"],
            imagen=p["imagen"] or None,
            costo_produccion=p["costo_produccion"],
            precio_publico=p["precio_publico"],
            stock_actual=0,
        )
        db.add(producto)
        db.flush()

        # Movimiento de auditoría: punto de partida de la demo, no
        # se reconstruye la historia de ventas previas a la migración.
        registrar_movimiento(
            db,
            producto,
            TipoMovimientoInventario.STOCK_INICIAL,
            p["stock"],
            motivo="Carga inicial de datos de muestra",
        )

    colores = list(db.scalars(select(Color)))
    productos = list(db.scalars(select(Producto)))
    for producto in productos:
        for color in colores:
            db.add(ProductoColor(producto_id=producto.id, color_id=color.id))

    db.commit()
    print(f"  productos: {len(data.PRODUCTOS)} creados (+ {len(productos) * len(colores)} producto_colores)")


def seed_clientas(db) -> None:
    if not _tabla_vacia(db, Clienta):
        return

    for c in data.CLIENTES:
        db.add(
            Clienta(
                id=c["id"],
                nombres=c["nombre"],
                apellidos=c["apellido"],
                telefono=c["telefono"] or None,
                email=c["email"] or None,
                direccion=c["direccion"] or None,
                fecha_nacimiento=None,
                avatar=c["avatar"] or None,
                notas=c["notas"] or None,
            )
        )

    db.commit()
    print(f"  clientas: {len(data.CLIENTES)} creadas")


def seed_pedidos(db) -> None:
    if not _tabla_vacia(db, Pedido):
        return

    colores_por_nombre = {c.nombre: c for c in db.scalars(select(Color))}

    for v in data.VENTAS:
        producto = db.get(Producto, v["producto_id"])
        color = colores_por_nombre.get(v["color"])

        pedido = Pedido(
            numero_pedido=generar_numero_pedido(db),
            clienta_id=v["cliente_id"],
            estado_entrega=MAPA_ENTREGA_SEED[v["estado_entrega"]],
            estado_pago=MAPA_PAGO_SEED[v["estado_pago"]],
            fecha_creacion=data.date.fromisoformat(v["fecha_creacion"]),
            fecha_entrega=data.date.fromisoformat(v["fecha_entrega"]) if v["fecha_entrega"] else None,
            fecha_pago=data.date.fromisoformat(v["fecha_pago"]) if v["fecha_pago"] else None,
            fecha_vencimiento_pago=(
                data.date.fromisoformat(v["fecha_vencimiento_pago"]) if v["fecha_vencimiento_pago"] else None
            ),
            subtotal=v["subtotal"],
            total=v["total"],
            costo_total=producto.costo_produccion * v["cantidad"],
            ganancia_total=v["subtotal"] - producto.costo_produccion * v["cantidad"],
            notas=v["notas"] or None,
            cancelado_en=None,
        )
        db.add(pedido)
        db.flush()

        db.add(
            PedidoItem(
                pedido_id=pedido.id,
                producto_id=v["producto_id"],
                color_id=color.id if color else None,
                cantidad=v["cantidad"],
                precio_unitario=v["precio_unitario"],
                costo_unitario=producto.costo_produccion,
                subtotal=v["subtotal"],
                costo_subtotal=producto.costo_produccion * v["cantidad"],
            )
        )

        if v["estado_pago"] == "pagado":
            db.add(
                Pago(
                    pedido_id=pedido.id,
                    monto=v["total"],
                    metodo_pago="efectivo",
                    fecha_pago=data.date.fromisoformat(v["fecha_pago"]) if v["fecha_pago"] else data.date.today(),
                )
            )

    db.commit()
    print(f"  pedidos: {len(data.VENTAS)} creados (migrados desde data.VENTAS)")


def main() -> None:
    Base.metadata.create_all(bind=engine)  # red de seguridad; Alembic ya crea las tablas

    db = SessionLocal()
    try:
        print("Sembrando datos iniciales (idempotente)...")
        seguridad.asegurar_datos_iniciales(db)
        seed_colores(db)
        seed_productos(db)
        seed_clientas(db)
        seed_pedidos(db)
        print("Listo.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
