import time

from flask import Flask
from flask_smorest import Api
from sqlalchemy.exc import IntegrityError, OperationalError

from .common import configurar_logging, obtener_logger, registrar_health, registrar_manejo_errores
from .config import Config
from .models import Rol, Usuario, db
from .security import cifrar_password

ROLES_INICIALES = {
    "ADMIN": "Administrador: gestiona usuarios, catálogo, compras y configuración",
    "OPERADOR": "Operador de bodega: registra movimientos y recepciones de mercancía",
}


def create_app(config=None):
    app = Flask(__name__)
    app.json.sort_keys = False  # respeta el orden de campos de los contratos
    app.config.from_object(Config)
    if config:
        app.config.update(config)

    configurar_logging(app, app.config["SERVICIO"])
    db.init_app(app)

    api = Api(app)
    from .routes_auth import blp as auth_blp, interno
    from .routes_usuarios import blp as usuarios_blp

    api.register_blueprint(auth_blp)
    api.register_blueprint(usuarios_blp)
    app.register_blueprint(interno)

    registrar_manejo_errores(app, db)
    registrar_health(app, app.config["SERVICIO"], db)

    with app.app_context():
        inicializar_bd(app)
    return app


def inicializar_bd(app, intentos=30):
    """Crea las tablas y datos iniciales; reintenta mientras MySQL arranca."""
    logger = obtener_logger(app)
    for intento in range(1, intentos + 1):
        try:
            db.create_all()
            sembrar_datos(app)
            logger.info("base de datos lista")
            # Se cierran las conexiones creadas antes de que gunicorn haga fork
            db.session.remove()
            db.engine.dispose()
            return
        except (OperationalError, IntegrityError):
            # OperationalError: MySQL aún no está listo.
            # IntegrityError: otra réplica creó los datos iniciales al mismo tiempo.
            # En ambos casos se espera y se reintenta.
            db.session.rollback()
            logger.warning("base de datos no disponible, reintentando", extra={"datos": {"intento": intento}})
            time.sleep(2)
    raise RuntimeError("No fue posible conectarse a la base de datos")


def sembrar_datos(app):
    for nombre, descripcion in ROLES_INICIALES.items():
        if not Rol.query.filter_by(nombre=nombre).first():
            db.session.add(Rol(nombre=nombre, descripcion=descripcion))
    db.session.commit()

    correo = app.config["ADMIN_CORREO"].lower()
    if not Usuario.query.filter_by(correo=correo).first():
        db.session.add(Usuario(
            nombre=app.config["ADMIN_NOMBRE"],
            correo=correo,
            password_hash=cifrar_password(app.config["ADMIN_PASSWORD"]),
            rol=Rol.query.filter_by(nombre="ADMIN").first(),
        ))
        db.session.commit()
