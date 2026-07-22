"""
Modelos ORM de Nudo Rosa.

No existe una tabla "ventas" separada: una venta completada es un
`Pedido` con estado_entrega=ENTREGADO y estado_pago=PAGADO — ver
`services/pedidos.py` (`listar_ventas_completadas`). Pedidos, Cobros
y Ventas son la MISMA fila vista con distintos filtros, nunca datos
duplicados.

Los Enum se guardan como texto (native_enum=False): es más portable
entre SQLite y una futura migración a PostgreSQL que depender del
tipo ENUM nativo de cada motor.
"""

import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class EstadoEntrega(str, enum.Enum):
    PENDIENTE = "PENDIENTE"
    EN_PREPARACION = "EN_PREPARACION"
    LISTO_PARA_ENTREGAR = "LISTO_PARA_ENTREGAR"
    ENTREGADO = "ENTREGADO"
    CANCELADO = "CANCELADO"


class EstadoPago(str, enum.Enum):
    PENDIENTE = "PENDIENTE"
    PAGADO = "PAGADO"
    CANCELADO = "CANCELADO"


class TipoMovimientoInventario(str, enum.Enum):
    STOCK_INICIAL = "STOCK_INICIAL"
    ENTRADA = "ENTRADA"
    SALIDA_PEDIDO = "SALIDA_PEDIDO"
    DEVOLUCION_CANCELACION = "DEVOLUCION_CANCELACION"
    AJUSTE_POSITIVO = "AJUSTE_POSITIVO"
    AJUSTE_NEGATIVO = "AJUSTE_NEGATIVO"
    CORRECCION = "CORRECCION"


# Progresión válida de entrega — única fuente de verdad para las
# transiciones permitidas (services/pedidos.py la usa, nunca la
# reimplementa).
SIGUIENTE_ESTADO_ENTREGA = {
    EstadoEntrega.PENDIENTE: EstadoEntrega.EN_PREPARACION,
    EstadoEntrega.EN_PREPARACION: EstadoEntrega.LISTO_PARA_ENTREGAR,
    EstadoEntrega.LISTO_PARA_ENTREGAR: EstadoEntrega.ENTREGADO,
}

ESTADOS_ENTREGA_EDITABLES = {
    EstadoEntrega.PENDIENTE,
    EstadoEntrega.EN_PREPARACION,
    EstadoEntrega.LISTO_PARA_ENTREGAR,
}


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    nombre_usuario: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    password_salt: Mapped[str] = mapped_column(String(64))
    activo: Mapped[bool] = mapped_column(default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    ultimo_acceso_en: Mapped[datetime | None] = mapped_column(DateTime, default=None)


class Configuracion(Base):
    """Fila única (id=1): ajustes generales del negocio."""

    __tablename__ = "configuracion"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    nombre_negocio: Mapped[str] = mapped_column(String(120), default="Nudo Rosa by Ivanna")
    nombre_administrador: Mapped[str] = mapped_column(String(120), default="Ivanna")
    dias_credito: Mapped[int] = mapped_column(Integer, default=5)
    limite_poco_stock: Mapped[int] = mapped_column(Integer, default=5)
    moneda: Mapped[str] = mapped_column(String(8), default="$")
    version_app: Mapped[str] = mapped_column(String(20), default="1.0")
    logo: Mapped[str] = mapped_column(String(255), default="/static/images/logo.png")

    # "Mis materiales" (ver services/materiales.py): porcentaje que se
    # suma sobre el subtotal de tela+silicón+gancho+hilo para cubrir
    # insumos chiquitos (silicón de repuesto, cinta, etc. — no se
    # cargan uno por uno) y el valor de una hora de trabajo, en
    # bolívares, para calcular la mano de obra de cada lazo
    # (minutos_elaboracion del producto × valor_hora_trabajo / 60).
    # valor_hora_trabajo en 0 = todavía no configurado — nunca se
    # inventa un valor.
    porcentaje_pequenos_materiales: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("5"))
    valor_hora_trabajo: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))

    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ContadorPedidos(Base):
    """Fila única (id=1): contador atómico para numero_pedido (PED-000001)."""

    __tablename__ = "contador_pedidos"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    siguiente_valor: Mapped[int] = mapped_column(Integer, default=1)


