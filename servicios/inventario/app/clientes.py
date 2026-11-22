"""Cliente HTTP para comunicación síncrona (REST) con otros microservicios.

Las llamadas entre servicios van directo por la red interna (Service de
Kubernetes / red de Docker), no por el Gateway, y reenvían la identidad del
usuario y el X-Request-Id para mantener la trazabilidad en los logs.
"""
import requests
from flask import g, request
from flask_smorest import abort

_sesion = requests.Session()
ENCABEZADOS_PROPAGADOS = ("X-Usuario-Id", "X-Usuario-Rol", "X-Usuario-Correo")


def llamar_servicio(nombre, metodo, url, **kwargs):
    encabezados = {k: request.headers[k] for k in ENCABEZADOS_PROPAGADOS if k in request.headers}
    encabezados["X-Request-Id"] = g.get("request_id", "")
    try:
        respuesta = _sesion.request(metodo, url, headers=encabezados, timeout=(2, 10), **kwargs)
    except requests.Timeout:
        abort(504, message=f"El servicio de {nombre} no respondió a tiempo.")
    except requests.ConnectionError:
        abort(503, message=f"El servicio de {nombre} no está disponible en este momento.")
    if respuesta.status_code >= 500:
        abort(502, message=f"El servicio de {nombre} respondió con un error ({respuesta.status_code}).")
    return respuesta
