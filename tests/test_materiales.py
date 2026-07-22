"""
Tests de services/materiales.py — la calculadora de "Mis materiales".

Todo el cálculo corre en bolívares y recién al final se convierte a
dólares con la tasa BCV vigente (igual que services/tasa_cambio.py),
así que estos tests fijan precios de materiales y una tasa conocidos
para poder verificar el resultado a mano.
"""

from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base
from models import Configuracion, Material, Producto, TasaCambio
from services import ErrorNegocio, materiales


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    sesion = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    try:
        yield sesion
    finally:
        sesion.close()


def _cargar_materiales_de_prueba(db):
    """Tela Bs. 400/metro, silicón Bs. 150/barra, gancho Bs. 60/paquete
    de 20, hilo Bs. 100/carrete que rinde 50 lazos."""

    materiales.asegurar_materiales_iniciales(db)
    materiales.actualizar_material(db, "tela", Decimal("400"))
    materiales.actualizar_material(db, "silicon", Decimal("150"))
    materiales.actualizar_material(db, "gancho", Decimal("60"), rendimiento=20)
    materiales.actualizar_material(db, "hilo", Decimal("100"), rendimiento=50)


def _configurar_produccion(db, porcentaje="5", valor_hora="120"):
    configuracion = Configuracion(
        id=1,
        porcentaje_pequenos_materiales=Decimal(porcentaje),
        valor_hora_trabajo=Decimal(valor_hora),
    )
    db.add(configuracion)
    db.commit()


def test_asegurar_materiales_iniciales_siembra_las_4_filas(db):
    materiales.asegurar_materiales_iniciales(db)

    tipos = {m.tipo for m in materiales.listar_materiales(db)}
    assert tipos == {"tela", "silicon", "gancho", "hilo"}
    assert all(m.precio == 0 for m in materiales.listar_materiales(db))


def test_asegurar_materiales_iniciales_no_pisa_datos_existentes(db):
    materiales.asegurar_materiales_iniciales(db)
    materiales.actualizar_material(db, "tela", Decimal("400"))

    materiales.asegurar_materiales_iniciales(db)

    assert materiales.obtener_material(db, "tela").precio == Decimal("400")


def test_actualizar_material_rechaza_precio_negativo(db):
    materiales.asegurar_materiales_iniciales(db)

    with pytest.raises(ErrorNegocio):
        materiales.actualizar_material(db, "tela", Decimal("-1"))


def test_actualizar_material_gancho_exige_rendimiento_positivo(db):
    materiales.asegurar_materiales_iniciales(db)

    with pytest.raises(ErrorNegocio):
        materiales.actualizar_material(db, "gancho", Decimal("60"), rendimiento=0)

    with pytest.raises(ErrorNegocio):
        materiales.actualizar_material(db, "gancho", Decimal("60"), rendimiento=None)


def test_calcular_costo_bs_desglose_correcto(db):
    _cargar_materiales_de_prueba(db)
    _configurar_produccion(db, porcentaje="5", valor_hora="120")

    desglose = materiales.calcular_costo_bs(
        db,
        lazos_por_metro_tela=8,
        lazos_por_barra_silicon=20,
        cantidad_ganchos=1,
        usa_hilo=True,
        minutos_elaboracion=15,
    )

    # tela: 400/8 = 50 | silicon: 150/20 = 7.5 | gancho: (60/20)*1 = 3
    # hilo: 100/50 = 2 -> subtotal materiales = 62.5
    assert desglose["costo_tela_bs"] == Decimal("50.00")
    assert desglose["costo_silicon_bs"] == Decimal("7.50")
    assert desglose["costo_gancho_bs"] == Decimal("3.00")
    assert desglose["costo_hilo_bs"] == Decimal("2.00")
    assert desglose["subtotal_materiales_bs"] == Decimal("62.50")

    # 5% de 62.50 = 3.125 -> redondeado a 3.13 (ROUND_HALF_UP)
    assert desglose["pequenos_materiales_bs"] == Decimal("3.13")

    # 120/60 * 15 minutos = 30
    assert desglose["mano_obra_bs"] == Decimal("30.00")

    assert desglose["total_bs"] == Decimal("95.63")


