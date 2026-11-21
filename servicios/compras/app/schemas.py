from marshmallow import Schema, fields, validate

from .models import ESTADOS_ORDEN


class ProveedorSchema(Schema):
    id = fields.Integer(dump_only=True)
    nit = fields.String(required=True, validate=validate.Regexp(r"^[0-9]{6,12}(-[0-9])?$", error="NIT inválido."))
    razon_social = fields.String(required=True, validate=validate.Length(min=3, max=150))
    contacto = fields.String(allow_none=True, validate=validate.Length(max=100))
    telefono = fields.String(allow_none=True, validate=validate.Regexp(r"^[0-9+ ]{7,20}$"))
    correo = fields.Email(allow_none=True)
    direccion = fields.String(allow_none=True, validate=validate.Length(max=200))
    activo = fields.Boolean(dump_only=True)
    productos_ids = fields.Function(lambda p: [x.producto_id for x in p.productos], dump_only=True)


class ProveedorActualizarSchema(Schema):
    razon_social = fields.String(validate=validate.Length(min=3, max=150))
    contacto = fields.String(allow_none=True, validate=validate.Length(max=100))
    telefono = fields.String(allow_none=True, validate=validate.Regexp(r"^[0-9+ ]{7,20}$"))
    correo = fields.Email(allow_none=True)
    direccion = fields.String(allow_none=True, validate=validate.Length(max=200))
    activo = fields.Boolean()


class ProveedorFiltroSchema(Schema):
    q = fields.String(metadata={"description": "Busca por razón social o NIT"})
    producto_id = fields.Integer(metadata={"description": "Proveedores que suministran este producto"})
    activo = fields.Boolean(load_default=True)
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    limit = fields.Integer(load_default=20, validate=validate.Range(min=1, max=500))


class ProveedorProductoSchema(Schema):
    producto_id = fields.Integer(required=True)
    costo_referencia = fields.Float(allow_none=True, validate=validate.Range(min=0))


class DetalleOrdenSchema(Schema):
    producto_id = fields.Integer(required=True)
    cantidad = fields.Integer(required=True, validate=validate.Range(min=1, max=100000))
    costo_unitario = fields.Float(required=True, validate=validate.Range(min=0))
    cantidad_recibida = fields.Integer(dump_only=True)
    pendiente = fields.Integer(dump_only=True)


class OrdenCrearSchema(Schema):
    proveedor_id = fields.Integer(required=True)
    bodega_id = fields.Integer(required=True, metadata={"description": "Bodega donde se recibirá"})
    fecha_esperada = fields.Date(allow_none=True)
    observacion = fields.String(allow_none=True, validate=validate.Length(max=300))
    detalles = fields.List(fields.Nested(DetalleOrdenSchema), required=True, validate=validate.Length(min=1))


class RecepcionResumenSchema(Schema):
    id = fields.Integer()
    transaccion_inventario = fields.String()
    fecha = fields.DateTime()
    usuario_id = fields.Integer()
    observacion = fields.String(allow_none=True)
    detalles = fields.Function(lambda r: [{"producto_id": d.producto_id, "cantidad": d.cantidad} for d in r.detalles])


class OrdenSchema(Schema):
    id = fields.Integer()
    codigo = fields.String()
    proveedor_id = fields.Integer()
    proveedor = fields.Function(lambda o: o.proveedor.razon_social)
    bodega_id = fields.Integer()
    estado = fields.String()
    observacion = fields.String(allow_none=True)
    fecha_creacion = fields.DateTime()
    fecha_esperada = fields.Date(allow_none=True)
    actualizado_en = fields.DateTime()
    usuario_id = fields.Integer()
    total = fields.Float()
    detalles = fields.List(fields.Nested(DetalleOrdenSchema))
    recepciones = fields.List(fields.Nested(RecepcionResumenSchema))


class OrdenFiltroSchema(Schema):
    estado = fields.String(validate=validate.OneOf(ESTADOS_ORDEN))
    proveedor_id = fields.Integer()
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    limit = fields.Integer(load_default=20, validate=validate.Range(min=1, max=500))


class CambioEstadoSchema(Schema):
    estado = fields.String(required=True, validate=validate.OneOf(["ENVIADA", "CANCELADA"]))


class DetalleRecepcionSchema(Schema):
    producto_id = fields.Integer(required=True)
    cantidad = fields.Integer(required=True, validate=validate.Range(min=1, max=100000))


class RecepcionSchema(Schema):
    observacion = fields.String(load_default="", validate=validate.Length(max=300))
    detalles = fields.List(fields.Nested(DetalleRecepcionSchema), required=True, validate=validate.Length(min=1))
