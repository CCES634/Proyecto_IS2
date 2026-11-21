"""Endpoints del servicio de Inventario: RF04, RF05, RF09, RF10 y RF13."""
import math
from collections import defaultdict

from flask.views import MethodView
from flask_smorest import Blueprint, abort
from sqlalchemy import func

from .common import ROL_ADMIN, ROL_OPERADOR, esquema_paginado, paginar, requiere_rol
from .models import Bodega, DetalleMovimiento, Existencia, Movimiento, UmbralStock, db
from .schemas import (
    AjusteSchema,
    AlertaFiltroSchema,
    AlertasRespuestaSchema,
    BodegaActualizarSchema,
    BodegaSchema,
    DevolucionSchema,
    EntradaSchema,
    ExistenciaFiltroSchema,
    ExistenciaSchema,
    KardexFiltroSchema,
    KardexSchema,
    MovimientoRespuestaSchema,
    MovimientoSchema,
    ResumenFiltroSchema,
    ResumenItemSchema,
    SalidaSchema,
    StockProductoSchema,
    TrasladoSchema,
    UmbralSchema,
)
from .stock import bodega_activa, registrar_movimiento, saldo_actual, stock_de_producto, validar_productos

blp = Blueprint("inventario", __name__, url_prefix="/api/inventario",
                description="Bodegas, existencias, movimientos y kardex")

ExistenciasPaginadasSchema = esquema_paginado(ExistenciaSchema, "ExistenciasPaginadas")
KardexPaginadoSchema = esquema_paginado(KardexSchema, "KardexPaginado")
OPERADORES = (ROL_ADMIN, ROL_OPERADOR)


def _respuesta(movimiento, mensaje):
    return {"transaccion_id": movimiento.codigo, "mensaje": mensaje, "fecha_registro": movimiento.fecha}


def _sin_repetidos(detalles):
    ids = [d["producto_id"] for d in detalles]
    if len(ids) != len(set(ids)):
        abort(422, message="Un producto no puede repetirse en el mismo movimiento.")
    return ids


# ------------------------------------------------------------------ bodegas
@blp.route("/bodegas")
class Bodegas(MethodView):
    @blp.response(200, BodegaSchema(many=True))
    @requiere_rol()
    def get(self):
        """Lista las bodegas"""
        return Bodega.query.order_by(Bodega.id).all()

    @blp.arguments(BodegaSchema)
    @blp.response(201, BodegaSchema)
    @requiere_rol(ROL_ADMIN)
    def post(self, datos):
        """Crea una bodega"""
        if Bodega.query.filter_by(codigo=datos["codigo"]).first():
            abort(409, message="Ya existe una bodega con ese código.")
        bodega = Bodega(**datos)
        db.session.add(bodega)
        db.session.commit()
        return bodega


@blp.route("/bodegas/<int:bodega_id>")
class BodegaPorId(MethodView):
    @blp.response(200, BodegaSchema)
    @requiere_rol()
    def get(self, bodega_id):
        """Consulta una bodega"""
        bodega = db.session.get(Bodega, bodega_id)
        if not bodega:
            abort(404, message="Bodega no encontrada.")
        return bodega

    @blp.arguments(BodegaActualizarSchema)
    @blp.response(200, BodegaSchema)
    @requiere_rol(ROL_ADMIN)
    def put(self, datos, bodega_id):
        """Actualiza o desactiva una bodega"""
        bodega = db.session.get(Bodega, bodega_id)
        if not bodega:
            abort(404, message="Bodega no encontrada.")
        if datos.get("activa") is False:
            con_stock = Existencia.query.filter(Existencia.bodega_id == bodega_id, Existencia.cantidad > 0).first()
            if con_stock:
                abort(409, message="No se puede desactivar una bodega con existencias. Trasládelas primero.")
        for campo, valor in datos.items():
            setattr(bodega, campo, valor)
        db.session.commit()
        return bodega


# -------------------------------------------------------------- existencias
@blp.route("/existencias")
class Existencias(MethodView):
    @blp.arguments(ExistenciaFiltroSchema, location="query")
    @blp.response(200, ExistenciasPaginadasSchema)
    @requiere_rol()
    def get(self, filtros):
        """Consulta saldos por producto y/o bodega"""
        consulta = Existencia.query
        if "producto_id" in filtros:
            consulta = consulta.filter_by(producto_id=filtros["producto_id"])
        if "bodega_id" in filtros:
            consulta = consulta.filter_by(bodega_id=filtros["bodega_id"])
        if filtros.get("con_stock"):
            consulta = consulta.filter(Existencia.cantidad > 0)
        consulta = consulta.order_by(Existencia.producto_id, Existencia.bodega_id)
        return paginar(consulta, filtros["page"], filtros["limit"])


@blp.route("/existencias/producto/<int:producto_id>")
class StockProducto(MethodView):
    @blp.response(200, StockProductoSchema)
    @requiere_rol()
    def get(self, producto_id):
        """Stock total de un producto y su desglose por bodega"""
        return stock_de_producto(producto_id)