def test_calcular_costo_bs_sin_hilo_ni_ganchos(db):
    _cargar_materiales_de_prueba(db)
    _configurar_produccion(db, porcentaje="0", valor_hora="0")

    desglose = materiales.calcular_costo_bs(
        db,
        lazos_por_metro_tela=8,
        lazos_por_barra_silicon=20,
        cantidad_ganchos=0,
        usa_hilo=False,
        minutos_elaboracion=10,
    )

    assert desglose["costo_gancho_bs"] == Decimal("0")
    assert desglose["costo_hilo_bs"] == Decimal("0")
    assert desglose["mano_obra_bs"] == Decimal("0.00")
    assert desglose["total_bs"] == Decimal("57.50")  # 50 + 7.50


@pytest.mark.parametrize(
    "kwargs",
    [
        {"lazos_por_metro_tela": 0, "lazos_por_barra_silicon": 20, "cantidad_ganchos": 1, "usa_hilo": True, "minutos_elaboracion": 10},
        {"lazos_por_metro_tela": 8, "lazos_por_barra_silicon": 0, "cantidad_ganchos": 1, "usa_hilo": True, "minutos_elaboracion": 10},
        {"lazos_por_metro_tela": 8, "lazos_por_barra_silicon": 20, "cantidad_ganchos": -1, "usa_hilo": True, "minutos_elaboracion": 10},
        {"lazos_por_metro_tela": 8, "lazos_por_barra_silicon": 20, "cantidad_ganchos": 1, "usa_hilo": True, "minutos_elaboracion": 0},
    ],
)
def test_calcular_costo_bs_rechaza_rendimientos_invalidos(db, kwargs):
    _cargar_materiales_de_prueba(db)
    _configurar_produccion(db)

    with pytest.raises(ErrorNegocio):
        materiales.calcular_costo_bs(db, **kwargs)


def test_convertir_bolivares_a_usd(db):
    assert materiales.convertir_bolivares_a_usd(Decimal("100"), Decimal("200")) == Decimal("0.5000")
    assert materiales.convertir_bolivares_a_usd(Decimal("100"), None) is None


def test_calcular_costo_producto_none_sin_datos_de_materiales(db):
    _cargar_materiales_de_prueba(db)
    _configurar_produccion(db)

    producto = Producto(nombre="Lazo de prueba", precio_publico=5, costo_produccion=Decimal("0"))
    db.add(producto)
    db.commit()

    assert materiales.calcular_costo_producto(db, producto) is None


def test_recalcular_costo_producto_convierte_a_usd_con_la_tasa_vigente(db):
    _cargar_materiales_de_prueba(db)
    _configurar_produccion(db, porcentaje="5", valor_hora="120")

    db.add(TasaCambio(moneda="USD", tasa_bolivares=Decimal("100"), activa=True))
    db.commit()

    producto = Producto(
        nombre="Lazo con materiales",
        precio_publico=5,
        costo_produccion=Decimal("0"),
        lazos_por_metro_tela=8,
        lazos_por_barra_silicon=20,
        cantidad_ganchos=1,
        usa_hilo=True,
        minutos_elaboracion=15,
    )
    db.add(producto)
    db.commit()

    materiales.recalcular_costo_producto(db, producto)

    # total_bs = 95.63 (ver test_calcular_costo_bs_desglose_correcto),
    # tasa 100 Bs/USD -> 0.9563
    assert producto.costo_produccion == Decimal("0.9563")


def test_recalcular_productos_con_materiales_actualiza_todos(db):
    _cargar_materiales_de_prueba(db)
    _configurar_produccion(db, porcentaje="0", valor_hora="0")
    db.add(TasaCambio(moneda="USD", tasa_bolivares=Decimal("100"), activa=True))

    producto = Producto(
        nombre="Lazo con materiales",
        precio_publico=5,
        costo_produccion=Decimal("0"),
        lazos_por_metro_tela=8,
        lazos_por_barra_silicon=20,
        cantidad_ganchos=0,
        usa_hilo=False,
        minutos_elaboracion=10,
    )
    db.add(producto)
    db.commit()

    # Sube el precio de la tela después de crear el producto — el
    # costo guardado queda desactualizado hasta recalcular.
    materiales.actualizar_material(db, "tela", Decimal("800"))
    db.refresh(producto)
    assert producto.costo_produccion == Decimal("1.0750")  # (800/8 + 150/20) / 100 = (100+7.5)/100
