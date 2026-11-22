"""Endpoints del servicio de Reportes y Alertas: RF09, RF11 y RF14.

Este servicio no tiene base de datos: compone la información que entregan
Inventario (saldos, umbrales, movimientos) y Catálogo (datos del producto)."""
import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from flask.views import MethodView
from flask_smorest import Blueprint
from marshmallow import Schema, fields, validate

from . import fuentes
from .common import requiere_rol

blp = Blueprint("reportes", __name__, url_prefix="/api/reportes",
                description="Alertas de stock, reportes de inventario y dashboard")


class PaginaArgs(Schema):
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    limit = fields.Integer(load_default=50, validate=validate.Range(min=1, max=500))


class ExistenciasArgs(PaginaArgs):
    bodega_id = fields.Integer()
    categoria = fields.String()


class RotacionArgs(Schema):
    dias = fields.Integer(load_default=30, validate=validate.Range(min=1, max=365))
    top = fields.Integer(load_default=5, validate=validate.Range(min=1, max=50))


def _paginar_lista(elementos, page, limit):
    return {
        "pagina_actual": page,
        "total_paginas": max(1, math.ceil(len(elementos) / limit)),
        "total_registros": len(elementos),
        "data": elementos[(page - 1) * limit: page * limit],
    }


def _info(producto):
    return {k: producto.get(k) for k in ("codigo_sku", "nombre", "categoria")} if producto else {
        "codigo_sku": None, "nombre": "(producto no encontrado en catálogo)", "categoria": None
    }


def _stock_por_producto(bodega_id=None):
    por_producto = defaultdict(lambda: {"stock_total": 0, "desglose_bodegas": []})
    for e in fuentes.existencias():
        if bodega_id and e["bodega_id"] != bodega_id:
            continue
        registro = por_producto[e["producto_id"]]
        registro["stock_total"] += e["cantidad"]
        registro["desglose_bodegas"].append(
            {"bodega_id": e["bodega_id"], "nombre": e["bodega"], "cantidad": e["cantidad"]}
        )
    return por_producto


@blp.route("/alertas/stock-bajo")
class Alertas(MethodView):
    @blp.arguments(PaginaArgs, location="query")
    @blp.response(200)
    @requiere_rol()
    def get(self, args):
        """RF09 - Productos con stock por debajo del umbral mínimo"""
        alertas = fuentes.alertas_inventario(solo_stock_bajo=True)
        catalogo = fuentes.productos([a["producto_id"] for a in alertas])
        prioridad = {"AGOTADO": 0, "CRITICO": 1, "BAJO": 2}
        datos = sorted(
            (
                {
                    "producto_id": a["producto_id"],
                    **_info(catalogo.get(a["producto_id"])),
                    "stock_total": a["stock_total"],
                    "stock_minimo": a["stock_minimo_configurado"],
                    "faltante": max(0, a["stock_minimo_configurado"] - a["stock_total"]),
                    "estado_alerta": a["estado_alerta"],
                    "desglose_bodegas": a["desglose_bodegas"],
                }
                for a in alertas
            ),
            key=lambda x: (prioridad.get(x["estado_alerta"], 9), x["producto_id"]),
        )
        resumen = defaultdict(int)
        for d in datos:
            resumen[d["estado_alerta"]] += 1
        respuesta = _paginar_lista(datos, args["page"], args["limit"])
        respuesta["resumen"] = dict(resumen)
        return respuesta


@blp.route("/existencias")
class Existencias(MethodView):
    @blp.arguments(ExistenciasArgs, location="query")
    @blp.response(200)
    @requiere_rol()
    def get(self, args):
        """RF11 - Existencias actuales por producto (con desglose por bodega)"""
        stock = _stock_por_producto(args.get("bodega_id"))
        catalogo = fuentes.productos(list(stock))
        datos = []
        for producto_id, registro in sorted(stock.items()):
            info = _info(catalogo.get(producto_id))
            if args.get("categoria") and (info["categoria"] or "").lower() != args["categoria"].lower():
                continue
            datos.append({"producto_id": producto_id, **info, **registro})
        return _paginar_lista(datos, args["page"], args["limit"])