@blp.route("/existencias/alertas")
class Alertas(MethodView):
    @blp.arguments(AlertaFiltroSchema, location="query")
    @blp.response(200, AlertasRespuestaSchema)
    @requiere_rol()
    def get(self, filtros):
        """Existencias frente al umbral mínimo (contrato Reportes -> Inventario)"""
        umbrales = {u.producto_id: u.stock_minimo for u in UmbralStock.query.all()}
        por_producto = defaultdict(list)
        for existencia in Existencia.query.filter(Existencia.producto_id.in_(list(umbrales))).all():
            por_producto[existencia.producto_id].append(existencia)

        resultados = [
            stock_de_producto(pid, por_producto[pid], minimo) for pid, minimo in sorted(umbrales.items())
        ]
        if filtros["solo_stock_bajo"]:
            resultados = [r for r in resultados if r["estado_alerta"] in ("AGOTADO", "CRITICO", "BAJO")]

        page, limit = filtros["page"], filtros["limit"]
        return {
            "pagina_actual": page,
            "total_paginas": max(1, math.ceil(len(resultados) / limit)),
            "total_registros": len(resultados),
            "data": resultados[(page - 1) * limit: page * limit],
        }


@blp.route("/umbrales")
class Umbrales(MethodView):
    @blp.response(200, UmbralSchema(many=True))
    @requiere_rol()
    def get(self):
        """Lista los umbrales de stock mínimo configurados"""
        return UmbralStock.query.order_by(UmbralStock.producto_id).all()


@blp.route("/umbrales/<int:producto_id>")
class UmbralPorProducto(MethodView):
    @blp.arguments(UmbralSchema)
    @blp.response(200, UmbralSchema)
    @requiere_rol(ROL_ADMIN)
    def put(self, datos, producto_id):
        """Configura el stock mínimo de un producto (RF09)"""
        validar_productos([producto_id])
        umbral = db.session.get(UmbralStock, producto_id) or UmbralStock(producto_id=producto_id)
        umbral.stock_minimo = datos["stock_minimo"]
        db.session.add(umbral)
        db.session.commit()
        return umbral


# -------------------------------------------------------------- movimientos
@blp.route("/movimientos/entradas")
class Entradas(MethodView):
    @blp.arguments(EntradaSchema)
    @blp.response(201, MovimientoRespuestaSchema)
    @requiere_rol(*OPERADORES)
    def post(self, datos):
        """Registra una entrada de mercancía (compras, recepciones)"""
        validar_productos(_sin_repetidos(datos["detalles"]))
        bodega_activa(datos["bodega_id"])
        lineas = [
            {"producto_id": d["producto_id"], "bodega_id": datos["bodega_id"], "cantidad": d["cantidad"],
             "costo_unitario": d.get("costo_unitario")}
            for d in datos["detalles"]
        ]
        referencia = f"OC-{datos['orden_compra_id']}" if datos.get("orden_compra_id") else None
        movimiento = registrar_movimiento(
            "ENTRADA", datos["bodega_id"], lineas, referencia=referencia,
            proveedor_id=datos.get("proveedor_id"), observacion=datos["observacion"],
        )
        return _respuesta(movimiento, "Entrada de inventario registrada y stock actualizado correctamente")


@blp.route("/movimientos/salidas")
class Salidas(MethodView):
    @blp.arguments(SalidaSchema)
    @blp.response(201, MovimientoRespuestaSchema)
    @requiere_rol(*OPERADORES)
    def post(self, datos):
        """Registra una salida de mercancía (ventas, despachos)"""
        validar_productos(_sin_repetidos(datos["detalles"]), exigir_activos=False)
        bodega_activa(datos["bodega_id"])
        lineas = [
            {"producto_id": d["producto_id"], "bodega_id": datos["bodega_id"], "cantidad": -d["cantidad"],
             "precio_unitario": d.get("precio_venta_unitario")}
            for d in datos["detalles"]
        ]
        movimiento = registrar_movimiento(
            "SALIDA", datos["bodega_id"], lineas, referencia=datos.get("comprobante_venta_id"),
            observacion=datos["observacion"],
        )
        return _respuesta(movimiento, "Salida de inventario registrada y stock actualizado correctamente")


@blp.route("/movimientos/ajustes")
class Ajustes(MethodView):
    @blp.arguments(AjusteSchema)
    @blp.response(201, MovimientoRespuestaSchema)
    @requiere_rol(ROL_ADMIN)
    def post(self, datos):
        """Ajusta el saldo según el conteo físico (solo administradores)"""
        validar_productos(_sin_repetidos(datos["detalles"]), exigir_activos=False)
        bodega_activa(datos["bodega_id"])
        lineas = []
        for d in datos["detalles"]:
            diferencia = d["cantidad_contada"] - saldo_actual(d["producto_id"], datos["bodega_id"])
            if diferencia != 0:
                lineas.append({"producto_id": d["producto_id"], "bodega_id": datos["bodega_id"],
                               "cantidad": diferencia})
        if not lineas:
            abort(422, message="El conteo coincide con el saldo registrado; no hay nada que ajustar.")
        movimiento = registrar_movimiento("AJUSTE", datos["bodega_id"], lineas, observacion=datos["observacion"])
        return _respuesta(movimiento, "Ajuste de inventario registrado correctamente")


