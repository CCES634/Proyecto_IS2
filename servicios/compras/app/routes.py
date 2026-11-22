"""Endpoints del servicio de Compras y Proveedores: RF03 y RF06."""
import uuid

from flask import current_app
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from sqlalchemy import or_

from .clientes import llamar_servicio
from .common import ROL_ADMIN, ROL_OPERADOR, esquema_paginado, obtener_logger, paginar, requiere_rol, usuario_actual
from .models import DetalleOrden, DetalleRecepcion, OrdenCompra, Proveedor, ProveedorProducto, Recepcion, db
from .schemas import (
    CambioEstadoSchema,
    OrdenCrearSchema,
    OrdenFiltroSchema,
    OrdenSchema,
    ProveedorActualizarSchema,
    ProveedorFiltroSchema,
    ProveedorProductoSchema,
    ProveedorSchema,
    RecepcionSchema,
)

blp = Blueprint("compras", __name__, url_prefix="/api/compras",
                description="Proveedores, órdenes de compra y recepción de mercancía")

ProveedoresPaginadosSchema = esquema_paginado(ProveedorSchema, "ProveedoresPaginados")
OrdenesPaginadasSchema = esquema_paginado(OrdenSchema, "OrdenesPaginadas")

# Transiciones permitidas manualmente; RECIBIDA_PARCIAL y RECIBIDA se dan por recepciones
TRANSICIONES = {
    "BORRADOR": {"ENVIADA", "CANCELADA"},
    "ENVIADA": {"CANCELADA"},
}


def _proveedor(proveedor_id):
    proveedor = db.session.get(Proveedor, proveedor_id)
    if not proveedor:
        abort(404, message="Proveedor no encontrado.")
    return proveedor


def _orden(orden_id):
    orden = db.session.get(OrdenCompra, orden_id)
    if not orden:
        abort(404, message="Orden de compra no encontrada.")
    return orden


def _validar_productos(ids):
    if not current_app.config["VALIDAR_PRODUCTOS"]:
        return
    respuesta = llamar_servicio(
        "catálogo", "POST", f"{current_app.config['CATALOGO_URL']}/api/catalogo/productos/consulta",
        json={"productos_ids": sorted(set(ids))},
    )
    cuerpo = respuesta.json()
    if respuesta.status_code != 200:
        abort(502, message="No fue posible validar los productos con el servicio de catálogo.")
    if cuerpo.get("no_encontrados"):
        abort(404, message=f"Productos inexistentes en el catálogo: {cuerpo['no_encontrados']}")
    inactivos = [p["producto_id"] for p in cuerpo["productos"] if not p.get("activo", True)]
    if inactivos:
        abort(409, message=f"Productos dados de baja en el catálogo: {inactivos}")


# -------------------------------------------------------------- proveedores
@blp.route("/proveedores")
class Proveedores(MethodView):
    @blp.arguments(ProveedorFiltroSchema, location="query")
    @blp.response(200, ProveedoresPaginadosSchema)
    @requiere_rol()
    def get(self, filtros):
        """Lista y busca proveedores"""
        consulta = Proveedor.query
        if filtros.get("activo") is not None:
            consulta = consulta.filter(Proveedor.activo == filtros["activo"])
        if filtros.get("q"):
            patron = f"%{filtros['q']}%"
            consulta = consulta.filter(or_(Proveedor.razon_social.ilike(patron), Proveedor.nit.ilike(patron)))
        if "producto_id" in filtros:
            consulta = consulta.filter(Proveedor.productos.any(producto_id=filtros["producto_id"]))
        return paginar(consulta.order_by(Proveedor.razon_social), filtros["page"], filtros["limit"])

    @blp.arguments(ProveedorSchema)
    @blp.response(201, ProveedorSchema)
    @requiere_rol(ROL_ADMIN)
    def post(self, datos):
        """Registra un proveedor"""
        if Proveedor.query.filter_by(nit=datos["nit"]).first():
            abort(409, message="Ya existe un proveedor con ese NIT.")
        proveedor = Proveedor(**datos)
        db.session.add(proveedor)
        db.session.commit()
        return proveedor


