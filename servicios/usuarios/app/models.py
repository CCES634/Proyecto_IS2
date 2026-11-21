from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def ahora():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Rol(db.Model):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(30), unique=True, nullable=False)
    descripcion = db.Column(db.String(150))


class Usuario(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    correo = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    rol_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    ultimo_acceso = db.Column(db.DateTime)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora)
    actualizado_en = db.Column(db.DateTime, nullable=False, default=ahora, onupdate=ahora)

    rol = db.relationship("Rol", lazy="joined")


class TokenRecuperacion(db.Model):
    """Token de un solo uso para recuperar la contraseña (se guarda su hash)."""
    __tablename__ = "tokens_recuperacion"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    token_hash = db.Column(db.String(64), unique=True, nullable=False)
    expira_en = db.Column(db.DateTime, nullable=False)
    usado = db.Column(db.Boolean, nullable=False, default=False)


class TokenRevocado(db.Model):
    """JWT invalidados por cierre de sesión (lista negra por jti)."""
    __tablename__ = "tokens_revocados"

    jti = db.Column(db.String(36), primary_key=True)
    expira_en = db.Column(db.DateTime, nullable=False)
    revocado_en = db.Column(db.DateTime, nullable=False, default=ahora)