@blp.route("/movimientos/traslados")
class Traslados(MethodView):
    @blp.arguments(TrasladoSchema)
    @blp.response(201, MovimientoRespuestaSchema)
    @requiere_rol(*OPERADORES)
    def post(self, datos):
        """Traslada mercancía entre bodegas"""
        validar_productos(_sin_repetidos(datos["detalles"]), exigir_activos=False)
        origen = bodega_activa(datos["bodega_origen_id"]).id
        destino = bodega_activa(datos["bodega_destino_id"]).id
        lineas = []
        for d in datos["detalles"]:
            lineas.append({"producto_id": d["producto_id"], "bodega_id": origen, "cantidad": -d["cantidad"]})
            lineas.append({"producto_id": d["producto_id"], "bodega_id": destino, "cantidad": d["cantidad"]})
        movimiento = registrar_movimiento(
            "TRASLADO", origen, lineas, bodega_destino_id=destino, observacion=datos["observacion"]
        )
        return _respuesta(movimiento, "Traslado registrado correctamente")


@blp.route("/movimientos/devoluciones")
class Devoluciones(MethodView):
    @blp.arguments(DevolucionSchema)
    @blp.response(201, MovimientoRespuestaSchema)
    @requiere_rol(*OPERADORES)
    def post(self, datos):
        """Registra devoluciones de clientes (entra stock) o a proveedores (sale stock)"""
        validar_productos(_sin_repetidos(datos["detalles"]), exigir_activos=False)
        bodega_activa(datos["bodega_id"])
        signo = 1 if datos["tipo"] == "CLIENTE" else -1
        lineas = [
            {"producto_id": d["producto_id"], "bodega_id": datos["bodega_id"], "cantidad": signo * d["cantidad"]}
            for d in datos["detalles"]
        ]
        movimiento = registrar_movimiento(
            f"DEVOLUCION_{datos['tipo']}", datos["bodega_id"], lineas, referencia=datos.get("referencia"),
            proveedor_id=datos.get("proveedor_id"), observacion=datos["observacion"],
        )
        return _respuesta(movimiento, "Devolución registrada y stock actualizado correctamente")


# ----------------------------------------------------- trazabilidad RF10
@blp.route("/kardex")
class Kardex(MethodView):
    @blp.arguments(KardexFiltroSchema, location="query")
    @blp.response(200, KardexPaginadoSchema)
    @requiere_rol()
    def get(self, filtros):
        """Kardex: histórico de movimientos con usuario, fecha y saldo resultante"""
        consulta = DetalleMovimiento.query.join(Movimiento)
        if "producto_id" in filtros:
            consulta = consulta.filter(DetalleMovimiento.producto_id == filtros["producto_id"])
        if "bodega_id" in filtros:
            consulta = consulta.filter(DetalleMovimiento.bodega_id == filtros["bodega_id"])
        if "tipo" in filtros:
            consulta = consulta.filter(Movimiento.tipo == filtros["tipo"])
        if "desde" in filtros:
            consulta = consulta.filter(Movimiento.fecha >= filtros["desde"].replace(tzinfo=None))
        if "hasta" in filtros:
            consulta = consulta.filter(Movimiento.fecha <= filtros["hasta"].replace(tzinfo=None))
        consulta = consulta.order_by(Movimiento.fecha.desc(), DetalleMovimiento.id.desc())
        return paginar(consulta, filtros["page"], filtros["limit"])


@blp.route("/movimientos/<string:codigo>")
class MovimientoPorCodigo(MethodView):
    @blp.response(200, MovimientoSchema)
    @requiere_rol()
    def get(self, codigo):
        """Consulta un movimiento por su código de transacción"""
        movimiento = Movimiento.query.filter_by(codigo=codigo).first()
        if not movimiento:
            abort(404, message="Movimiento no encontrado.")
        return movimiento


@blp.route("/movimientos/resumen")
class Resumen(MethodView):
    @blp.arguments(ResumenFiltroSchema, location="query")
    @blp.response(200, ResumenItemSchema(many=True))
    @requiere_rol()
    def get(self, filtros):
        """Cantidades totales movidas por producto (insumo para el reporte de rotación)"""
        consulta = (
            db.session.query(
                DetalleMovimiento.producto_id,
                func.sum(func.abs(DetalleMovimiento.cantidad)).label("cantidad_total"),
                func.count(func.distinct(Movimiento.id)).label("numero_movimientos"),
            )
            .join(Movimiento)
            .filter(Movimiento.tipo == filtros["tipo"])
        )
        if "desde" in filtros:
            consulta = consulta.filter(Movimiento.fecha >= filtros["desde"].replace(tzinfo=None))
        if "hasta" in filtros:
            consulta = consulta.filter(Movimiento.fecha <= filtros["hasta"].replace(tzinfo=None))
        filas = consulta.group_by(DetalleMovimiento.producto_id).all()
        return [
            {"producto_id": f.producto_id, "cantidad_total": int(f.cantidad_total),
             "numero_movimientos": f.numero_movimientos}
            for f in filas
        ]
