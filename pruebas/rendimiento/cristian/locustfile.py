import logging
import os
from collections import deque
from time import perf_counter
from uuid import uuid4

import requests
from locust import HttpUser, between, events, task
from locust.exception import StopUser


logger = logging.getLogger(__name__)

INVENTARIO = "/api/inventario"
COMPRAS = "/api/compras"
CATALOGO = "/api/catalogo"

EXISTENCIAS = f"{INVENTARIO}/existencias"
ENTRADAS = f"{INVENTARIO}/movimientos/entradas"
SALIDAS = f"{INVENTARIO}/movimientos/salidas"
TRASLADOS = f"{INVENTARIO}/movimientos/traslados"
KARDEX = f"{INVENTARIO}/kardex"
ORDENES = f"{COMPRAS}/ordenes"

BODEGA_ORIGEN = 1
BODEGA_DESTINO = 2
CATEGORIA_ID = 2
PROVEEDOR_ID = 2
COSTO = 26000
PRECIO_VENTA = 39000
STOCK_NORMAL = 100000
STOCK_LIMITADO = 30
TIMEOUT = 30


def detalle(producto_id, cantidad=1, **campos):
    return {"producto_id": producto_id, "cantidad": cantidad, **campos}


def datos_entrada(producto_id, cantidad=1):
    return {
        "bodega_id": BODEGA_ORIGEN,
        "detalles": [detalle(producto_id, cantidad, costo_unitario=COSTO)],
    }


def datos_orden(producto_id):
    return {
        "proveedor_id": PROVEEDOR_ID,
        "bodega_id": BODEGA_ORIGEN,
        "observacion": "Prueba de rendimiento Cristian",
        "detalles": [detalle(producto_id, costo_unitario=COSTO)],
    }


class Corrida:
    def __init__(self, host):
        self.host = host.rstrip("/")
        self.headers = {}
        self.producto_id = None
        self.ordenes_pendientes = deque()
        self.salidas_aceptadas = 0
        self.salidas_rechazadas_por_stock = 0
        self.recepciones_confirmadas = 0

    def solicitar(self, metodo, ruta, esperado, **opciones):
        """Preparación y verificaciones fuera de las métricas de Locust."""
        respuesta = requests.request(
            metodo,
            f"{self.host}{ruta}",
            headers=self.headers,
            timeout=TIMEOUT,
            **opciones,
        )
        if respuesta.status_code != esperado:
            raise RuntimeError(
                f"{metodo} {ruta}: HTTP {respuesta.status_code}; "
                f"se esperaba {esperado}. {respuesta.text[:300]}"
            )
        return respuesta.json()

    def autenticar(self):
        credenciales = {
            "correo": os.getenv("LOCUST_ADMIN_CORREO", "admin@motopartes.com"),
            "password": os.getenv("LOCUST_ADMIN_PASSWORD", "Admin12345"),
        }
        datos = self.solicitar("POST", "/api/auth/login", 200, json=credenciales)
        self.headers["Authorization"] = f"Bearer {datos['token']}"

    def crear_producto(self):
        sufijo = uuid4().hex[:10].upper()
        producto = self.solicitar(
            "POST",
            f"{CATALOGO}/productos",
            201,
            json={
                "codigo_sku": f"LOC-CE-{sufijo}",
                "nombre": f"Producto Locust Cristian {sufijo}",
                "categoria_id": CATEGORIA_ID,
                "unidad_medida": "PAR",
                "precio_costo": COSTO,
                "precio_venta": PRECIO_VENTA,
                "proveedor_id": PROVEEDOR_ID,
            },
        )
        self.producto_id = producto["id"]

    def cargar_stock(self, cantidad):
        self.solicitar(
            "POST", ENTRADAS, 201, json=datos_entrada(self.producto_id, cantidad)
        )

    def preparar_ordenes(self):
        cantidad = int(os.getenv("LOCUST_TOTAL_ORDENES", "200"))
        if cantidad < 1:
            raise ValueError("LOCUST_TOTAL_ORDENES debe ser mayor que cero")

        for _ in range(cantidad):
            orden = self.solicitar(
                "POST", ORDENES, 201, json=datos_orden(self.producto_id)
            )
            orden_id = orden["id"]
            self.solicitar(
                "PATCH",
                f"{ORDENES}/{orden_id}/estado",
                200,
                json={"estado": "ENVIADA"},
            )
            self.ordenes_pendientes.append(orden_id)

    def stock_en_origen(self):
        datos = self.solicitar(
            "GET",
            EXISTENCIAS,
            200,
            params={"producto_id": self.producto_id, "bodega_id": BODEGA_ORIGEN},
        )
        return sum(fila["cantidad"] for fila in datos["data"])


