"""materiales y costo de elaboracion

Revision ID: 2222c866c6b8
Revises: 22aa14939071
Create Date: 2026-07-21 16:41:47.261892

"""
import logging
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2222c866c6b8'
down_revision: Union[str, Sequence[str], None] = '22aa14939071'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Mismo namespace "alembic." que la migración de tasa_bcv (ver
# 22aa14939071) para heredar el nivel INFO configurado en alembic.ini.
logger = logging.getLogger("alembic.migration.materiales")


def upgrade() -> None:
    """
    Idempotente a propósito, siguiendo el mismo criterio que
    22aa14939071_tasa_de_cambio_bcv.py: cada paso se fija primero, con
    el inspector, si ya está hecho antes de ejecutarlo.
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # --- Tabla materiales ------------------------------------------------
    if not inspector.has_table("materiales"):
        logger.info("Creando tabla materiales...")
        op.create_table(
            'materiales',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('tipo', sa.String(length=20), nullable=False),
            sa.Column('nombre', sa.String(length=60), nullable=False),
            sa.Column('unidad_compra', sa.String(length=30), nullable=False),
            sa.Column('precio', sa.Numeric(precision=12, scale=2), nullable=False),
            sa.Column('rendimiento', sa.Integer(), nullable=True),
            sa.Column('actualizado_en', sa.DateTime(), nullable=False),
            sa.CheckConstraint('precio >= 0', name='ck_material_precio_no_negativo'),
            sa.CheckConstraint('rendimiento IS NULL OR rendimiento > 0', name='ck_material_rendimiento_positivo'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('tipo'),
        )
    else:
        logger.info("La tabla materiales ya existe — se omite create_table.")

    # --- Columnas nuevas en productos (preguntas de "Mis materiales") ----
    columnas_productos = {c["name"] for c in sa.inspect(bind).get_columns("productos")}

    if "lazos_por_metro_tela" not in columnas_productos:
        op.add_column('productos', sa.Column('lazos_por_metro_tela', sa.Integer(), nullable=True))
    if "lazos_por_barra_silicon" not in columnas_productos:
        op.add_column('productos', sa.Column('lazos_por_barra_silicon', sa.Integer(), nullable=True))
    if "cantidad_ganchos" not in columnas_productos:
        op.add_column('productos', sa.Column('cantidad_ganchos', sa.Integer(), nullable=True))
    if "usa_hilo" not in columnas_productos:
        op.add_column('productos', sa.Column('usa_hilo', sa.Boolean(), nullable=False, server_default=sa.true()))
    if "minutos_elaboracion" not in columnas_productos:
        op.add_column('productos', sa.Column('minutos_elaboracion', sa.Integer(), nullable=True))

    with op.batch_alter_table('productos') as batch_op:
        for nombre, condicion in (
            ('ck_producto_lazos_metro_tela_positivo', 'lazos_por_metro_tela IS NULL OR lazos_por_metro_tela > 0'),
            ('ck_producto_lazos_barra_silicon_positivo', 'lazos_por_barra_silicon IS NULL OR lazos_por_barra_silicon > 0'),
            ('ck_producto_cantidad_ganchos_no_negativa', 'cantidad_ganchos IS NULL OR cantidad_ganchos >= 0'),
            ('ck_producto_minutos_elaboracion_positivo', 'minutos_elaboracion IS NULL OR minutos_elaboracion > 0'),
        ):
            restricciones_existentes = {ck["name"] for ck in sa.inspect(bind).get_check_constraints("productos")}
            if nombre not in restricciones_existentes:
                batch_op.create_check_constraint(nombre, condicion)

    # costo_produccion: Integer -> Numeric(12, 4). Un costo convertido
    # desde bolívares casi siempre tiene centavos — con enteros varios
    # lazos redondeaban a $0.
    columna_costo = next(c for c in sa.inspect(bind).get_columns("productos") if c["name"] == "costo_produccion")
    if isinstance(columna_costo["type"], sa.Integer):
        logger.info("Convirtiendo productos.costo_produccion a Numeric(12, 4)...")
        with op.batch_alter_table('productos') as batch_op:
            batch_op.alter_column(
                'costo_produccion',
                existing_type=sa.Integer(),
                type_=sa.Numeric(precision=12, scale=4),
                existing_nullable=False,
            )
    else:
        logger.info("productos.costo_produccion ya es Numeric — se omite.")

    # --- Configuracion: pequeños materiales + valor de la hora ------------
    columnas_configuracion = {c["name"] for c in sa.inspect(bind).get_columns("configuracion")}

    if "porcentaje_pequenos_materiales" not in columnas_configuracion:
        op.add_column(
            'configuracion',
            sa.Column(
                'porcentaje_pequenos_materiales',
                sa.Numeric(precision=5, scale=2),
                nullable=False,
                server_default='5',
            ),
        )
    if "valor_hora_trabajo" not in columnas_configuracion:
        op.add_column(
            'configuracion',
            sa.Column('valor_hora_trabajo', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'),
        )

    # --- Pedidos / pedido_items / movimientos_inventario: Integer -> Numeric
    def _convertir_si_hace_falta(tabla, columna, precision, escala, nullable):
        info = next(c for c in sa.inspect(bind).get_columns(tabla) if c["name"] == columna)
        if not isinstance(info["type"], sa.Integer):
            logger.info("%s.%s ya es Numeric — se omite.", tabla, columna)
            return

        logger.info("Convirtiendo %s.%s a Numeric(%s, %s)...", tabla, columna, precision, escala)
        with op.batch_alter_table(tabla) as batch_op:
            batch_op.alter_column(
                columna,
                existing_type=sa.Integer(),
                type_=sa.Numeric(precision=precision, scale=escala),
                existing_nullable=nullable,
            )

    _convertir_si_hace_falta("pedidos", "costo_total", 14, 4, False)
    _convertir_si_hace_falta("pedidos", "ganancia_total", 14, 4, False)
    _convertir_si_hace_falta("pedido_items", "costo_unitario", 12, 4, False)
    _convertir_si_hace_falta("pedido_items", "costo_subtotal", 14, 4, False)
    _convertir_si_hace_falta("movimientos_inventario", "costo_unitario", 12, 4, True)

    logger.info("Migración completada.")


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('movimientos_inventario') as batch_op:
        batch_op.alter_column('costo_unitario', existing_type=sa.Numeric(precision=12, scale=4), type_=sa.Integer())

    with op.batch_alter_table('pedido_items') as batch_op:
        batch_op.alter_column('costo_subtotal', existing_type=sa.Numeric(precision=14, scale=4), type_=sa.Integer())
        batch_op.alter_column('costo_unitario', existing_type=sa.Numeric(precision=12, scale=4), type_=sa.Integer())

    with op.batch_alter_table('pedidos') as batch_op:
        batch_op.alter_column('ganancia_total', existing_type=sa.Numeric(precision=14, scale=4), type_=sa.Integer())
        batch_op.alter_column('costo_total', existing_type=sa.Numeric(precision=14, scale=4), type_=sa.Integer())

    op.drop_column('configuracion', 'valor_hora_trabajo')
    op.drop_column('configuracion', 'porcentaje_pequenos_materiales')

    with op.batch_alter_table('productos') as batch_op:
        batch_op.alter_column('costo_produccion', existing_type=sa.Numeric(precision=12, scale=4), type_=sa.Integer())
        batch_op.drop_constraint('ck_producto_minutos_elaboracion_positivo', type_='check')
        batch_op.drop_constraint('ck_producto_cantidad_ganchos_no_negativa', type_='check')
        batch_op.drop_constraint('ck_producto_lazos_barra_silicon_positivo', type_='check')
        batch_op.drop_constraint('ck_producto_lazos_metro_tela_positivo', type_='check')

    op.drop_column('productos', 'minutos_elaboracion')
    op.drop_column('productos', 'usa_hilo')
    op.drop_column('productos', 'cantidad_ganchos')
    op.drop_column('productos', 'lazos_por_barra_silicon')
    op.drop_column('productos', 'lazos_por_metro_tela')

    op.drop_table('materiales')
