"""
Configuración de la base de datos de Nudo Rosa.

En local, sin nada configurado, usa SQLite (archivo `nudorosa.db` en la
raíz del proyecto). En producción (Render u otro host), si existe la
variable de entorno DATABASE_URL, se usa esa base — normalmente
PostgreSQL — en su lugar.

Esto no es opcional en Render: el filesystem de un servicio web ahí es
efímero (se reinicia con cada deploy y, en el plan free, cada vez que el
servicio "duerme" por inactividad y despierta de nuevo). Un archivo
SQLite guardado ahí se borra en cualquiera de esos reinicios — por eso
los productos y clientas "desaparecían" después de cerrar sesión: no es
que se perdieran, es que el próximo request arrancaba el proceso desde
cero con un nudorosa.db vacío. PostgreSQL en Render corre en un servicio
aparte con disco persistente propio, así que no tiene ese problema.

Toda la app habla con SQLAlchemy, nunca con SQL crudo ni con
particularidades de un motor específico fuera de este archivo, así que
el cambio de motor no afecta a `services/` ni a `main.py`.
"""

import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

BASE_DIR = Path(__file__).resolve().parent
RUTA_BASE_DATOS = BASE_DIR / "nudorosa.db"

_DATABASE_URL_ENV = os.environ.get("DATABASE_URL")

if _DATABASE_URL_ENV:
    # Render (y Heroku, de donde viene la convención) entregan la URL
    # con el esquema viejo "postgres://", que psycopg2/SQLAlchemy 2.x
    # ya no aceptan — hay que normalizarlo a "postgresql://".
    DATABASE_URL = _DATABASE_URL_ENV.replace("postgres://", "postgresql://", 1)
else:
    DATABASE_URL = f"sqlite:///{RUTA_BASE_DATOS}"

_ES_SQLITE = DATABASE_URL.startswith("sqlite")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if _ES_SQLITE else {},
)


if _ES_SQLITE:
    @event.listens_for(engine, "connect")
    def _activar_claves_foraneas(conexion_dbapi, _record):
        # SQLite trae las FOREIGN KEY apagadas por defecto; sin esto,
        # las relaciones e integridad referencial no se respetan.
        cursor = conexion_dbapi.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
