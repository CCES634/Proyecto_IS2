from marshmallow import Schema, ValidationError, fields, validate, validates_schema

from .models import TIPOS_MOVIMIENTO

CANTIDAD = validate.Range(min=1, max=100000)
OBSERVACION = validate.Length(max=300)


# ------------------------------------------------------------------ bodegas
class BodegaSchema(Schema):
    id = fields.Integer(dump_only=True)
    codigo = fields.String(required=True, validate=validate.Regexp(r"^[A-Z0-9-]{2,20}$"))
    nombre = fields.String(required=True, validate=validate.Length(min=3, max=100))
    direccion = fields.String(allow_none=True, validate=validate.Length(max=200))
    activa = fields.Boolean(dump_only=True)


class BodegaActualizarSchema(Schema):
    nombre = fields.String(validate=validate.Length(min=3, max=100))
    direccion = fields.String(allow_none=True, validate=validate.Length(max=200))
    activa = fields.Boolean()


# --------------------------------------------------------------- existencias
class ExistenciaSchema(Schema):
    producto_id = fields.Integer()
    bodega_id = fields.Integer()
    bodega = fields.Function(lambda e: e.bodega.nombre)
    cantidad = fields.Integer()
    costo_promedio = fields.Float()
    actualizado_en = fields.DateTime()


class ExistenciaFiltroSchema(Schema):
    producto_id = fields.Integer()
    bodega_id = fields.Integer()
    con_stock = fields.Boolean(metadata={"description": "true = solo saldos mayores a cero"})
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    limit = fields.Integer(load_default=50, validate=validate.Range(min=1, max=500))


class DesgloseBodegaSchema(Schema):
    bodega_id = fields.Integer()
    nombre = fields.String()
    cantidad = fields.Integer()


class StockProductoSchema(Schema):
    producto_id = fields.Integer()
    stock_total = fields.Integer()
    stock_minimo_configurado = fields.Integer(allow_none=True)
    estado_alerta = fields.String()
    desglose_bodegas = fields.List(fields.Nested(DesgloseBodegaSchema))


class AlertaFiltroSchema(Schema):
    solo_stock_bajo = fields.Boolean(load_default=True)
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    limit = fields.Integer(load_default=50, validate=validate.Range(min=1, max=500))


class AlertasRespuestaSchema(Schema):
    pagina_actual = fields.Integer()
    total_paginas = fields.Integer()
    total_registros = fields.Integer()
    data = fields.List(fields.Nested(StockProductoSchema))


class UmbralSchema(Schema):
    producto_id = fields.Integer(dump_only=True)
    stock_minimo = fields.Integer(required=True, validate=validate.Range(min=0, max=100000))


# -------------------------------------------------------------- movimientos
class DetalleEntradaSchema(Schema):
    producto_id = fields.Integer(required=True)
    cantidad = fields.Integer(required=True, validate=CANTIDAD)
    costo_unitario = fields.Float(load_default=None, allow_none=True, validate=validate.Range(min=0))


class EntradaSchema(Schema):
    """Contrato Compras/Proveedores -> Inventario (Entrega 2)."""
    orden_compra_id = fields.Integer(allow_none=True)
    proveedor_id = fields.Integer(allow_none=True)
    bodega_id = fields.Integer(required=True)
    observacion = fields.String(load_default="", validate=OBSERVACION)
    detalles = fields.List(fields.Nested(DetalleEntradaSchema), required=True, validate=validate.Length(min=1))


class DetalleSalidaSchema(Schema):
    producto_id = fields.Integer(required=True)
    cantidad = fields.Integer(required=True, validate=CANTIDAD)
    precio_venta_unitario = fields.Float(load_default=None, allow_none=True, validate=validate.Range(min=0))


class SalidaSchema(Schema):
    comprobante_venta_id = fields.String(allow_none=True, validate=validate.Length(max=50))
    bodega_id = fields.Integer(required=True)
    observacion = fields.String(load_default="", validate=OBSERVACION)
    detalles = fields.List(fields.Nested(DetalleSalidaSchema), required=True, validate=validate.Length(min=1))


class DetalleAjusteSchema(Schema):
    producto_id = fields.Integer(required=True)
    cantidad_contada = fields.Integer(required=True, validate=validate.Range(min=0, max=100000))


