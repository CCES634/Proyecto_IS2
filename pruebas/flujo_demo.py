"""Prueba de humo / guion de la demo en vivo de la Entrega 3.

Recorre el flujo completo del sistema pasando SIEMPRE por el API Gateway:
login -> catálogo -> orden de compra -> recepción (Compras -> Inventario)
-> salida -> traslado -> alertas y dashboard (Reportes -> Inventario + Catálogo)
-> controles de seguridad -> logout.

Uso:
    python pruebas/flujo_demo.py                       # gateway en http://localhost:8000
    python pruebas/flujo_demo.py http://<ip-minikube>:30080
"""
import sys
import uuid

import requests

GATEWAY = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
ADMIN = {"correo": "admin@motopartes.com", "password": "Admin12345"}
fallos = 0


def paso(titulo):
    print(f"\n=== {titulo}")


def verificar(descripcion, respuesta, esperado):
    global fallos
    ok = respuesta.status_code == esperado
    fallos += 0 if ok else 1
    marca = "OK " if ok else "ERR"
    print(f"  [{marca}] {descripcion}: HTTP {respuesta.status_code} (esperado {esperado})")
    if not ok:
        print(f"        {respuesta.text[:300]}")
    return respuesta.json() if respuesta.content and respuesta.headers.get("Content-Type", "").startswith(
        "application/json") else None


