import time

from flask import Flask
from flask_smorest import Api
from sqlalchemy.exc import IntegrityError, OperationalError

from .common import configurar_logging, obtener_logger, registrar_health, registrar_manejo_errores
from .config import Config
from .models import db
from .semilla import sembrar_datos


def create_app(config=None):
    app = Flask(__name__)
    app.json.sort_keys = False  # respeta el orden de campos de los contratos
    app.config.from_object(Config)
    if config:
        app.config.update(config)

    configurar_logging(app, app.config["SERVICIO"])
    db.init_app(app)

    api = Api(app)
    from .routes import blp

    api.register_blueprint(blp)
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
            if app.config["DATOS_DEMO"]:
                sembrar_datos()
            logger.info("base de datos lista")
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
