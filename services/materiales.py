"""
"Mis materiales": calculadora del costo de elaboración de un lazo.

Todo el cálculo ocurre EN BOLÍVARES (así compra Ivanna la tela, el
silicón, los ganchos y el hilo — ver models.Material) y recién al
final se convierte a dólares con la tasa BCV vigente
(services/tasa_cambio.py), porque precio_publico y ganancia_total del
resto de la app viven en dólares. La conversión nunca se guarda "a
mano": siempre pasa por convertir_bolivares_a_usd, que usa la MISMA
tasa activa que ya usa el resto de la app.

El costo de un producto (Producto.costo_produccion) es un valor
DERIVADO mientras el producto siga con precio pendiente de venta: se
recalcula solo cada vez que cambia un precio de material o los datos
del producto (ver recalcular_costo_producto /
recalcular_productos_con_materiales). Recién se "congela" de verdad
cuando ese costo pasa a un PedidoItem/Pedido al vender (ver
services/pedidos.py) — el mismo patrón que ya usa la tasa BCV con las
ventas (congelar al pagar, recalcular mientras está pendiente).
"""

from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Configuracion, Material, Producto, TIPOS_MATERIAL
from services import ErrorNegocio, tasa_cambio

# Metadata fija de cada material — nombre visible y unidad de compra
# para la pantalla "Mis materiales". No se guarda en la base: es
# presentación pura, igual que MAPA_ENTREGA_A_LEGACY en main.py.
METADATA_MATERIAL = {
    "tela": {"nombre": "Tela", "unidad_compra": "metro", "usa_rendimiento": False},
    "silicon": {"nombre": "Silicón", "unidad_compra": "barra", "usa_rendimiento": False},
    "gancho": {"nombre": "Gancho", "unidad_compra": "paquete", "usa_rendimiento": True},
    "hilo": {"nombre": "Hilo", "unidad_compra": "carrete", "usa_rendimiento": True},
}


def asegurar_materiales_iniciales(db: Session) -> None:
    """Se llama una sola vez al arrancar la app (ver el lifespan en
    main.py). Siembra las 4 filas fijas si no existen todavía —
    precio en 0 (sin configurar), nunca inventa un valor. No pisa
    materiales que ya existan."""

    existentes = {m.tipo for m in db.scalars(select(Material))}
    faltantes = [tipo for tipo in TIPOS_MATERIAL if tipo not in existentes]
    if not faltantes:
        return

    for tipo in faltantes:
        meta = METADATA_MATERIAL[tipo]
        db.add(
            Material(
                tipo=tipo,
                nombre=meta["nombre"],
                unidad_compra=meta["unidad_compra"],
                precio=Decimal("0"),
                rendimiento=None,
            )
        )

    db.commit()


def listar_materiales(db: Session) -> list[Material]:
    materiales = {m.tipo: m for m in db.scalars(select(Material))}
    return [materiales[tipo] for tipo in TIPOS_MATERIAL if tipo in materiales]


def obtener_material(db: Session, tipo: str) -> Material | None:
    if tipo not in TIPOS_MATERIAL:
        return None
    return db.scalar(select(Material).where(Material.tipo == tipo))


def actualizar_material(
    db: Session, tipo: str, precio: Decimal, rendimiento: int | None = None
) -> Material:
    material = obtener_material(db, tipo)
    if material is None:
        raise ErrorNegocio("Ese material no existe.")

    if precio < 0:
        raise ErrorNegocio("El precio no puede ser negativo.")

    usa_rendimiento = METADATA_MATERIAL[tipo]["usa_rendimiento"]
    if usa_rendimiento:
        if rendimiento is None or rendimiento <= 0:
            unidad = material.unidad_compra
            raise ErrorNegocio(f"Indicá cuántos lazos rinde cada {unidad} — debe ser mayor que cero.")
    else:
        rendimiento = None

    material.precio = precio
    material.rendimiento = rendimiento
    db.commit()
    db.refresh(material)

    recalcular_productos_con_materiales(db)
    return material


