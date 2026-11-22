"""Pruebas de rendimiento de Manuela Palacio Díaz (MP-01 a MP-11).

Servicios cubiertos: Catálogo, Usuarios y Autenticación, Reportes y Alertas.
Todas las peticiones pasan por el API Gateway (--host apunta al Gateway).

Cada clase de usuario corresponde a un endpoint del plan de la Entrega 2; el
escenario (carga normal, pico, estrés, capacidad) lo define el número de
usuarios y la velocidad de llegada con que se ejecuta (ver ejecutar_pruebas.py).

Ejemplo manual:
    locust -f locustfile.py BusquedaProductos --host http://localhost:8000
"""
import random
import uuid

import requests
from locust import HttpUser, between, events, task

ADMIN = {"correo": "admin@motopartes.com", "password": "Admin12345"}
MODELOS = ["FZ16", "FZ25", "CB190R", "XTZ125", "GN125", "NKD125", "Pulsar", "XR150L"]
BUSQUEDAS = ["filtro", "freno", "bater", "kit", "llanta", "buj", "FIL", "ELE"]

TOKEN = {"valor": None}
SUBCATEGORIAS = []


@events.test_start.add_listener
def preparar(environment, **_):
    """Un solo login al iniciar, para no mezclar el costo del login en las demás pruebas,
    y consulta de las subcategorías existentes para registrar productos válidos."""
    respuesta = requests.post(f"{environment.host}/api/auth/login", json=ADMIN, timeout=30)
    respuesta.raise_for_status()
    TOKEN["valor"] = respuesta.json()["token"]
    categorias = requests.get(f"{environment.host}/api/catalogo/categorias", timeout=30,
                              headers={"Authorization": f"Bearer {TOKEN['valor']}"}).json()
    SUBCATEGORIAS[:] = [c["id"] for c in categorias if c["padre_id"]] or [c["id"] for c in categorias]


class UsuarioAutenticado(HttpUser):
    abstract = True
    wait_time = between(1, 3)  # tiempo de "pensar" de un usuario real

    @property
    def auth(self):
        return {"Authorization": f"Bearer {TOKEN['valor']}"}


# ------------------------------------------------------------ MP-01 / MP-02
class BusquedaProductos(UsuarioAutenticado):
    """GET /api/catalogo/productos — búsqueda y filtrado (RF12)."""

    @task(3)
    def buscar_texto(self):
        self.client.get("/api/catalogo/productos", params={"q": random.choice(BUSQUEDAS)},
                        headers=self.auth, name="GET /api/catalogo/productos?q")

    @task(1)
    def filtrar_categoria(self):
        self.client.get("/api/catalogo/productos", params={"categoria_id": random.randint(1, 5)},
                        headers=self.auth, name="GET /api/catalogo/productos?categoria_id")

    @task(1)
    def filtrar_proveedor(self):
        self.client.get("/api/catalogo/productos", params={"proveedor_id": random.randint(1, 3)},
                        headers=self.auth, name="GET /api/catalogo/productos?proveedor_id")


# ------------------------------------------------------------ MP-03 / MP-04
class Compatibilidad(UsuarioAutenticado):
    """GET /api/catalogo/productos/compatibles — repuestos por modelo de moto (RF15)."""

    @task
    def compatibles(self):
        self.client.get("/api/catalogo/productos/compatibles", params={"modelo": random.choice(MODELOS)},
                        headers=self.auth, name="GET /api/catalogo/productos/compatibles")


# ------------------------------------------------------------------- MP-05
class RegistroProductos(UsuarioAutenticado):
    """POST /api/catalogo/productos — registro con validación (RF01, RNF18)."""

    @task(4)
    def registrar_valido(self):
        sku = f"PRB-{uuid.uuid4().hex[:10].upper()}"
        costo = random.randint(5, 200) * 1000
        self.client.post("/api/catalogo/productos", headers=self.auth, name="POST /api/catalogo/productos", json={
            "codigo_sku": sku, "nombre": f"Producto prueba {sku}", "categoria_id": random.choice(SUBCATEGORIAS),
            "unidad_medida": "UNIDAD", "precio_costo": costo, "precio_venta": costo * 1.4,
            "proveedor_id": random.randint(1, 3), "modelos_ids": random.sample(range(1, 9), 2),
        })

    @task(1)
    def registrar_invalido(self):
        """Debe ser rechazado con 422: se mide que la validación también responde rápido."""
        with self.client.post("/api/catalogo/productos", headers=self.auth, catch_response=True,
                              name="POST /api/catalogo/productos (inválido)",
                              json={"codigo_sku": "x", "nombre": "", "categoria_id": 1,
                                    "precio_costo": 100, "precio_venta": 50}) as r:
            if r.status_code == 422:
                r.success()
            else:
                r.failure(f"se esperaba 422 y llegó {r.status_code}")


# ------------------------------------------------------------------- MP-06
class ConsultaLote(UsuarioAutenticado):
    """POST /api/catalogo/productos/consulta — consulta por lote (contrato Reportes -> Catálogo)."""

    @task
    def consulta(self):
        self.client.post("/api/catalogo/productos/consulta", headers=self.auth,
                         name="POST /api/catalogo/productos/consulta",
                         json={"productos_ids": random.sample(range(1, 10), random.randint(3, 9))})


# ------------------------------------------------------------ MP-07/08/09
class Login(HttpUser):
    """POST /api/auth/login — inicio de sesión (contraseñas cifradas con scrypt)."""
    wait_time = between(1, 3)

    @task
    def login(self):
        self.client.post("/api/auth/login", json=ADMIN, name="POST /api/auth/login")


# ------------------------------------------------------------------- MP-10
class ReporteAlertas(UsuarioAutenticado):
    """GET /api/reportes/alertas/stock-bajo — Reportes consulta Inventario y Catálogo."""

    @task
    def alertas(self):
        self.client.get("/api/reportes/alertas/stock-bajo", headers=self.auth,
                        name="GET /api/reportes/alertas/stock-bajo")


# ------------------------------------------------------------------- MP-11
class Dashboard(UsuarioAutenticado):
    """GET /api/reportes/dashboard — el reporte más costoso (varias consultas encadenadas)."""

    @task
    def dashboard(self):
        self.client.get("/api/reportes/dashboard", headers=self.auth, name="GET /api/reportes/dashboard")
