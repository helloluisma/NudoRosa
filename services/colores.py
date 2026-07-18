from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Color


def listar_colores_activos(db: Session) -> list[Color]:
    return list(
        db.scalars(select(Color).where(Color.activo.is_(True)).order_by(Color.orden, Color.id))
    )


def get_color_por_nombre(db: Session, nombre: str) -> Color | None:
    return db.scalar(select(Color).where(Color.nombre == nombre))