@blp.route("/proveedores/<int:proveedor_id>")
class ProveedorPorId(MethodView):
    @blp.response(200, ProveedorSchema)
    @requiere_rol()
    def get(self, proveedor_id):
        """Consulta un proveedor"""
        return _proveedor(proveedor_id)

    @blp.arguments(ProveedorActualizarSchema)
    @blp.response(200, ProveedorSchema)
    @requiere_rol(ROL_ADMIN)
    def put(self, datos, proveedor_id):
        """Actualiza un proveedor"""
        proveedor = _proveedor(proveedor_id)
        for campo, valor in datos.items():
            setattr(proveedor, campo, valor)
        db.session.commit()
        return proveedor

    @blp.response(204)
    @requiere_rol(ROL_ADMIN)
    def delete(self, proveedor_id):
        """Da de baja un proveedor (no puede tener órdenes abiertas)"""
        proveedor = _proveedor(proveedor_id)
        abiertas = OrdenCompra.query.filter(
            OrdenCompra.proveedor_id == proveedor_id,
            OrdenCompra.estado.in_(["BORRADOR", "ENVIADA", "RECIBIDA_PARCIAL"]),
        ).first()
        if abiertas:
            abort(409, message="El proveedor tiene órdenes de compra abiertas.")
        proveedor.activo = False
        db.session.commit()


@blp.route("/proveedores/<int:proveedor_id>/productos")
class ProductosProveedor(MethodView):
    @blp.response(200, ProveedorProductoSchema(many=True))
    @requiere_rol()
    def get(self, proveedor_id):
        """Productos que suministra un proveedor"""
        return _proveedor(proveedor_id).productos

    @blp.arguments(ProveedorProductoSchema)
    @blp.response(201, ProveedorProductoSchema)
    @requiere_rol(ROL_ADMIN)
    def post(self, datos, proveedor_id):
        """Asocia un producto del catálogo al proveedor"""
        proveedor = _proveedor(proveedor_id)
        _validar_productos([datos["producto_id"]])
        asociacion = db.session.get(ProveedorProducto, (proveedor.id, datos["producto_id"]))
        if asociacion:
            abort(409, message="El producto ya está asociado a este proveedor.")
        asociacion = ProveedorProducto(proveedor_id=proveedor.id, **datos)
        db.session.add(asociacion)
        db.session.commit()
        return asociacion


@blp.route("/proveedores/<int:proveedor_id>/productos/<int:producto_id>")
class ProductoProveedor(MethodView):
    @blp.response(204)
    @requiere_rol(ROL_ADMIN)
    def delete(self, proveedor_id, producto_id):
        """Elimina la asociación producto - proveedor"""
        asociacion = db.session.get(ProveedorProducto, (proveedor_id, producto_id))
        if not asociacion:
            abort(404, message="El producto no está asociado a este proveedor.")
        db.session.delete(asociacion)
        db.session.commit()


# ---------------------------------------------------------- órdenes de compra
@blp.route("/ordenes")
class Ordenes(MethodView):
    @blp.arguments(OrdenFiltroSchema, location="query")
    @blp.response(200, OrdenesPaginadasSchema)
    @requiere_rol()
    def get(self, filtros):
        """Lista órdenes de compra"""
        consulta = OrdenCompra.query
        if "estado" in filtros:
            consulta = consulta.filter_by(estado=filtros["estado"])
        if "proveedor_id" in filtros:
            consulta = consulta.filter_by(proveedor_id=filtros["proveedor_id"])
        return paginar(consulta.order_by(OrdenCompra.id.desc()), filtros["page"], filtros["limit"])

    @blp.arguments(OrdenCrearSchema)
    @blp.response(201, OrdenSchema)
    @requiere_rol(ROL_ADMIN)
    def post(self, datos):
        """Genera una orden de compra en estado BORRADOR"""
        proveedor = _proveedor(datos["proveedor_id"])
        if not proveedor.activo:
            abort(409, message="El proveedor está inactivo.")
        ids = [d["producto_id"] for d in datos["detalles"]]
        if len(ids) != len(set(ids)):
            abort(422, message="Un producto no puede repetirse en la misma orden.")
        _validar_productos(ids)

        orden = OrdenCompra(
            codigo=f"TMP-{uuid.uuid4().hex[:16]}", proveedor=proveedor, bodega_id=datos["bodega_id"],
            fecha_esperada=datos.get("fecha_esperada"), observacion=datos.get("observacion"),
            usuario_id=usuario_actual()["id"],
        )
        orden.detalles = [DetalleOrden(**d) for d in datos["detalles"]]
        db.session.add(orden)
        db.session.flush()
        orden.codigo = f"OC-{orden.fecha_creacion.year}-{orden.id:05d}"
        db.session.commit()
        return orden