class TasaCambio(Base):
    """
    Historial de tasas de cambio (hoy solo USD, vía BCV). Nunca se
    sobreescribe una fila existente: cada actualización —automática o
    manual— agrega una fila nueva con `activa=True` y desactiva la
    anterior en la misma transacción (ver
    services/tasa_cambio.py::_guardar_nueva_tasa). Así queda un
    historial completo y a la vez una única tasa activa por moneda
    para los cálculos actuales (`obtener_tasa_activa`).

    Una consulta al BCV que falla NUNCA agrega ni modifica una fila
    acá — services/tasa_cambio.py simplemente devuelve la tasa activa
    existente sin tocar la base. `mensaje_error` queda para dejar
    constancia en la fila cuando una actualización se guarda en un
    estado degradado (hoy no se usa en el camino feliz).
    """

    __tablename__ = "tasas_cambio"
    __table_args__ = (
        CheckConstraint("tasa_bolivares > 0", name="ck_tasa_cambio_positiva"),
        Index("ix_tasas_cambio_moneda_activa", "moneda", "activa"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    moneda: Mapped[str] = mapped_column(String(8), default="USD")
    tasa_bolivares: Mapped[Decimal] = mapped_column(Numeric(18, 8))
    fuente: Mapped[str] = mapped_column(String(20), default="BCV")
    fecha_vigencia: Mapped[date] = mapped_column(Date, default=date.today)
    fecha_actualizacion: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    actualizada_automaticamente: Mapped[bool] = mapped_column(default=True)
    mensaje_error: Mapped[str | None] = mapped_column(Text, default=None)
    activa: Mapped[bool] = mapped_column(default=True)


class Clienta(Base):
    __tablename__ = "clientas"
    __table_args__ = (
        Index("ix_clientas_nombres", "nombres"),
        Index("ix_clientas_apellidos", "apellidos"),
        Index("ix_clientas_telefono", "telefono"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nombres: Mapped[str] = mapped_column(String(120))
    apellidos: Mapped[str] = mapped_column(String(120))
    telefono: Mapped[str | None] = mapped_column(String(40), default=None)
    email: Mapped[str | None] = mapped_column(String(120), default=None)
    direccion: Mapped[str | None] = mapped_column(String(255), default=None)
    fecha_nacimiento: Mapped[date | None] = mapped_column(Date, default=None)
    avatar: Mapped[str | None] = mapped_column(String(255), default=None)
    notas: Mapped[str | None] = mapped_column(Text, default=None)
    activa: Mapped[bool] = mapped_column(default=True)
    creada_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    actualizada_en: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    pedidos: Mapped[list["Pedido"]] = relationship(back_populates="clienta")


class Producto(Base):
    __tablename__ = "productos"
    __table_args__ = (
        CheckConstraint("costo_produccion >= 0", name="ck_producto_costo_no_negativo"),
        CheckConstraint("precio_publico >= 0", name="ck_producto_precio_no_negativo"),
        CheckConstraint("stock_actual >= 0", name="ck_producto_stock_no_negativo"),
        CheckConstraint(
            "lazos_por_metro_tela IS NULL OR lazos_por_metro_tela > 0",
            name="ck_producto_lazos_metro_tela_positivo",
        ),
        CheckConstraint(
            "lazos_por_barra_silicon IS NULL OR lazos_por_barra_silicon > 0",
            name="ck_producto_lazos_barra_silicon_positivo",
        ),
        CheckConstraint(
            "cantidad_ganchos IS NULL OR cantidad_ganchos >= 0",
            name="ck_producto_cantidad_ganchos_no_negativa",
        ),
        CheckConstraint(
            "minutos_elaboracion IS NULL OR minutos_elaboracion > 0",
            name="ck_producto_minutos_elaboracion_positivo",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(160))
    imagen: Mapped[str | None] = mapped_column(String(255), default=None)

    # Costo de elaboración: fuente de verdad en dólares (para poder
    # compararse contra precio_publico y calcular ganancia_total sin
    # mezclar monedas), pero para un producto que usa "Mis materiales"
    # (ver services/materiales.py) ES UN VALOR DERIVADO — se recalcula
    # solo, en vivo, a partir de los precios de materiales (en
    # bolívares) y la tasa BCV vigente cada vez que se guarda el
    # producto o cambia un precio de material. Numeric (no Integer,
    # como precio_publico) porque un costo convertido desde bolívares
    # casi siempre cae en centavos — con enteros, muchos lazos
    # redondearían a $0 y la ganancia mostrada quedaría mal.
    costo_produccion: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    precio_publico: Mapped[int] = mapped_column(Integer, default=0)
    stock_actual: Mapped[int] = mapped_column(Integer, default=0)

    # Preguntas de "Mis materiales" (services/materiales.py). Todas
    # nulas por defecto: un producto sin estas respuestas sigue
    # usando su costo_produccion manual de siempre (compatibilidad con
    # productos creados antes de esta funcionalidad). minutos_elaboracion
    # no nulo es la señal de "este producto ya usa la calculadora".
    lazos_por_metro_tela: Mapped[int | None] = mapped_column(Integer, default=None)
    lazos_por_barra_silicon: Mapped[int | None] = mapped_column(Integer, default=None)
    cantidad_ganchos: Mapped[int | None] = mapped_column(Integer, default=None)
    usa_hilo: Mapped[bool] = mapped_column(default=True)
    minutos_elaboracion: Mapped[int | None] = mapped_column(Integer, default=None)

    activo: Mapped[bool] = mapped_column(default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    colores: Mapped[list["ProductoColor"]] = relationship(back_populates="producto")


class Color(Base):
    __tablename__ = "colores"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(60), unique=True)
    codigo_hex: Mapped[str] = mapped_column(String(7))
    activo: Mapped[bool] = mapped_column(default=True)
    orden: Mapped[int] = mapped_column(Integer, default=0)


class ProductoColor(Base):
    __tablename__ = "producto_colores"

    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"), primary_key=True)
    color_id: Mapped[int] = mapped_column(ForeignKey("colores.id"), primary_key=True)
    activo: Mapped[bool] = mapped_column(default=True)

    producto: Mapped["Producto"] = relationship(back_populates="colores")
    color: Mapped["Color"] = relationship()


TIPOS_MATERIAL = ("tela", "silicon", "gancho", "hilo")


class Material(Base):
    """
    "Mis materiales" (ver services/materiales.py). Fila fija por
    tipo — se siembran las 4 (tela, silicón, gancho, hilo) una sola
    vez al arrancar (asegurar_materiales_iniciales), nunca se crean ni
    borran filas desde la UI, solo se edita precio/rendimiento.

    precio está en BOLÍVARES (así los compra Ivanna) — nunca en
    dólares. rendimiento es una constante del material, no del
    producto: cuántos ganchos trae un paquete, o cuántos lazos rinde
    un carrete de hilo. Para tela y silicón el rendimiento depende de
    cada producto (cuántos lazos salen de un metro/barra), así que
    vive en Producto, no acá (rendimiento queda NULL para esos dos).
    """

    __tablename__ = "materiales"
    __table_args__ = (
        CheckConstraint("precio >= 0", name="ck_material_precio_no_negativo"),
        CheckConstraint("rendimiento IS NULL OR rendimiento > 0", name="ck_material_rendimiento_positivo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[str] = mapped_column(String(20), unique=True)
    nombre: Mapped[str] = mapped_column(String(60))
    unidad_compra: Mapped[str] = mapped_column(String(30))
    precio: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    rendimiento: Mapped[int | None] = mapped_column(Integer, default=None)
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Pedido(Base):
    """
    Operación principal del negocio. Pedidos, Cobros y Ventas
    completadas son vistas/consultas sobre esta misma tabla (ver
    services/pedidos.py) — nunca se copia a otra tabla.
    """

    __tablename__ = "pedidos"
    __table_args__ = (
        Index("ix_pedidos_clienta_id", "clienta_id"),
        Index("ix_pedidos_estado_entrega", "estado_entrega"),
        Index("ix_pedidos_estado_pago", "estado_pago"),
        Index("ix_pedidos_fecha_creacion", "fecha_creacion"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    numero_pedido: Mapped[str] = mapped_column(String(20), unique=True)
    clienta_id: Mapped[int] = mapped_column(ForeignKey("clientas.id"))

    estado_entrega: Mapped[EstadoEntrega] = mapped_column(
        Enum(EstadoEntrega, native_enum=False, length=30), default=EstadoEntrega.PENDIENTE
    )
    estado_pago: Mapped[EstadoPago] = mapped_column(
        Enum(EstadoPago, native_enum=False, length=20), default=EstadoPago.PENDIENTE
    )

    fecha_creacion: Mapped[date] = mapped_column(Date, default=date.today)
    fecha_estimada_entrega: Mapped[date | None] = mapped_column(Date, default=None)
    fecha_entrega: Mapped[date | None] = mapped_column(Date, default=None)
    fecha_vencimiento_pago: Mapped[date | None] = mapped_column(Date, default=None)
    fecha_pago: Mapped[date | None] = mapped_column(Date, default=None)

    subtotal: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=0)
    # Numeric (no Integer): costo_total viene de costo_unitario, que
    # puede tener centavos reales al convertir desde bolívares (ver
    # Producto.costo_produccion). ganancia_total hereda la misma
    # precisión porque es total(entero) - costo_total.
    costo_total: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=Decimal("0"))
    ganancia_total: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=Decimal("0"))

    # Se escriben en dos momentos distintos, a propósito:
    #   1. Al crear el pedido (services/pedidos.py::crear_pedido) —
    #      valor inicial, con la tasa de ese instante.
    #   2. Al marcar el pedido como pagado
    #      (services/pedidos.py::marcar_pago) — ACÁ es donde quedan
    #      congelados de verdad, con la tasa vigente en ese momento
    #      (no necesariamente la misma que en el paso 1).
    # Mientras el pedido sigue pendiente de pago, estas dos columnas
    # NO son la fuente de verdad para mostrar el equivalente en
    # bolívares — main.py::_venta_enriquecida lo recalcula con la tasa
    # BCV vigente en cada lectura. Una vez pagado, nunca más se tocan:
    # una tasa BCV nueva no puede cambiar una venta ya cobrada. Nulos
    # en pedidos creados antes de esta columna — las plantillas no
    # inventan un valor para esos casos.
    tasa_bcv_aplicada: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), default=None)
    total_bolivares: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), default=None)

    notas: Mapped[str | None] = mapped_column(Text, default=None)
    cancelado_en: Mapped[datetime | None] = mapped_column(DateTime, default=None)

    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    clienta: Mapped["Clienta"] = relationship(back_populates="pedidos")
    items: Mapped[list["PedidoItem"]] = relationship(
        back_populates="pedido", cascade="all, delete-orphan"
    )
    pagos: Mapped[list["Pago"]] = relationship(back_populates="pedido")
    movimientos: Mapped[list["MovimientoInventario"]] = relationship(back_populates="pedido")


class PedidoItem(Base):
    """
    Hoy cada pedido tiene un solo item (un producto/color/cantidad),
    pero la tabla ya soporta varios por pedido sin cambios futuros.
    precio_unitario/costo_unitario son históricos: si el precio del
    producto cambia después, este item conserva el valor con el que
    se vendió.
    """

    __tablename__ = "pedido_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    pedido_id: Mapped[int] = mapped_column(ForeignKey("pedidos.id"))
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"))
    color_id: Mapped[int | None] = mapped_column(ForeignKey("colores.id"), default=None)

    cantidad: Mapped[int] = mapped_column(Integer)
    precio_unitario: Mapped[int] = mapped_column(Integer)
    # Numeric: ver el comentario en Pedido.costo_total sobre por qué
    # el costo necesita centavos y el precio de venta no.
    costo_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    subtotal: Mapped[int] = mapped_column(Integer)
    costo_subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 4))

    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    pedido: Mapped["Pedido"] = relationship(back_populates="items")
    producto: Mapped["Producto"] = relationship()
    color: Mapped["Color | None"] = relationship()


