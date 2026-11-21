import os


class Config:
    SERVICIO = "reportes"

    # Reportes y Alertas no tiene base de datos propia: consulta Inventario y Catálogo
    INVENTARIO_URL = os.getenv("INVENTARIO_URL", "http://localhost:5003")
    CATALOGO_URL = os.getenv("CATALOGO_URL", "http://localhost:5002")

    API_TITLE = "Servicio de Reportes y Alertas - MotoPartes Andina"
    API_VERSION = "1.0.0"
    OPENAPI_VERSION = "3.0.3"
    OPENAPI_URL_PREFIX = "/api/reportes/docs"
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
