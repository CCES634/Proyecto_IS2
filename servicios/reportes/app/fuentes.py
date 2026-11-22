"""Consultas a los servicios dueños de los datos (Inventario y Catálogo)."""
from flask import current_app
from flask_smorest import abort

from .clientes import llamar_servicio

LIMITE_PAGINA = 500


def _json(respuesta, servicio):
    if respuesta.status_code != 200:
        abort(502, message=f"El servicio de {servicio} respondió {respuesta.status_code}.")
    return respuesta.json()


def _todas_las_paginas(servicio, url, params):
    datos, pagina = [], 1
    while True:
        cuerpo = _json(
            llamar_servicio(servicio, "GET", url, params={**params, "page": pagina, "limit": LIMITE_PAGINA}),
            servicio,
        )
        datos.extend(cuerpo["data"])
        if pagina >= cuerpo["total_paginas"]:
            return datos
        pagina += 1


def alertas_inventario(solo_stock_bajo=True):
    """Contrato Reportes -> Inventario (Entrega 2)."""
    return _todas_las_paginas(
        "inventario",
        f"{current_app.config['INVENTARIO_URL']}/api/inventario/existencias/alertas",
        {"solo_stock_bajo": str(solo_stock_bajo).lower()},
    )


def existencias():
    return _todas_las_paginas(
        "inventario", f"{current_app.config['INVENTARIO_URL']}/api/inventario/existencias", {"con_stock": "true"}
    )


def resumen_movimientos(tipo, desde=None):
    params = {"tipo": tipo}
    if desde:
        params["desde"] = desde.isoformat()
    return _json(
        llamar_servicio("inventario", "GET",
                        f"{current_app.config['INVENTARIO_URL']}/api/inventario/movimientos/resumen", params=params),
        "inventario",
    )


def productos(ids=None):
    """Contrato Reportes -> Catálogo (Entrega 2). Devuelve dict producto_id -> datos."""
    if ids is not None:
        ids = sorted(set(ids))
        if not ids:
            return {}
        resultado = {}
        for i in range(0, len(ids), LIMITE_PAGINA):
            cuerpo = _json(
                llamar_servicio("catálogo", "POST",
                                f"{current_app.config['CATALOGO_URL']}/api/catalogo/productos/consulta",
                                json={"productos_ids": ids[i:i + LIMITE_PAGINA]}),
                "catálogo",
            )
            resultado.update({p["producto_id"]: p for p in cuerpo["productos"]})
        return resultado

    activos = _todas_las_paginas(
        "catálogo", f"{current_app.config['CATALOGO_URL']}/api/catalogo/productos", {"activo": "true"}
    )
    return {
        p["id"]: {"producto_id": p["id"], **{k: p.get(k) for k in
                  ("codigo_sku", "nombre", "categoria", "precio_costo", "precio_venta", "compatibilidad")}}
        for p in activos
    }