class Pago(Base):
    """
    Historial de pagos de un pedido. Hoy la UI solo registra un pago
    completo, pero la tabla soporta pagos parciales futuros: el
    estado_pago del pedido se recalcula comparando la suma de pagos
    contra el total (ver services/pedidos.py).
    """

    __tablename__ = "pagos"
    __table_args__ = (
        Index("ix_pagos_pedido_id", "pedido_id"),
        CheckConstraint("monto >= 0", name="ck_pago_monto_no_negativo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    pedido_id: Mapped[int] = mapped_column(ForeignKey("pedidos.id"))
    monto: Mapped[int] = mapped_column(Integer)
    metodo_pago: Mapped[str | None] = mapped_column(String(40), default=None)
    referencia: Mapped[str | None] = mapped_column(String(120), default=None)
    fecha_pago: Mapped[date] = mapped_column(Date, default=date.today)
    notas: Mapped[str | None] = mapped_column(Text, default=None)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    pedido: Mapped["Pedido"] = relationship(back_populates="pagos")


class MovimientoInventario(Base):
    """
    Historial de todo cambio de stock. Convención: cantidad positiva
    = entrada, cantidad negativa = salida. Nunca se cambia
    stock_actual sin crear un movimiento (ver services/inventario.py).
    """

    __tablename__ = "movimientos_inventario"
    __table_args__ = (Index("ix_movimientos_producto_id", "producto_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"))
    pedido_id: Mapped[int | None] = mapped_column(ForeignKey("pedidos.id"), default=None)
    tipo_movimiento: Mapped[TipoMovimientoInventario] = mapped_column(
        Enum(TipoMovimientoInventario, native_enum=False, length=30)
    )
    cantidad: Mapped[int] = mapped_column(Integer)
    stock_anterior: Mapped[int] = mapped_column(Integer)
    stock_nuevo: Mapped[int] = mapped_column(Integer)
    # Numeric: puede recibir el costo calculado por "Mis materiales"
    # (services/materiales.py), casi siempre con centavos.
    costo_unitario: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), default=None)
    motivo: Mapped[str | None] = mapped_column(String(255), default=None)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), default=None)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    producto: Mapped["Producto"] = relationship()
    pedido: Mapped["Pedido | None"] = relationship(back_populates="movimientos")
