"""
Configuración de la base de datos de Nudo Rosa.

SQLite hoy, pensado para migrar a PostgreSQL sin reescribir lógica de
negocio: toda la app habla con SQLAlchemy, nunca con SQL crudo ni con
particularidades de SQLite fuera de este archivo.
"""

from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

BASE_DIR = Path(__file__).resolve().parent
RUTA_BASE_DATOS = BASE_DIR / "nudorosa.db"
DATABASE_URL = f"sqlite:///{RUTA_BASE_DATOS}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)


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