def _valorizacion():
    stock = _stock_por_producto()
    catalogo = fuentes.productos(list(stock))
    productos, por_bodega, por_categoria = [], defaultdict(float), defaultdict(float)
    for producto_id, registro in sorted(stock.items()):
        producto = catalogo.get(producto_id) or {}
        costo = float(producto.get("precio_costo") or 0)
        valor = registro["stock_total"] * costo
        productos.append({
            "producto_id": producto_id, **_info(producto or None),
            "stock_total": registro["stock_total"], "precio_costo": costo, "valor": round(valor, 2),
        })
        por_categoria[producto.get("categoria") or "Sin categoría"] += valor
        for d in registro["desglose_bodegas"]:
            por_bodega[d["nombre"]] += d["cantidad"] * costo
    productos.sort(key=lambda p: p["valor"], reverse=True)
    return {
        "valor_total": round(sum(p["valor"] for p in productos), 2),
        "moneda": "COP",
        "por_bodega": {k: round(v, 2) for k, v in por_bodega.items()},
        "por_categoria": {k: round(v, 2) for k, v in sorted(por_categoria.items(), key=lambda x: -x[1])},
        "productos": productos,
    }


@blp.route("/valorizacion")
class Valorizacion(MethodView):
    @blp.response(200)
    @requiere_rol()
    def get(self):
        """RF11 - Valorización del inventario a precio de costo"""
        return _valorizacion()


def _rotacion(dias, top):
    desde = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=dias)
    salidas = {s["producto_id"]: s["cantidad_total"] for s in fuentes.resumen_movimientos("SALIDA", desde)}
    stock = _stock_por_producto()
    catalogo = fuentes.productos()  # todos los productos activos
    filas = []
    for producto_id, producto in catalogo.items():
        vendidas = salidas.get(producto_id, 0)
        actual = stock.get(producto_id, {}).get("stock_total", 0)
        filas.append({
            "producto_id": producto_id, **_info(producto),
            "unidades_salida": vendidas,
            "stock_actual": actual,
            # Índice simple: unidades que salieron por cada unidad en stock durante el periodo
            "indice_rotacion": round(vendidas / actual, 2) if actual else (None if vendidas == 0 else vendidas),
        })
    mayor = sorted(filas, key=lambda f: (-f["unidades_salida"], f["producto_id"]))[:top]
    menor = sorted(filas, key=lambda f: (f["unidades_salida"], -f["stock_actual"]))[:top]
    return {"periodo_dias": dias, "desde": desde.isoformat(), "mayor_rotacion": mayor, "menor_rotacion": menor}


@blp.route("/rotacion")
class Rotacion(MethodView):
    @blp.arguments(RotacionArgs, location="query")
    @blp.response(200)
    @requiere_rol()
    def get(self, args):
        """RF11 - Productos con mayor y menor rotación en el periodo"""
        return _rotacion(args["dias"], args["top"])


@blp.route("/dashboard")
class Dashboard(MethodView):
    @blp.response(200)
    @requiere_rol()
    def get(self):
        """RF14 - Indicadores clave del inventario"""
        valorizacion = _valorizacion()
        alertas = fuentes.alertas_inventario(solo_stock_bajo=True)
        rotacion = _rotacion(30, 5)
        estados = defaultdict(int)
        for a in alertas:
            estados[a["estado_alerta"]] += 1
        con_stock = [p for p in valorizacion["productos"] if p["stock_total"] > 0]
        return {
            "generado_en": datetime.now(timezone.utc).isoformat(),
            "valor_total_inventario": valorizacion["valor_total"],
            "unidades_en_stock": sum(p["stock_total"] for p in con_stock),
            "productos_con_stock": len(con_stock),
            "productos_en_alerta": len(alertas),
            "quiebres_de_stock": estados.get("AGOTADO", 0),
            "alertas_por_estado": dict(estados),
            "valor_por_bodega": valorizacion["por_bodega"],
            "top_mayor_rotacion": rotacion["mayor_rotacion"],
            "top_menor_rotacion": rotacion["menor_rotacion"],
        }