@blp.route("/ordenes/<int:orden_id>")
class OrdenPorId(MethodView):
    @blp.response(200, OrdenSchema)
    @requiere_rol()
    def get(self, orden_id):
        """Consulta una orden con sus detalles y recepciones"""
        return _orden(orden_id)


@blp.route("/ordenes/<int:orden_id>/estado")
class EstadoOrden(MethodView):
    @blp.arguments(CambioEstadoSchema)
    @blp.response(200, OrdenSchema)
    @requiere_rol(ROL_ADMIN)
    def patch(self, datos, orden_id):
        """Cambia el estado de la orden (BORRADOR -> ENVIADA, o cancelación)"""
        orden = _orden(orden_id)
        if datos["estado"] not in TRANSICIONES.get(orden.estado, set()):
            abort(409, message=f"No se puede pasar una orden de {orden.estado} a {datos['estado']}.")
        orden.estado = datos["estado"]
        db.session.commit()
        return orden


@blp.route("/ordenes/<int:orden_id>/recepciones")
class Recepciones(MethodView):
    @blp.arguments(RecepcionSchema)
    @blp.response(201, OrdenSchema)
    @requiere_rol(ROL_ADMIN, ROL_OPERADOR)
    def post(self, datos, orden_id):
        """Recibe mercancía contra la orden y registra la entrada en Inventario"""
        orden = _orden(orden_id)
        if orden.estado not in ("ENVIADA", "RECIBIDA_PARCIAL"):
            abort(409, message=f"Solo se puede recibir mercancía de órdenes enviadas (estado actual: {orden.estado}).")

        detalles_orden = {d.producto_id: d for d in orden.detalles}
        for item in datos["detalles"]:
            detalle = detalles_orden.get(item["producto_id"])
            if not detalle:
                abort(422, message=f"El producto {item['producto_id']} no hace parte de la orden.")
            if item["cantidad"] > detalle.pendiente:
                abort(422, message=(
                    f"Cantidad a recibir del producto {item['producto_id']} supera lo pendiente ({detalle.pendiente})."
                ))

        # Comunicación síncrona: contrato Compras/Proveedores -> Inventario (Entrega 2)
        respuesta = llamar_servicio(
            "inventario", "POST", f"{current_app.config['INVENTARIO_URL']}/api/inventario/movimientos/entradas",
            json={
                "orden_compra_id": orden.id,
                "proveedor_id": orden.proveedor_id,
                "bodega_id": orden.bodega_id,
                "observacion": datos["observacion"] or f"Recepción de {orden.codigo}",
                "detalles": [
                    {"producto_id": i["producto_id"], "cantidad": i["cantidad"],
                     "costo_unitario": float(detalles_orden[i["producto_id"]].costo_unitario)}
                    for i in datos["detalles"]
                ],
            },
        )
        if respuesta.status_code != 201:
            mensaje = respuesta.json().get("message", "error desconocido")
            abort(respuesta.status_code if respuesta.status_code < 500 else 502,
                  message=f"Inventario rechazó la entrada: {mensaje}")
        transaccion = respuesta.json()["transaccion_id"]

        for item in datos["detalles"]:
            detalles_orden[item["producto_id"]].cantidad_recibida += item["cantidad"]
        orden.recepciones.append(Recepcion(
            transaccion_inventario=transaccion, observacion=datos["observacion"],
            usuario_id=usuario_actual()["id"],
            detalles=[DetalleRecepcion(**i) for i in datos["detalles"]],
        ))
        orden.estado = "RECIBIDA" if all(d.pendiente == 0 for d in orden.detalles) else "RECIBIDA_PARCIAL"
        db.session.commit()
        obtener_logger(current_app).info(
            "recepcion registrada",
            extra={"datos": {"orden": orden.codigo, "transaccion_inventario": transaccion, "estado": orden.estado}},
        )
        return orden
