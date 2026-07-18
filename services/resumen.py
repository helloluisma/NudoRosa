"""
Resumen del día / de la semana para Inicio y Resumen — todo
calculado a partir de pedidos reales, nada de valores de muestra.
"""

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import Clienta, EstadoEntrega, EstadoPago, Pedido, Producto

DIAS_ABREV = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


def resumen_dia(db: Session, limite_poco_stock: int) -> dict:
    hoy = date.today()

    ventas_hoy = db.execute(
        select(func.count(Pedido.id), func.coalesce(func.sum(Pedido.total), 0), func.coalesce(func.sum(Pedido.ganancia_total), 0))
        .where(
            Pedido.estado_entrega == EstadoEntrega.ENTREGADO,
            Pedido.estado_pago == EstadoPago.PAGADO,
            Pedido.fecha_creacion == hoy,
        )
    ).one()
    ventas_count, ingresos, ganancia = ventas_hoy

    pedidos_activos = db.scalar(
        select(func.count(Pedido.id)).where(
            Pedido.estado_entrega.notin_([EstadoEntrega.ENTREGADO, EstadoEntrega.CANCELADO])
        )
    ) or 0

    cobros_pendientes = db.scalar(
        select(func.count(Pedido.id)).where(
            Pedido.estado_pago == EstadoPago.PENDIENTE,
            Pedido.estado_entrega != EstadoEntrega.CANCELADO,
        )
    ) or 0

    cobros_vencidos = db.scalar(
        select(func.count(Pedido.id)).where(
            Pedido.estado_pago == EstadoPago.PENDIENTE,
            Pedido.estado_entrega != EstadoEntrega.CANCELADO,
            Pedido.fecha_vencimiento_pago < hoy,
        )
    ) or 0

    productos_poco_stock = db.scalar(
        select(func.count(Producto.id)).where(
            Producto.activo.is_(True),
            Producto.stock_actual > 0,
            Producto.stock_actual <= limite_poco_stock,
        )
    ) or 0

    productos_agotados = db.scalar(
        select(func.count(Producto.id)).where(Producto.activo.is_(True), Producto.stock_actual == 0)
    ) or 0

    clientas_count = db.scalar(
        select(func.count(Clienta.id)).where(Clienta.activa.is_(True))
    ) or 0

    return {
        "ventas_completadas_hoy": ventas_count,
        "ingresos_hoy": ingresos,
        "ganancia_hoy": ganancia,
        "pedidos_activos": pedidos_activos,
        "cobros_pendientes": cobros_pendientes,
        "cobros_vencidos": cobros_vencidos,
        "productos_poco_stock": productos_poco_stock,
        "productos_agotados": productos_agotados,
        "clientas_count": clientas_count,
    }


def resumen_semana(db: Session) -> list[dict]:
    hoy = date.today()
    inicio = hoy - timedelta(days=6)

    filas = db.execute(
        select(Pedido.fecha_creacion, func.coalesce(func.sum(Pedido.total), 0))
        .where(
            Pedido.estado_entrega == EstadoEntrega.ENTREGADO,
            Pedido.estado_pago == EstadoPago.PAGADO,
            Pedido.fecha_creacion >= inicio,
            Pedido.fecha_creacion <= hoy,
        )
        .group_by(Pedido.fecha_creacion)
    ).all()

    totales_por_dia = {fecha: monto for fecha, monto in filas}

    semana = []
    for offset in range(7):
        dia = inicio + timedelta(days=offset)
        etiqueta = "Hoy" if dia == hoy else DIAS_ABREV[dia.weekday()]
        semana.append({"dia": etiqueta, "monto": totales_por_dia.get(dia, 0)})

    return semana
