"""Utilidades comunes del microservicio: logging, manejo de errores,
seguridad basada en los encabezados del API Gateway, salud y paginación.

Cada microservicio tiene su propia copia de este módulo para que pueda
desplegarse de forma independiente (no hay librerías compartidas).
"""
import json
import logging
import math
import sys
import time
import uuid
from functools import wraps

from flask import g, request
from flask_smorest import abort
from marshmallow import Schema, fields, validate
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError


# --------------------------------------------------------------------------
# Logging estructurado (JSON por línea) para que sea consultable con
# `kubectl logs` o `docker compose logs` (RNF10 - Observabilidad).
# --------------------------------------------------------------------------
class FormatoJson(logging.Formatter):
    def __init__(self, servicio):
        super().__init__()
        self.servicio = servicio

    def format(self, record):
        datos = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "nivel": record.levelname,
            "servicio": self.servicio,
            "mensaje": record.getMessage(),
        }
        extra = getattr(record, "datos", None)
        if extra:
            datos.update(extra)
        if record.exc_info:
            datos["excepcion"] = self.formatException(record.exc_info)
        return json.dumps(datos, ensure_ascii=False, default=str)


def configurar_logging(app, servicio):
    manejador = logging.StreamHandler(sys.stdout)
    manejador.setFormatter(FormatoJson(servicio))
    logger = logging.getLogger(servicio)
    logger.handlers = [manejador]
    logger.setLevel(logging.INFO)
    logger.propagate = False
    app.extensions["logger_servicio"] = logger

    @app.before_request
    def _inicio_peticion():
        g.inicio = time.perf_counter()
        g.request_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex[:16]

    @app.after_request
    def _fin_peticion(respuesta):
        if request.path == "/health":
            return respuesta
        duracion = (time.perf_counter() - g.get("inicio", time.perf_counter())) * 1000
        logger.info(
            "peticion",
            extra={"datos": {
                "request_id": g.get("request_id"),
                "metodo": request.method,
                "ruta": request.path,
                "estado": respuesta.status_code,
                "duracion_ms": round(duracion, 2),
                "usuario_id": request.headers.get("X-Usuario-Id"),
            }},
        )
        respuesta.headers["X-Request-Id"] = g.get("request_id", "")
        return respuesta

    return logger


def obtener_logger(app):
    return app.extensions["logger_servicio"]


# --------------------------------------------------------------------------
# Manejo de errores: todas las respuestas de error son JSON con el mismo
# formato que usa flask-smorest: {"code", "status", "message"}.
# --------------------------------------------------------------------------
def registrar_manejo_errores(app, db=None):
    logger = obtener_logger(app)

    if db is not None:
        @app.errorhandler(IntegrityError)
        def _error_integridad(error):
            db.session.rollback()
            logger.warning("violacion de integridad", extra={"datos": {"detalle": str(error.orig)}})
            return {
                "code": 409,
                "status": "Conflict",
                "message": "El registro viola una restricción de unicidad o integridad (posible duplicado).",
            }, 409

    @app.errorhandler(Exception)
    def _error_inesperado(error):
        if db is not None:
            db.session.rollback()
        logger.exception("error no controlado")
        return {
            "code": 500,
            "status": "Internal Server Error",
            "message": "Ocurrió un error interno en el servicio.",
        }, 500


# --------------------------------------------------------------------------
# Seguridad: el API Gateway valida el JWT y reenvía la identidad del
# usuario en encabezados X-Usuario-*. Los servicios solo son accesibles
# dentro de la red interna (ClusterIP en Kubernetes).
# --------------------------------------------------------------------------
ROL_ADMIN = "ADMIN"
ROL_OPERADOR = "OPERADOR"


def usuario_actual():
    usuario_id = request.headers.get("X-Usuario-Id")
    if not usuario_id:
        abort(401, message="Petición sin usuario autenticado. Las peticiones deben pasar por el API Gateway.")
    return {
        "id": int(usuario_id),
        "rol": request.headers.get("X-Usuario-Rol", ""),
        "correo": request.headers.get("X-Usuario-Correo", ""),
    }


def requiere_rol(*roles):
    """Exige un usuario autenticado y, si se indican roles, que tenga alguno de ellos."""
    def decorador(funcion):
        @wraps(funcion)
        def envoltura(*args, **kwargs):
            usuario = usuario_actual()
            if roles and usuario["rol"] not in roles:
                abort(403, message="No tiene permisos para realizar esta operación.")
            return funcion(*args, **kwargs)
        return envoltura
    return decorador


# --------------------------------------------------------------------------
# Salud (usado por las sondas liveness/readiness de Kubernetes)
# --------------------------------------------------------------------------
def registrar_health(app, servicio, db=None):
    @app.get("/health")
    def health():
        if db is not None:
            try:
                db.session.execute(text("SELECT 1"))
            except Exception:  # noqa: BLE001
                return {"estado": "error", "servicio": servicio, "detalle": "sin conexión a la base de datos"}, 503
        return {"estado": "ok", "servicio": servicio}


# --------------------------------------------------------------------------
# Paginación
# --------------------------------------------------------------------------
class PaginacionArgsSchema(Schema):
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    limit = fields.Integer(load_default=20, validate=validate.Range(min=1, max=500))


def paginar(consulta, page, limit):
    total = consulta.order_by(None).count()
    elementos = consulta.limit(limit).offset((page - 1) * limit).all()
    return {
        "pagina_actual": page,
        "total_paginas": max(1, math.ceil(total / limit)),
        "total_registros": total,
        "data": elementos,
    }


def esquema_paginado(esquema_item, nombre):
    """Crea un esquema de respuesta paginada con el formato de los contratos de API."""
    return Schema.from_dict(
        {
            "pagina_actual": fields.Integer(),
            "total_paginas": fields.Integer(),
            "total_registros": fields.Integer(),
            "data": fields.List(fields.Nested(esquema_item)),
        },
        name=nombre,
    )
