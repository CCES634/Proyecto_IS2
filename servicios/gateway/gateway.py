"""API Gateway propio de MotoPartes Andina (RNF09).

Único punto de entrada al sistema. Responsabilidades:
  1. Enrutamiento: /api/<servicio>/... -> microservicio correspondiente.
  2. Autenticación centralizada: valida el JWT (firma, expiración y revocación)
     y reenvía la identidad del usuario en encabezados X-Usuario-*.
  3. Trazabilidad: asigna un X-Request-Id y registra cada petición en formato JSON.
  4. Manejo de fallas: responde 503/504 si un servicio no está disponible o no responde.
"""
import json
import logging
import os
import re
import sys
import threading
import time
import uuid

import jwt
import requests
from flask import Flask, Response, g, jsonify, request
from werkzeug.exceptions import HTTPException

# ----------------------------------------------------------------- configuración
SERVICIOS = {
    "auth": os.getenv("USUARIOS_URL", "http://localhost:5001"),
    "usuarios": os.getenv("USUARIOS_URL", "http://localhost:5001"),
    "catalogo": os.getenv("CATALOGO_URL", "http://localhost:5002"),
    "inventario": os.getenv("INVENTARIO_URL", "http://localhost:5003"),
    "compras": os.getenv("COMPRAS_URL", "http://localhost:5004"),
    "reportes": os.getenv("REPORTES_URL", "http://localhost:5005"),
}
JWT_SECRET = os.getenv("JWT_SECRET", "cambiar-este-secreto-en-produccion")
TIMEOUT_CONEXION = float(os.getenv("TIMEOUT_CONEXION", "2"))
TIMEOUT_RESPUESTA = float(os.getenv("TIMEOUT_RESPUESTA", "20"))
CACHE_REVOCACION_SEGUNDOS = int(os.getenv("CACHE_REVOCACION_SEGUNDOS", "30"))

# Rutas que no requieren token
RUTAS_PUBLICAS = [
    re.compile(r"^/api/auth/(login|recuperar|restablecer)/?$"),
    re.compile(r"^/api/[a-z]+/docs(/.*)?$"),  # Swagger UI y openapi.json de cada servicio
]
METODOS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
# Encabezados que no se reenvían (hop-by-hop o que el Gateway controla)
ENCABEZADOS_EXCLUIDOS_PETICION = {"host", "content-length", "connection", "authorization"}
ENCABEZADOS_EXCLUIDOS_RESPUESTA = {"content-encoding", "content-length", "transfer-encoding", "connection"}

app = Flask(__name__)
app.json.sort_keys = False
sesion = requests.Session()  # reutiliza conexiones HTTP (keep-alive) hacia los servicios
adaptador = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=50)
sesion.mount("http://", adaptador)


# ----------------------------------------------------------------- logging JSON
class FormatoJson(logging.Formatter):
    def format(self, record):
        datos = {"ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"), "nivel": record.levelname,
                 "servicio": "gateway", "mensaje": record.getMessage()}
        datos.update(getattr(record, "datos", {}) or {})
        return json.dumps(datos, ensure_ascii=False)


logger = logging.getLogger("gateway")
_manejador = logging.StreamHandler(sys.stdout)
_manejador.setFormatter(FormatoJson())
logger.handlers = [_manejador]
logger.setLevel(logging.INFO)
logger.propagate = False


def error(codigo, estado, mensaje):
    respuesta = jsonify({"code": codigo, "status": estado, "message": mensaje})
    respuesta.status_code = codigo
    return respuesta


# ----------------------------------------------------- revocación de tokens
class CacheRevocacion:
    """Evita consultar al servicio de usuarios en cada petición."""

    def __init__(self):
        self._datos = {}
        self._lock = threading.Lock()

    def obtener(self, jti):
        with self._lock:
            valor = self._datos.get(jti)
        if valor is None:
            return None
        revocado, momento = valor
        if revocado or time.monotonic() - momento < CACHE_REVOCACION_SEGUNDOS:
            return revocado
        return None

    def guardar(self, jti, revocado):
        with self._lock:
            if len(self._datos) > 10000:
                self._datos.clear()
            self._datos[jti] = (revocado, time.monotonic())


cache_revocacion = CacheRevocacion()


def token_revocado(jti):
    en_cache = cache_revocacion.obtener(jti)
    if en_cache is not None:
        return en_cache
    try:
        r = sesion.get(f"{SERVICIOS['auth']}/internal/tokens-revocados/{jti}", timeout=(TIMEOUT_CONEXION, 3))
        revocado = bool(r.ok and r.json().get("revocado"))
    except requests.RequestException:
        # Decisión de diseño: si Usuarios no responde se acepta el token (firma y
        # expiración ya validadas) para no tumbar todo el sistema. Queda en el log.
        logger.warning("no se pudo verificar revocacion del token", extra={"datos": {"jti": jti}})
        return False
    cache_revocacion.guardar(jti, revocado)
    return revocado