class AjusteSchema(Schema):
    """Ajuste por conteo físico: el sistema calcula la diferencia contra el saldo registrado."""
    bodega_id = fields.Integer(required=True)
    observacion = fields.String(required=True, validate=validate.Length(min=5, max=300))
    detalles = fields.List(fields.Nested(DetalleAjusteSchema), required=True, validate=validate.Length(min=1))


class DetalleCantidadSchema(Schema):
    producto_id = fields.Integer(required=True)
    cantidad = fields.Integer(required=True, validate=CANTIDAD)


class TrasladoSchema(Schema):
    bodega_origen_id = fields.Integer(required=True)
    bodega_destino_id = fields.Integer(required=True)
    observacion = fields.String(load_default="", validate=OBSERVACION)
    detalles = fields.List(fields.Nested(DetalleCantidadSchema), required=True, validate=validate.Length(min=1))

    @validates_schema
    def validar_bodegas(self, datos, **kwargs):
        if datos.get("bodega_origen_id") == datos.get("bodega_destino_id"):
            raise ValidationError("La bodega de destino debe ser diferente a la de origen.", "bodega_destino_id")


class DevolucionSchema(Schema):
    """RF13 - CLIENTE: el producto regresa al stock. PROVEEDOR: sale del stock."""
    tipo = fields.String(required=True, validate=validate.OneOf(["CLIENTE", "PROVEEDOR"]))
    bodega_id = fields.Integer(required=True)
    referencia = fields.String(allow_none=True, validate=validate.Length(max=50))
    proveedor_id = fields.Integer(allow_none=True)
    observacion = fields.String(required=True, validate=validate.Length(min=5, max=300))
    detalles = fields.List(fields.Nested(DetalleCantidadSchema), required=True, validate=validate.Length(min=1))


class MovimientoRespuestaSchema(Schema):
    transaccion_id = fields.String()
    mensaje = fields.String()
    fecha_registro = fields.DateTime()


class DetalleMovimientoSchema(Schema):
    producto_id = fields.Integer()
    bodega_id = fields.Integer()
    cantidad = fields.Integer()
    costo_unitario = fields.Float(allow_none=True)
    precio_unitario = fields.Float(allow_none=True)
    saldo_resultante = fields.Integer()


class MovimientoSchema(Schema):
    codigo = fields.String()
    tipo = fields.String()
    bodega_id = fields.Integer()
    bodega_destino_id = fields.Integer(allow_none=True)
    referencia = fields.String(allow_none=True)
    proveedor_id = fields.Integer(allow_none=True)
    observacion = fields.String(allow_none=True)
    usuario_id = fields.Integer()
    usuario_correo = fields.String(allow_none=True)
    fecha = fields.DateTime()
    detalles = fields.List(fields.Nested(DetalleMovimientoSchema))


class KardexSchema(Schema):
    """Una fila por línea de movimiento (histórico/kardex)."""
    fecha = fields.Function(lambda d: d.movimiento.fecha.isoformat())
    codigo = fields.Function(lambda d: d.movimiento.codigo)
    tipo = fields.Function(lambda d: d.movimiento.tipo)
    producto_id = fields.Integer()
    bodega_id = fields.Integer()
    cantidad = fields.Integer()
    saldo_resultante = fields.Integer()
    costo_unitario = fields.Float(allow_none=True)
    referencia = fields.Function(lambda d: d.movimiento.referencia)
    usuario_id = fields.Function(lambda d: d.movimiento.usuario_id)
    usuario_correo = fields.Function(lambda d: d.movimiento.usuario_correo)


class KardexFiltroSchema(Schema):
    producto_id = fields.Integer()
    bodega_id = fields.Integer()
    tipo = fields.String(validate=validate.OneOf(TIPOS_MOVIMIENTO))
    desde = fields.DateTime()
    hasta = fields.DateTime()
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    limit = fields.Integer(load_default=50, validate=validate.Range(min=1, max=500))


class ResumenFiltroSchema(Schema):
    tipo = fields.String(load_default="SALIDA", validate=validate.OneOf(TIPOS_MOVIMIENTO))
    desde = fields.DateTime()
    hasta = fields.DateTime()


class ResumenItemSchema(Schema):
    producto_id = fields.Integer()
    cantidad_total = fields.Integer()
    numero_movimientos = fields.Integer()
