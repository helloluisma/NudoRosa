import logging
import os
import sys
from logging.config import fileConfig
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import DATABASE_URL  # noqa: E402
import models  # noqa: E402  (registra todas las tablas en Base.metadata)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Las migraciones corren mejor contra la conexión DIRECTA de Neon, no
# la pooled (PgBouncer en modo transacción no sostiene bien una
# migración de varias sentencias dependientes entre sí — Neon lo
# documenta así). DATABASE_URL_UNPOOLED es opcional: si no está
# seteada (SQLite local, o cualquier Postgres sin pooler de por medio),
# se cae a la misma DATABASE_URL que usa el resto de la app.
config.set_main_option(
    "sqlalchemy.url", os.environ.get("DATABASE_URL_UNPOOLED", DATABASE_URL)
)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = models.Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

_logger = logging.getLogger("alembic.env")

# Revisión que crea el esquema completo desde cero (todas las tablas
# de la app). Es la única que puede chocar con una base preexistente
# creada antes de que este proyecto usara Alembic (ver
# _bootstrap_baseline_si_hace_falta).
_REVISION_ESQUEMA_INICIAL = "8c1c0d28abfb"

# Tablas que crea exactamente esa revisión (ver
# alembic/versions/8c1c0d28abfb_esquema_inicial.py). Se exige que
# estén TODAS antes de dar por hecho que la base es un "baseline" —
# con que exista una sola tabla suelta no alcanza.
_TABLAS_ESQUEMA_INICIAL = {
    "clientas", "productos", "colores", "producto_colores",
    "pedidos", "pedido_items", "pagos", "movimientos_inventario",
    "usuarios", "configuracion", "contador_pedidos",
}


def _bootstrap_baseline_si_hace_falta(connection: sa.Connection) -> None:
    """
    Adopta Alembic sobre una base que ya tenía el esquema completo
    ANTES de que este proyecto lo usara — el caso de Neon, cuyas
    tablas se crearon alguna vez con Base.metadata.create_all() y
    nunca quedó registrada ninguna revisión.

    Alembic no infiere versión a partir del esquema: si no existe la
    tabla `alembic_version`, asume que la base está en <base> (vacía)
    e intenta correr 8c1c0d28abfb entera — cuyos CREATE TABLE fallan
    porque esas tablas ya existen (DuplicateTable en Postgres). Eso es
    justo lo que se vio en el log de Render: "Running upgrade ->
    8c1c0d28abfb" seguido de un crash.

    Acá se detecta ESE caso puntual — todas las tablas de
    8c1c0d28abfb presentes, alembic_version ausente — y se registra
    (stamp) esa revisión como punto de partida, usando la misma API
    interna que usa el comando `alembic stamp` (MigrationContext.stamp,
    que además crea la tabla alembic_version si hace falta). No se
    ejecuta ningún DDL de 8c1c0d28abfb, así que las tablas existentes
    no se tocan. Con eso hecho, run_migrations_online() sigue su curso
    normal más abajo y corre solo lo que falte hasta head — hoy,
    únicamente 22aa14939071 — nunca 8c1c0d28abfb de nuevo, y nunca se
    salta ninguna migración real.

    Dos casos en los que esta función no hace nada:
      - Base nueva y vacía (deploy desde cero): no tiene ninguna de
        las tablas del esquema inicial, así que Alembic corre toda la
        cadena desde <base> de la forma normal.
      - Base que ya tiene alembic_version (el caso normal, incluido
        Render después de este fix): no hay nada que adoptar.
    """
    inspector = sa.inspect(connection)
    tablas_existentes = set(inspector.get_table_names())

    if "alembic_version" in tablas_existentes:
        return

    if not _TABLAS_ESQUEMA_INICIAL.issubset(tablas_existentes):
        return

    _logger.warning(
        "Se encontraron las tablas del esquema inicial sin alembic_version — "
        "registrando %s como punto de partida antes de migrar (adopción de "
        "Alembic sobre una base preexistente).",
        _REVISION_ESQUEMA_INICIAL,
    )

    migration_ctx = MigrationContext.configure(connection)
    migration_ctx.stamp(ScriptDirectory.from_config(config), _REVISION_ESQUEMA_INICIAL)
    connection.commit()


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        _bootstrap_baseline_si_hace_falta(connection)

        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
