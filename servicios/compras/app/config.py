import os


class Config:
    SERVICIO = "compras"

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///compras.db")
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Comunicación con Catálogo (validación de productos) e Inventario (recepciones)
    CATALOGO_URL = os.getenv("CATALOGO_URL", "http://localhost:5002")
    INVENTARIO_URL = os.getenv("INVENTARIO_URL", "http://localhost:5003")
    VALIDAR_PRODUCTOS = os.getenv("VALIDAR_PRODUCTOS", "true").lower() == "true"

    # Proveedores de ejemplo
    DATOS_DEMO = os.getenv("DATOS_DEMO", "true").lower() == "true"

    API_TITLE = "Servicio de Compras y Proveedores - MotoPartes Andina"
    API_VERSION = "1.0.0"
    OPENAPI_VERSION = "3.0.3"
    OPENAPI_URL_PREFIX = "/api/compras/docs"
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