def autenticar():
    """Devuelve (claims, None) o (None, respuesta_de_error)."""
    cabecera = request.headers.get("Authorization", "")
    if not cabecera.startswith("Bearer "):
        return None, error(401, "Unauthorized", "Se requiere un token de acceso (Authorization: Bearer <token>).")
    try:
        claims = jwt.decode(cabecera[7:], JWT_SECRET, algorithms=["HS256"],
                            options={"require": ["exp", "sub", "jti"]})
    except jwt.ExpiredSignatureError:
        return None, error(401, "Unauthorized", "El token expiró. Inicie sesión nuevamente.")
    except jwt.InvalidTokenError:
        return None, error(401, "Unauthorized", "Token inválido.")
    if token_revocado(claims["jti"]):
        return None, error(401, "Unauthorized", "La sesión fue cerrada. Inicie sesión nuevamente.")
    return claims, None


# --------------------------------------------------------------- middleware
@app.before_request
def inicio():
    g.inicio = time.perf_counter()
    g.request_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex[:16]


@app.after_request
def fin(respuesta):
    respuesta.headers["X-Request-Id"] = g.get("request_id", "")
    # CORS básico para una futura interfaz web
    respuesta.headers["Access-Control-Allow-Origin"] = os.getenv("CORS_ORIGEN", "*")
    respuesta.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
    respuesta.headers["Access-Control-Allow-Methods"] = ", ".join(METODOS)
    if request.path != "/health":
        logger.info("peticion", extra={"datos": {
            "request_id": g.get("request_id"),
            "metodo": request.method,
            "ruta": request.path,
            "servicio_destino": g.get("servicio"),
            "estado": respuesta.status_code,
            "duracion_ms": round((time.perf_counter() - g.inicio) * 1000, 2),
            "usuario_id": g.get("usuario_id"),
            "ip": request.headers.get("X-Forwarded-For", request.remote_addr),
        }})
    return respuesta


# ------------------------------------------------------------------- rutas
@app.get("/health")
def health():
    return {"estado": "ok", "servicio": "gateway"}


@app.get("/")
def inicio_gateway():
    return {
        "sistema": "MotoPartes Andina - Sistema de Gestión de Inventarios",
        "documentacion": {nombre: f"/api/{nombre}/docs/" for nombre in
                          ("usuarios", "catalogo", "inventario", "compras", "reportes")},
    }


@app.route("/api/<servicio>", defaults={"ruta": ""}, methods=METODOS)
@app.route("/api/<servicio>/", defaults={"ruta": ""}, methods=METODOS)
@app.route("/api/<servicio>/<path:ruta>", methods=METODOS)
def enrutar(servicio, ruta):
    destino = SERVICIOS.get(servicio)
    if not destino:
        return error(404, "Not Found", f"No existe el servicio '{servicio}'.")
    g.servicio = servicio
    if request.method == "OPTIONS":  # preflight CORS
        return Response(status=204)

    encabezados = {k: v for k, v in request.headers.items()
                   if k.lower() not in ENCABEZADOS_EXCLUIDOS_PETICION and not k.lower().startswith("x-usuario-")
                   and not k.lower().startswith("x-token-")}
    encabezados["X-Request-Id"] = g.request_id
    encabezados["X-Forwarded-For"] = request.headers.get("X-Forwarded-For", request.remote_addr or "")

    if not any(patron.match(request.path) for patron in RUTAS_PUBLICAS):
        claims, respuesta_error = autenticar()
        if respuesta_error:
            return respuesta_error
        g.usuario_id = claims["sub"]
        encabezados.update({
            "X-Usuario-Id": claims["sub"],
            "X-Usuario-Rol": claims.get("rol", ""),
            "X-Usuario-Correo": claims.get("correo", ""),
            "X-Token-Jti": claims["jti"],
            "X-Token-Exp": str(claims["exp"]),
        })

    try:
        respuesta = sesion.request(
            request.method, f"{destino}{request.path}", params=request.args, data=request.get_data(),
            headers=encabezados, timeout=(TIMEOUT_CONEXION, TIMEOUT_RESPUESTA), allow_redirects=False,
        )
    except requests.Timeout:
        return error(504, "Gateway Timeout", f"El servicio '{servicio}' no respondió a tiempo.")
    except requests.ConnectionError:
        logger.error("servicio no disponible", extra={"datos": {"servicio": servicio, "url": destino}})
        return error(503, "Service Unavailable", f"El servicio '{servicio}' no está disponible en este momento.")

    # Al cerrar sesión, el token queda revocado de inmediato en esta réplica
    if request.path.rstrip("/") == "/api/auth/logout" and respuesta.status_code == 200:
        cache_revocacion.guardar(encabezados["X-Token-Jti"], True)

    salida = [(k, v) for k, v in respuesta.headers.items() if k.lower() not in ENCABEZADOS_EXCLUIDOS_RESPUESTA]
    return Response(respuesta.content, status=respuesta.status_code, headers=salida)


@app.errorhandler(404)
def no_encontrado(_):
    return error(404, "Not Found", "Ruta no encontrada. Todas las rutas del sistema inician con /api/.")


@app.errorhandler(Exception)
def error_inesperado(e):
    if isinstance(e, HTTPException):
        return error(e.code, e.name, e.description)
    logger.exception("error no controlado en el gateway")
    return error(500, "Internal Server Error", "Error interno del API Gateway.")
