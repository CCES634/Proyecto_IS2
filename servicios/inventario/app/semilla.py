"""Datos iniciales: bodegas, umbrales y una carga inicial de inventario
registrada en el kardex (solo si la base está vacía).
Los producto_id corresponden a los productos de ejemplo del servicio de Catálogo."""
from .models import Bodega, DetalleMovimiento, Existencia, Movimiento, UmbralStock, ahora, db

BODEGAS = [
    ("BOD-PPAL", "Bodega Principal", "Cra 23 # 45-10, Manizales"),
    ("BOD-TALLER", "Bodega Taller", "Calle 48 # 20-15, Manizales"),
]

# Costo de referencia de los productos de ejemplo (para el costo promedio inicial)
COSTOS = {1: 25000, 2: 22000, 3: 30000, 4: 28000, 5: 18000, 6: 9000, 7: 140000, 8: 95000, 9: 160000}

# producto_id: (stock_minimo, cantidad en Bodega Principal, cantidad en Bodega Taller)
INVENTARIO_INICIAL = {
    1: (10, 2, 1),     # Filtro aceite FZ16 -> CRITICO
    2: (10, 25, 5),
    3: (5, 8, 0),
    4: (8, 6, 1),      # Pastillas FZ -> BAJO
    5: (6, 12, 4),
    6: (20, 60, 15),
    7: (5, 1, 0),      # Batería -> CRITICO
    8: (3, 4, 2),
    9: (4, 0, 0),      # Llanta -> AGOTADO
}


def sembrar_datos():
    if Bodega.query.first():
        return

    bodegas = []
    for codigo, nombre, direccion in BODEGAS:
        bodega = Bodega(codigo=codigo, nombre=nombre, direccion=direccion)
        db.session.add(bodega)
        bodegas.append(bodega)
    db.session.flush()

    movimiento = Movimiento(
        codigo="TEMP", tipo="AJUSTE", bodega_id=bodegas[0].id, observacion="Carga inicial del inventario",
        usuario_id=1, usuario_correo="sistema", fecha=ahora(),
    )
    db.session.add(movimiento)
    db.session.flush()
    movimiento.codigo = f"MOV-AJU-{movimiento.fecha.year}-{movimiento.id:05d}"

    for producto_id, (minimo, *cantidades) in INVENTARIO_INICIAL.items():
        db.session.add(UmbralStock(producto_id=producto_id, stock_minimo=minimo))
        for bodega, cantidad in zip(bodegas, cantidades):
            if cantidad == 0:
                continue
            db.session.add(Existencia(producto_id=producto_id, bodega_id=bodega.id, cantidad=cantidad,
                                      costo_promedio=COSTOS[producto_id]))
            db.session.add(DetalleMovimiento(
                movimiento=movimiento, producto_id=producto_id, bodega_id=bodega.id,
                cantidad=cantidad, saldo_resultante=cantidad, costo_unitario=COSTOS[producto_id],
            ))
    db.session.commit()
