import os


class Config:
    SERVICIO = "inventario"

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///inventario.db")
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Comunicación con el servicio de Catálogo (validación de productos)
    CATALOGO_URL = os.getenv("CATALOGO_URL", "http://localhost:5002")
    VALIDAR_PRODUCTOS = os.getenv("VALIDAR_PRODUCTOS", "true").lower() == "true"

    # Bodegas, umbrales y saldos de ejemplo
    DATOS_DEMO = os.getenv("DATOS_DEMO", "true").lower() == "true"

    API_TITLE = "Servicio de Inventario - MotoPartes Andina"
    API_VERSION = "1.0.0"
    OPENAPI_VERSION = "3.0.3"
    OPENAPI_URL_PREFIX = "/api/inventario/docs"
    OPENAPI_SWAGGER_UI_PATH = "/"
    OPENAPI_SWAGGER_UI_URL = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"
    API_SPEC_OPTIONS = {
        "components": {
            "securitySchemes": {
                "bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
            }
        },
        "security": [{"bearerAuth": []}],
    }