def main():
    s = requests.Session()
    sufijo = uuid.uuid4().hex[:4].upper()

    paso("1. Seguridad: sin token el Gateway rechaza la petición")
    verificar("GET productos sin token", s.get(f"{GATEWAY}/api/catalogo/productos"), 401)
    verificar("Token falso", s.get(f"{GATEWAY}/api/catalogo/productos",
                                   headers={"Authorization": "Bearer abc.def.ghi"}), 401)
    verificar("Servicio inexistente", s.get(f"{GATEWAY}/api/facturacion/x"), 404)

    paso("2. Login del administrador (Usuarios y Autenticación)")
    datos = verificar("POST /api/auth/login", s.post(f"{GATEWAY}/api/auth/login", json=ADMIN), 200)
    admin = {"Authorization": f"Bearer {datos['token']}"}
    print(f"  usuario: {datos['usuario']['nombre']} ({datos['usuario']['rol']})")

    paso("3. Crear un operador de bodega y entrar con él")
    correo_op = f"operador{sufijo.lower()}@motopartes.com"
    verificar("POST /api/usuarios/", s.post(f"{GATEWAY}/api/usuarios/", headers=admin, json={
        "nombre": "Operador Demo", "correo": correo_op, "password": "Operador123", "rol": "OPERADOR"}), 201)
    datos = verificar("Login operador", s.post(f"{GATEWAY}/api/auth/login",
                                               json={"correo": correo_op, "password": "Operador123"}), 200)
    operador = {"Authorization": f"Bearer {datos['token']}"}
    verificar("Operador NO puede listar usuarios (rol)", s.get(f"{GATEWAY}/api/usuarios/", headers=operador), 403)

    paso("4. Catálogo: búsqueda y creación de producto")
    datos = verificar("Buscar repuestos compatibles con FZ16",
                      s.get(f"{GATEWAY}/api/catalogo/productos/compatibles", params={"modelo": "FZ16"},
                            headers=operador), 200)
    print(f"  {datos['total_registros']} productos compatibles: {[p['codigo_sku'] for p in datos['data']]}")
    producto = verificar("Crear producto", s.post(f"{GATEWAY}/api/catalogo/productos", headers=admin, json={
        "codigo_sku": f"FRE-PAS-{sufijo}", "nombre": f"Pastillas Freno Pulsar NS200 {sufijo}", "categoria_id": 2,
        "unidad_medida": "PAR", "precio_costo": 26000, "precio_venta": 39000, "proveedor_id": 2}), 201)
    pid = producto["id"]
    verificar("Validación: precio de venta menor al costo",
              s.post(f"{GATEWAY}/api/catalogo/productos", headers=admin, json={
                  "codigo_sku": f"ERR-{sufijo}", "nombre": "Producto inválido", "categoria_id": 2,
                  "precio_costo": 100, "precio_venta": 50}), 422)
    verificar("Configurar stock mínimo (Inventario)",
              s.put(f"{GATEWAY}/api/inventario/umbrales/{pid}", headers=admin, json={"stock_minimo": 10}), 200)

    paso("5. Compras: orden de compra y recepción (Compras -> Inventario)")
    orden = verificar("Crear orden de compra", s.post(f"{GATEWAY}/api/compras/ordenes", headers=admin, json={
        "proveedor_id": 2, "bodega_id": 1, "observacion": "Pedido demo",
        "detalles": [{"producto_id": pid, "cantidad": 30, "costo_unitario": 26000}]}), 201)
    oid = orden["id"]
    print(f"  orden {orden['codigo']} estado={orden['estado']} total={orden['total']}")
    verificar("Recibir orden en BORRADOR (no permitido)", s.post(
        f"{GATEWAY}/api/compras/ordenes/{oid}/recepciones", headers=operador,
        json={"detalles": [{"producto_id": pid, "cantidad": 5}]}), 409)
    verificar("Enviar orden al proveedor", s.patch(f"{GATEWAY}/api/compras/ordenes/{oid}/estado", headers=admin,
                                                   json={"estado": "ENVIADA"}), 200)
    orden = verificar("Recepción parcial (20 de 30)", s.post(
        f"{GATEWAY}/api/compras/ordenes/{oid}/recepciones", headers=operador,
        json={"detalles": [{"producto_id": pid, "cantidad": 20}]}), 201)
    print(f"  estado={orden['estado']} transaccion={orden['recepciones'][-1]['transaccion_inventario']}")

    paso("6. Inventario: salida, traslado y kardex")
    verificar("Salida por venta (contrato Entrega 2)", s.post(
        f"{GATEWAY}/api/inventario/movimientos/salidas", headers=operador,
        json={"comprobante_venta_id": f"FACT-{sufijo}", "bodega_id": 1,
              "detalles": [{"producto_id": pid, "cantidad": 8, "precio_venta_unitario": 39000}]}), 201)
    verificar("Salida mayor al stock (rechazada)", s.post(
        f"{GATEWAY}/api/inventario/movimientos/salidas", headers=operador,
        json={"bodega_id": 1, "detalles": [{"producto_id": pid, "cantidad": 999}]}), 409)
    verificar("Traslado a Bodega Taller", s.post(
        f"{GATEWAY}/api/inventario/movimientos/traslados", headers=operador,
        json={"bodega_origen_id": 1, "bodega_destino_id": 2, "detalles": [{"producto_id": pid, "cantidad": 5}]}), 201)
    stock = verificar("Stock por bodega", s.get(f"{GATEWAY}/api/inventario/existencias/producto/{pid}",
                                                headers=operador), 200)
    print(f"  total={stock['stock_total']} minimo={stock['stock_minimo_configurado']} "
          f"estado={stock['estado_alerta']} desglose={stock['desglose_bodegas']}")
    kardex = verificar("Kardex del producto", s.get(f"{GATEWAY}/api/inventario/kardex",
                                                    params={"producto_id": pid}, headers=operador), 200)
    for fila in reversed(kardex["data"]):
        print(f"    {fila['codigo']:<20} {fila['tipo']:<10} bodega={fila['bodega_id']} "
              f"{fila['cantidad']:+4d} saldo={fila['saldo_resultante']:<4} por {fila['usuario_correo']}")

    paso("7. Reportes y Alertas (Reportes -> Inventario + Catálogo)")
    alertas = verificar("Alertas de stock bajo",
                        s.get(f"{GATEWAY}/api/reportes/alertas/stock-bajo", headers=operador), 200)
    print(f"  resumen={alertas['resumen']}")
    for a in alertas["data"][:5]:
        print(f"    {a['estado_alerta']:<8} {a['codigo_sku']:<14} stock={a['stock_total']} minimo={a['stock_minimo']}")
    dashboard = verificar("Dashboard", s.get(f"{GATEWAY}/api/reportes/dashboard", headers=operador), 200)
    print(f"  valor inventario=${dashboard['valor_total_inventario']:,.0f}  alertas={dashboard['productos_en_alerta']}"
          f"  quiebres={dashboard['quiebres_de_stock']}")

    paso("8. Cierre de sesión")
    verificar("Logout", s.post(f"{GATEWAY}/api/auth/logout", headers=operador), 200)
    verificar("Token revocado ya no sirve", s.get(f"{GATEWAY}/api/catalogo/productos", headers=operador), 401)

    print(f"\nResultado: {'TODO CORRECTO' if fallos == 0 else f'{fallos} verificaciones fallaron'}")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
