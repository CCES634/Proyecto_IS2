"""Proveedores de ejemplo de MotoPartes Andina (solo si la base está vacía).
Los ids 1, 2 y 3 coinciden con el proveedor_id de los productos de ejemplo del Catálogo."""
from .models import Proveedor, ProveedorProducto, db

PROVEEDORES = [
    ("900123456-1", "Repuestos Yamaha Colombia S.A.S.", "Carlos Gómez", "6068801234", "ventas@repyamaha.co",
     [(1, 25000), (2, 22000), (7, 140000)]),
    ("901987654-2", "Distribuidora Moto Andes Ltda.", "Laura Ríos", "6068805678", "pedidos@motoandes.co",
     [(3, 30000), (4, 28000), (8, 95000)]),
    ("800456789-3", "Importadora Llantas y Frenos S.A.", "Andrés Patiño", "6043215678", "compras@llantasyfrenos.co",
     [(5, 18000), (6, 9000), (9, 160000)]),
]


def sembrar_datos():
    if Proveedor.query.first():
        return
    for nit, razon, contacto, telefono, correo, productos in PROVEEDORES:
        proveedor = Proveedor(nit=nit, razon_social=razon, contacto=contacto, telefono=telefono, correo=correo,
                              direccion="Manizales, Caldas")
        proveedor.productos = [ProveedorProducto(producto_id=p, costo_referencia=c) for p, c in productos]
        db.session.add(proveedor)
    db.session.commit()