@events.test_start.add_listener
def preparar_corrida(environment, **_):
    environment.corrida_ce = None
    clases = environment.user_classes

    try:
        if len(clases) != 1:
            raise ValueError("Selecciona una sola clase, de CE01 a CE11")
        if not environment.host:
            raise ValueError("Indica la URL del API Gateway con --host")

        escenario = clases[0]
        corrida = Corrida(environment.host)
        corrida.autenticar()

        if escenario.requiere_producto:
            corrida.crear_producto()
        if escenario.stock_inicial:
            corrida.cargar_stock(escenario.stock_inicial)
        if escenario.prepara_recepciones:
            corrida.preparar_ordenes()

        environment.corrida_ce = corrida
    except (requests.RequestException, RuntimeError, ValueError, KeyError):
        logger.exception("No se pudo preparar la corrida de Cristian")
        environment.process_exit_code = 1


@events.test_stop.add_listener
def verificar_corrida(environment, **_):
    corrida = getattr(environment, "corrida_ce", None)
    if corrida is None:
        return

    escenario = environment.user_classes[0].__name__

    try:
        if escenario in {"CE04", "CE05"}:
            saldo = corrida.stock_en_origen()
            aceptadas = corrida.salidas_aceptadas
            rechazadas = corrida.salidas_rechazadas_por_stock
            esperado = environment.user_classes[0].stock_inicial - aceptadas
            logger.info(
                "%s: salidas aceptadas=%s, rechazos por stock=%s, saldo final=%s",
                escenario, aceptadas, rechazadas, saldo,
            )

            if aceptadas == 0 or saldo < 0 or saldo != esperado:
                raise RuntimeError(
                    f"{escenario}: saldo obtenido {saldo}, esperado {esperado}"
                )
            if escenario == "CE05" and (saldo != 0 or rechazadas == 0):
                raise RuntimeError("CE-05: la carga no ejercitó el rechazo por stock")

        if escenario == "CE10":
            saldo = corrida.stock_en_origen()
            confirmadas = corrida.recepciones_confirmadas
            logger.info(
                "CE-10: recepciones confirmadas=%s, órdenes sin usar=%s, stock=%s",
                confirmadas, len(corrida.ordenes_pendientes), saldo,
            )
            if confirmadas == 0 or saldo != confirmadas:
                raise RuntimeError(
                    f"CE-10: stock obtenido {saldo}, esperado {confirmadas}"
                )
    except (requests.RequestException, RuntimeError, ValueError, KeyError):
        logger.exception("Falló la verificación final de %s", escenario)
        environment.process_exit_code = 1


class UsuarioCristian(HttpUser):
    abstract = True
    wait_time = between(1, 3)

    requiere_producto = False
    stock_inicial = 0
    prepara_recepciones = False

    def on_start(self):
        self.corrida = getattr(self.environment, "corrida_ce", None)
        if self.corrida is None:
            raise StopUser()
        self.client.headers.update(self.corrida.headers)

    def consultar_pagina(self, ruta, params=None, limite_segundos=None):
        inicio = perf_counter()
        with self.client.get(
            ruta, params=params, timeout=TIMEOUT, catch_response=True
        ) as respuesta:
            duracion = perf_counter() - inicio
            if respuesta.status_code != 200:
                respuesta.failure(f"Se esperaba HTTP 200, recibido {respuesta.status_code}")
                return

            try:
                datos = respuesta.json()["data"]
            except (ValueError, KeyError, TypeError):
                respuesta.failure("Respuesta paginada inválida")
                return

            if not isinstance(datos, list):
                respuesta.failure("El campo data debe ser una lista")
            elif limite_segundos is not None and duracion >= limite_segundos:
                respuesta.failure("La consulta de existencias tardó 2 s o más")

    def registrar_movimiento(self, ruta, datos):
        with self.client.post(
            ruta, json=datos, timeout=TIMEOUT, catch_response=True
        ) as respuesta:
            if respuesta.status_code != 201:
                respuesta.failure(f"Se esperaba HTTP 201, recibido {respuesta.status_code}")
                return False
            try:
                transaccion = respuesta.json().get("transaccion_id")
            except (ValueError, AttributeError):
                transaccion = None
            if not transaccion:
                respuesta.failure("Movimiento sin identificador de transacción")
                return False
            return True

    def registrar_salida(self, permitir_agotamiento=False):
        datos = {
            "comprobante_venta_id": f"CE-{uuid4().hex}",
            "bodega_id": BODEGA_ORIGEN,
            "detalles": [
                detalle(self.corrida.producto_id, precio_venta_unitario=PRECIO_VENTA)
            ],
        }

        if not permitir_agotamiento:
            if self.registrar_movimiento(SALIDAS, datos):
                self.corrida.salidas_aceptadas += 1
            return

        with self.client.post(
            SALIDAS,
            json=datos,
            name=f"{SALIDAS} [stock limitado]",
            timeout=TIMEOUT,
            catch_response=True,
        ) as respuesta:
            if respuesta.status_code in (201, 409):
                try:
                    cuerpo = respuesta.json()
                except ValueError:
                    respuesta.failure("La respuesta de la salida no contiene JSON válido")
                    return

                if respuesta.status_code == 201 and cuerpo.get("transaccion_id"):
                    self.corrida.salidas_aceptadas += 1
                    return

                if (
                    respuesta.status_code == 409
                    and str(cuerpo.get("message", "")).startswith("Stock insuficiente")
                ):
                    self.corrida.salidas_rechazadas_por_stock += 1
                    respuesta.success()
                    return

            respuesta.failure(f"Resultado inesperado de la salida: HTTP {respuesta.status_code}")


