from flask import Flask
from flask_smorest import Api

from .common import configurar_logging, registrar_health, registrar_manejo_errores
from .config import Config


def create_app(config=None):
    app = Flask(__name__)
    app.json.sort_keys = False  # respeta el orden de campos de los contratos
    app.config.from_object(Config)
    if config:
        app.config.update(config)

    configurar_logging(app, app.config["SERVICIO"])

    api = Api(app)
    from .routes import blp

    api.register_blueprint(blp)
    registrar_manejo_errores(app)
    registrar_health(app, app.config["SERVICIO"])
    return app
