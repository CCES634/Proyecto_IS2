import os


class Config:
    SERVICIO = "usuarios"

    # Base de datos propia del servicio (MySQL en Docker/Kubernetes, SQLite para pruebas locales)
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///usuarios.db")
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT: el mismo secreto lo usa el API Gateway para validar los tokens
    JWT_SECRET = os.getenv("JWT_SECRET", "cambiar-este-secreto-en-produccion")
    JWT_ALGORITMO = "HS256"
    JWT_EXPIRACION_MINUTOS = int(os.getenv("JWT_EXPIRACION_MINUTOS", "60"))
    RECUPERACION_EXPIRACION_MINUTOS = int(os.getenv("RECUPERACION_EXPIRACION_MINUTOS", "30"))

    # En modo demo la recuperación de contraseña devuelve el token en la respuesta
    # (no hay servidor de correo en el alcance del proyecto).
    MODO_DEMO = os.getenv("MODO_DEMO", "true").lower() == "true"

    # Usuario administrador inicial
    ADMIN_NOMBRE = os.getenv("ADMIN_NOMBRE", "Administrador")
    ADMIN_CORREO = os.getenv("ADMIN_CORREO", "admin@motopartes.com")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin12345")

    # Documentación OpenAPI / Swagger (RNF08)
    API_TITLE = "Servicio de Usuarios y Autenticación - MotoPartes Andina"
    API_VERSION = "1.0.0"
    OPENAPI_VERSION = "3.0.3"
    OPENAPI_URL_PREFIX = "/api/usuarios/docs"
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