def convertir_bolivares_a_usd(monto_bs: Decimal, tasa_bolivares: Decimal | None) -> Decimal | None:
    """Inverso de tasa_cambio.convertir_usd_a_bolivares — None si no
    hay tasa (nunca se inventa una)."""

    if tasa_bolivares is None or tasa_bolivares <= 0:
        return None

    return (monto_bs / tasa_bolivares).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def calcular_costo_bs(
    db: Session,
    *,
    lazos_por_metro_tela: int,
    lazos_por_barra_silicon: int,
    cantidad_ganchos: int,
    usa_hilo: bool,
    minutos_elaboracion: int,
) -> dict:
    """Desglose completo en bolívares — usado tanto para la vista
    previa en vivo del formulario de producto como para guardar el
    costo real."""

    if lazos_por_metro_tela <= 0 or lazos_por_barra_silicon <= 0:
        raise ErrorNegocio("Los lazos por metro de tela y por barra de silicón deben ser mayores que cero.")

    if cantidad_ganchos < 0 or minutos_elaboracion <= 0:
        raise ErrorNegocio("Revisá la cantidad de ganchos y los minutos de elaboración.")

    materiales = {m.tipo: m for m in listar_materiales(db)}
    tela = materiales["tela"]
    silicon = materiales["silicon"]
    gancho = materiales["gancho"]
    hilo = materiales["hilo"]

    costo_tela = tela.precio / lazos_por_metro_tela
    costo_silicon = silicon.precio / lazos_por_barra_silicon

    if cantidad_ganchos > 0 and gancho.rendimiento:
        costo_gancho = (gancho.precio / gancho.rendimiento) * cantidad_ganchos
    else:
        costo_gancho = Decimal("0")

    if usa_hilo and hilo.rendimiento:
        costo_hilo = hilo.precio / hilo.rendimiento
    else:
        costo_hilo = Decimal("0")

    subtotal_materiales = costo_tela + costo_silicon + costo_gancho + costo_hilo

    configuracion = db.get(Configuracion, 1)
    porcentaje_pequenos = configuracion.porcentaje_pequenos_materiales if configuracion else Decimal("5")
    valor_hora = configuracion.valor_hora_trabajo if configuracion else Decimal("0")

    pequenos_materiales = subtotal_materiales * (porcentaje_pequenos / Decimal("100"))
    mano_obra = (valor_hora / Decimal("60")) * minutos_elaboracion

    total_bs = subtotal_materiales + pequenos_materiales + mano_obra

    cuantizar = lambda valor: valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return {
        "costo_tela_bs": cuantizar(costo_tela),
        "costo_silicon_bs": cuantizar(costo_silicon),
        "costo_gancho_bs": cuantizar(costo_gancho),
        "costo_hilo_bs": cuantizar(costo_hilo),
        "subtotal_materiales_bs": cuantizar(subtotal_materiales),
        "pequenos_materiales_bs": cuantizar(pequenos_materiales),
        "mano_obra_bs": cuantizar(mano_obra),
        "total_bs": cuantizar(total_bs),
    }


def calcular_costo_producto(db: Session, producto: Producto) -> dict | None:
    """None si el producto todavía no tiene las respuestas de "Mis
    materiales" cargadas (sigue con costo manual de siempre)."""

    if producto.minutos_elaboracion is None:
        return None

    desglose = calcular_costo_bs(
        db,
        lazos_por_metro_tela=producto.lazos_por_metro_tela or 0,
        lazos_por_barra_silicon=producto.lazos_por_barra_silicon or 0,
        cantidad_ganchos=producto.cantidad_ganchos or 0,
        usa_hilo=producto.usa_hilo,
        minutos_elaboracion=producto.minutos_elaboracion,
    )

    tasa_activa = tasa_cambio.obtener_tasa_activa(db)
    tasa_bolivares = tasa_activa.tasa_bolivares if tasa_activa else None
    total_usd = convertir_bolivares_a_usd(desglose["total_bs"], tasa_bolivares)

    return {**desglose, "total_usd": total_usd, "tasa_bolivares": tasa_bolivares}


def recalcular_costo_producto(db: Session, producto: Producto) -> None:
    """Actualiza producto.costo_produccion en vivo si el producto usa
    la calculadora de materiales. No hace commit — el llamador decide
    cuándo (igual que el resto de services/productos.py)."""

    resultado = calcular_costo_producto(db, producto)
    if resultado is None or resultado["total_usd"] is None:
        return

    producto.costo_produccion = resultado["total_usd"]


def recalcular_productos_con_materiales(db: Session) -> None:
    """Se llama después de cambiar el precio de un material (o la
    tasa BCV): recalcula costo_produccion de TODOS los productos que
    usan la calculadora, en una sola transacción."""

    productos = db.scalars(
        select(Producto).where(Producto.activo.is_(True), Producto.minutos_elaboracion.is_not(None))
    )
    for producto in productos:
        recalcular_costo_producto(db, producto)

    db.commit()
