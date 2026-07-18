"""
Autenticación y configuración general del negocio.

Hoy soporta un único administrador, pero `usuarios` ya es una tabla
(no un valor suelto) para poder pasar a varios usuarios sin cambiar
el esquema.
"""

import hashlib
import hmac
import json
import secrets
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Configuracion, Usuario

BASE_DIR = Path(__file__).resolve().parent.parent
RUTA_SEGURIDAD_JSON_LEGACY = BASE_DIR / "seguridad.json"

USUARIO_ADMIN_POR_DEFECTO = "admin"
PASSWORD_ADMIN_POR_DEFECTO = "Ivanna**0102"
ITERACIONES_HASH = 200_000


def hashear_password(password: str, salt_hex: str | None = None) -> tuple[str, str]:
    salt_hex = salt_hex or secrets.token_hex(16)
    hash_ = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), ITERACIONES_HASH
    ).hex()
    return hash_, salt_hex


def asegurar_datos_iniciales(db: Session) -> None:
    """Crea el administrador y la configuración una sola vez (si no
    existen). Si ya existe seguridad.json de una versión anterior de
    la app, reutiliza ese hash/salt tal cual — no resetea la
    contraseña que la usuaria ya haya cambiado."""

    if db.scalar(select(Configuracion).where(Configuracion.id == 1)) is None:
        db.add(Configuracion(id=1))

    if db.scalar(select(Usuario)) is None:
        if RUTA_SEGURIDAD_JSON_LEGACY.exists():
            legacy = json.loads(RUTA_SEGURIDAD_JSON_LEGACY.read_text(encoding="utf-8"))
            nombre = legacy.get("nombre_administrador", "Ivanna")
            nombre_usuario = legacy.get("usuario", USUARIO_ADMIN_POR_DEFECTO)
            password_hash = legacy["password_hash"]
            password_salt = legacy["password_salt"]

            configuracion = db.scalar(select(Configuracion).where(Configuracion.id == 1))
            if configuracion is not None:
                configuracion.nombre_administrador = nombre
        else:
            password_hash, password_salt = hashear_password(PASSWORD_ADMIN_POR_DEFECTO)
            nombre = "Ivanna"
            nombre_usuario = USUARIO_ADMIN_POR_DEFECTO

        db.add(
            Usuario(
                nombre=nombre,
                nombre_usuario=nombre_usuario,
                password_hash=password_hash,
                password_salt=password_salt,
            )
        )

    db.commit()


def obtener_configuracion(db: Session) -> Configuracion:
    return db.scalar(select(Configuracion).where(Configuracion.id == 1))


def obtener_administrador(db: Session) -> Usuario | None:
    return db.scalar(select(Usuario).where(Usuario.activo.is_(True)).order_by(Usuario.id))


def verificar_credenciales(db: Session, nombre_usuario: str, password: str) -> Usuario | None:
    usuario = db.scalar(
        select(Usuario).where(Usuario.nombre_usuario == nombre_usuario, Usuario.activo.is_(True))
    )
    if usuario is None:
        return None

    hash_calculado, _ = hashear_password(password, usuario.password_salt)
    if not hmac.compare_digest(hash_calculado, usuario.password_hash):
        return None

    usuario.ultimo_acceso_en = datetime.utcnow()
    db.commit()
    return usuario


def actualizar_seguridad(
    db: Session, nombre_administrador: str, nombre_usuario: str, password: str = ""
) -> Usuario:
    usuario = obtener_administrador(db)
    configuracion = obtener_configuracion(db)

    usuario.nombre = nombre_administrador
    usuario.nombre_usuario = nombre_usuario
    configuracion.nombre_administrador = nombre_administrador

    if password:
        password_hash, salt = hashear_password(password)
        usuario.password_hash = password_hash
        usuario.password_salt = salt

    db.commit()
    db.refresh(usuario)
    return usuario
