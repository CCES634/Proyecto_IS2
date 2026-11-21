"""Emisión de JWT y utilidades de contraseñas (RNF07)."""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from flask import current_app
from werkzeug.security import check_password_hash, generate_password_hash


def cifrar_password(password):
    # scrypt con sal aleatoria (algoritmo por defecto de Werkzeug 3)
    return generate_password_hash(password)


def verificar_password(password_hash, password):
    return check_password_hash(password_hash, password)


def emitir_token(usuario):
    minutos = current_app.config["JWT_EXPIRACION_MINUTOS"]
    ahora = datetime.now(timezone.utc)
    carga = {
        "sub": str(usuario.id),
        "nombre": usuario.nombre,
        "correo": usuario.correo,
        "rol": usuario.rol.nombre,
        "jti": str(uuid.uuid4()),
        "iat": ahora,
        "exp": ahora + timedelta(minutes=minutos),
    }
    token = jwt.encode(carga, current_app.config["JWT_SECRET"], algorithm=current_app.config["JWT_ALGORITMO"])
    return token, minutos


def generar_token_recuperacion():
    """Devuelve (token_en_claro, hash). En BD solo se guarda el hash."""
    token = secrets.token_urlsafe(32)
    return token, hash_token(token)


def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()
