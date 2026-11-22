"""Datos iniciales de ejemplo de MotoPartes Andina (solo si la base está vacía)."""
from .models import Categoria, ModeloMoto, Producto, db

CATEGORIAS = {
    "Filtros": ["Filtros de aceite", "Filtros de aire"],
    "Frenos": ["Pastillas de freno", "Bandas de freno"],
    "Eléctricos": ["Bujías", "Baterías"],
    "Transmisión": ["Kits de arrastre"],
    "Llantas": [],
}

MODELOS = [
    ("Yamaha", "FZ16", 150, 2011, 2019), ("Yamaha", "FZ25", 250, 2017, None), ("Yamaha", "XTZ125", 125, 2008, None),
    ("Honda", "CB190R", 190, 2016, None), ("Honda", "XR150L", 150, 2015, None),
    ("Bajaj", "Pulsar NS200", 200, 2013, None), ("Suzuki", "GN125", 125, 2000, None), ("AKT", "NKD125", 125, 2010, None),
]

# sku, nombre, subcategoría, unidad, costo, venta, proveedor_id, modelos compatibles
PRODUCTOS = [
    ("FIL-MOT-001", "Filtro de Aceite Yamaha FZ16", "Filtros de aceite", "UNIDAD", 25000, 38000, 1, ["FZ16", "FZ25"]),
    ("FIL-MOT-002", "Filtro de Aceite Honda CB190R", "Filtros de aceite", "UNIDAD", 22000, 34000, 1, ["CB190R", "XR150L"]),
    ("FIL-AIR-001", "Filtro de Aire Pulsar NS200", "Filtros de aire", "UNIDAD", 30000, 45000, 2, ["Pulsar NS200"]),
    ("FRE-PAS-001", "Pastillas de Freno Delanteras FZ", "Pastillas de freno", "PAR", 28000, 42000, 2, ["FZ16", "FZ25"]),
    ("FRE-BAN-001", "Bandas de Freno Traseras GN125", "Bandas de freno", "PAR", 18000, 29000, 3, ["GN125", "NKD125"]),
    ("ELE-BUJ-001", "Bujía NGK CR7HSA", "Bujías", "UNIDAD", 9000, 15000, 3, ["XTZ125", "GN125", "NKD125"]),
    ("ELE-BAT-001", "Batería YTX7L-BS 12V", "Baterías", "UNIDAD", 140000, 195000, 1, ["FZ16", "CB190R", "Pulsar NS200"]),
    ("TRA-KIT-001", "Kit de Arrastre 428 XTZ125", "Kits de arrastre", "KIT", 95000, 140000, 2, ["XTZ125"]),
    ("LLA-DEL-001", "Llanta Delantera 100/80-17", "Llantas", "UNIDAD", 160000, 230000, 3, ["FZ16", "CB190R"]),
]


def sembrar_datos():
    if Producto.query.first():
        return

    categorias = {}
    for principal, hijas in CATEGORIAS.items():
        padre = Categoria(nombre=principal)
        db.session.add(padre)
        categorias[principal] = padre
        for hija in hijas:
            categorias[hija] = Categoria(nombre=hija, padre=padre)
            db.session.add(categorias[hija])

    modelos = {}
    for marca, modelo, cc, desde, hasta in MODELOS:
        modelos[modelo] = ModeloMoto(marca=marca, modelo=modelo, cilindraje=cc, anio_desde=desde, anio_hasta=hasta)
        db.session.add(modelos[modelo])

    for sku, nombre, cat, unidad, costo, venta, proveedor, compatibles in PRODUCTOS:
        producto = Producto(
            codigo_sku=sku, nombre=nombre, categoria=categorias[cat], unidad_medida=unidad,
            precio_costo=costo, precio_venta=venta, proveedor_id=proveedor,
        )
        producto.modelos = [modelos[m] for m in compatibles]
        db.session.add(producto)
    db.session.commit()
