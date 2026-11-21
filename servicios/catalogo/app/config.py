import os


class Config:
    SERVICIO = "catalogo"

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///catalogo.db")
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Carga categorías y productos de ejemplo de MotoPartes Andina al iniciar
    DATOS_DEMO = os.getenv("DATOS_DEMO", "true").lower() == "true"

    API_TITLE = "Servicio de Catálogo - MotoPartes Andina"
    API_VERSION = "1.0.0"
    OPENAPI_VERSION = "3.0.3"
    OPENAPI_URL_PREFIX = "/api/catalogo/docs"
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