class CE01(UsuarioCristian):
    """Carga normal: consultar existencias por bodega en menos de 2 s."""

    @task
    def existencias(self):
        self.consultar_pagina(
            EXISTENCIAS, {"bodega_id": BODEGA_ORIGEN}, limite_segundos=2
        )


class CE02(UsuarioCristian):
    """Carga pico: consultar existencias con 200 usuarios."""

    @task
    def existencias(self):
        self.consultar_pagina(EXISTENCIAS, {"bodega_id": BODEGA_ORIGEN})


class CE03(UsuarioCristian):
    """Capacidad: medir el límite de usuarios de la consulta de existencias."""

    @task
    def existencias(self):
        self.consultar_pagina(EXISTENCIAS, {"bodega_id": BODEGA_ORIGEN})


class CE04(UsuarioCristian):
    """Carga normal: registrar salidas y comprobar el saldo final."""

    requiere_producto = True
    stock_inicial = STOCK_NORMAL

    @task
    def salida(self):
        self.registrar_salida()


class CE05(UsuarioCristian):
    """Carga pico: agotar un stock compartido sin dejarlo en negativo."""

    requiere_producto = True
    stock_inicial = STOCK_LIMITADO

    @task
    def salida_concurrente(self):
        self.registrar_salida(permitir_agotamiento=True)


class CE06(UsuarioCristian):
    """Estrés: aumentar la carga hasta encontrar el límite de las entradas."""

    requiere_producto = True

    @task
    def entrada(self):
        self.registrar_movimiento(ENTRADAS, datos_entrada(self.corrida.producto_id))


class CE07(UsuarioCristian):
    """Carga normal: medir el tiempo para trasladar unidades entre bodegas."""

    requiere_producto = True
    stock_inicial = STOCK_NORMAL

    @task
    def traslado(self):
        self.registrar_movimiento(
            TRASLADOS,
            {
                "bodega_origen_id": BODEGA_ORIGEN,
                "bodega_destino_id": BODEGA_DESTINO,
                "detalles": [detalle(self.corrida.producto_id)],
            },
        )


class CE08(UsuarioCristian):
    """Carga normal: consultar el kardex de un producto con movimiento previo."""

    requiere_producto = True
    stock_inicial = 1

    @task
    def kardex(self):
        self.consultar_pagina(KARDEX, {"producto_id": self.corrida.producto_id})


class CE09(UsuarioCristian):
    """Carga normal: crear órdenes de compra."""

    requiere_producto = True

    @task
    def crear_orden(self):
        with self.client.post(
            ORDENES,
            json=datos_orden(self.corrida.producto_id),
            timeout=TIMEOUT,
            catch_response=True,
        ) as respuesta:
            if respuesta.status_code != 201:
                respuesta.failure(f"Se esperaba HTTP 201, recibido {respuesta.status_code}")
                return
            try:
                orden_id = respuesta.json().get("id")
            except (ValueError, AttributeError):
                orden_id = None
            if not orden_id:
                respuesta.failure("La orden creada no tiene identificador")


class CE10(UsuarioCristian):
    """Carga pico: recibir órdenes e identificar el registro en Inventario."""

    requiere_producto = True
    prepara_recepciones = True

    @task
    def recibir_orden(self):
        try:
            orden_id = self.corrida.ordenes_pendientes.popleft()
        except IndexError:
            raise StopUser() from None

        with self.client.post(
            f"{ORDENES}/{orden_id}/recepciones",
            name=f"{ORDENES}/{{id}}/recepciones",
            json={"detalles": [detalle(self.corrida.producto_id)]},
            timeout=TIMEOUT,
            catch_response=True,
        ) as respuesta:
            if respuesta.status_code != 201:
                respuesta.failure(f"Se esperaba HTTP 201, recibido {respuesta.status_code}")
                return

            try:
                orden = respuesta.json()
                recepcion = orden["recepciones"][-1]
                if orden["estado"] != "RECIBIDA" or not recepcion["transaccion_inventario"]:
                    respuesta.failure("La orden no quedó recibida con transacción de Inventario")
                    return
            except (ValueError, KeyError, IndexError, TypeError):
                respuesta.failure("Respuesta de recepción incompleta")
                return

            self.corrida.recepciones_confirmadas += 1


class CE11(UsuarioCristian):
    """Estrés: mezclar tráfico de lectura y escritura a través del Gateway."""

    requiere_producto = True
    stock_inicial = 1

    @task(5)
    def existencias(self):
        self.consultar_pagina(EXISTENCIAS, {"bodega_id": BODEGA_ORIGEN})

    @task(2)
    def kardex(self):
        self.consultar_pagina(KARDEX, {"producto_id": self.corrida.producto_id})

    @task(2)
    def ordenes(self):
        self.consultar_pagina(ORDENES)

    @task(1)
    def entrada(self):
        self.registrar_movimiento(ENTRADAS, datos_entrada(self.corrida.producto_id))