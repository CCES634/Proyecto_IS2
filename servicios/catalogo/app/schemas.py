from marshmallow import Schema, ValidationError, fields, validate, validates_schema

UNIDADES = ["UNIDAD", "PAR", "KIT", "JUEGO", "LITRO", "GALON", "METRO", "CAJA"]


class CategoriaSchema(Schema):
    id = fields.Integer(dump_only=True)
    nombre = fields.String(required=True, validate=validate.Length(min=2, max=80))
    descripcion = fields.String(allow_none=True, validate=validate.Length(max=255))
    padre_id = fields.Integer(allow_none=True, metadata={"description": "Si se indica, es una subcategoría"})


class CategoriaDetalleSchema(CategoriaSchema):
    subcategorias = fields.List(fields.Nested(CategoriaSchema), dump_only=True)


class CategoriaActualizarSchema(Schema):
    nombre = fields.String(validate=validate.Length(min=2, max=80))
    descripcion = fields.String(allow_none=True, validate=validate.Length(max=255))
    padre_id = fields.Integer(allow_none=True)


class CategoriaFiltroSchema(Schema):
    padre_id = fields.Integer(metadata={"description": "Lista las subcategorías de esta categoría"})
    raiz = fields.Boolean(metadata={"description": "true = solo categorías principales"})


class ModeloMotoSchema(Schema):
    id = fields.Integer(dump_only=True)
    marca = fields.String(required=True, validate=validate.Length(min=2, max=50))
    modelo = fields.String(required=True, validate=validate.Length(min=1, max=80))
    cilindraje = fields.Integer(allow_none=True, validate=validate.Range(min=50, max=2000))
    anio_desde = fields.Integer(allow_none=True, validate=validate.Range(min=1950, max=2100))
    anio_hasta = fields.Integer(allow_none=True, validate=validate.Range(min=1950, max=2100))

    @validates_schema
    def validar_anios(self, datos, **kwargs):
        if datos.get("anio_desde") and datos.get("anio_hasta") and datos["anio_hasta"] < datos["anio_desde"]:
            raise ValidationError("anio_hasta no puede ser menor que anio_desde.", "anio_hasta")


class ProductoSchema(Schema):
    id = fields.Integer(dump_only=True)
    codigo_sku = fields.String(
        required=True,
        validate=validate.Regexp(r"^[A-Z0-9][A-Z0-9-]{2,29}$", error="SKU inválido: use mayúsculas, números y guiones."),
    )
    nombre = fields.String(required=True, validate=validate.Length(min=3, max=120))
    descripcion = fields.String(allow_none=True, validate=validate.Length(max=500))
    categoria_id = fields.Integer(required=True)
    categoria = fields.Function(lambda p: p.categoria.nombre if p.categoria else None, dump_only=True)
    unidad_medida = fields.String(load_default="UNIDAD", validate=validate.OneOf(UNIDADES))
    precio_costo = fields.Float(required=True, validate=validate.Range(min=0))
    precio_venta = fields.Float(required=True, validate=validate.Range(min=0))
    proveedor_id = fields.Integer(allow_none=True, metadata={"description": "Id del proveedor (servicio de Compras)"})
    activo = fields.Boolean(dump_only=True)
    compatibilidad = fields.Function(lambda p: [m.descripcion for m in p.modelos], dump_only=True)
    modelos_ids = fields.List(fields.Integer(), load_only=True, load_default=list)
    creado_en = fields.DateTime(dump_only=True)
    actualizado_en = fields.DateTime(dump_only=True)

    @validates_schema
    def validar_precios(self, datos, **kwargs):
        if "precio_costo" in datos and "precio_venta" in datos and datos["precio_venta"] < datos["precio_costo"]:
            raise ValidationError("El precio de venta no puede ser menor al precio de costo.", "precio_venta")


class ProductoActualizarSchema(ProductoSchema):
    """Todos los campos son opcionales; solo se actualiza lo enviado."""

    codigo_sku = fields.String(validate=validate.Regexp(r"^[A-Z0-9][A-Z0-9-]{2,29}$"))
    nombre = fields.String(validate=validate.Length(min=3, max=120))
    categoria_id = fields.Integer()
    unidad_medida = fields.String(validate=validate.OneOf(UNIDADES))
    precio_costo = fields.Float(validate=validate.Range(min=0))
    precio_venta = fields.Float(validate=validate.Range(min=0))
    modelos_ids = fields.List(fields.Integer(), load_only=True)
    activo = fields.Boolean()


class ProductoFiltroSchema(Schema):
    """RF12 - Búsqueda y filtrado de productos."""
    q = fields.String(metadata={"description": "Texto a buscar en nombre o código SKU"})
    codigo = fields.String()
    categoria_id = fields.Integer(metadata={"description": "Incluye las subcategorías"})
    proveedor_id = fields.Integer()
    compatible = fields.String(metadata={"description": "Modelo de moto, ej. FZ16"})
    activo = fields.Boolean(load_default=True)
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    limit = fields.Integer(load_default=20, validate=validate.Range(min=1, max=500))


class CompatiblesFiltroSchema(Schema):
    modelo = fields.String(required=True, metadata={"description": "Modelo de moto, ej. FZ16"})
    marca = fields.String(metadata={"description": "Marca, ej. Yamaha"})
    anio = fields.Integer(validate=validate.Range(min=1950, max=2100))
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    limit = fields.Integer(load_default=20, validate=validate.Range(min=1, max=500))


class ConsultaLoteSchema(Schema):
    productos_ids = fields.List(fields.Integer(), required=True, validate=validate.Length(min=1, max=500))


class ProductoResumenSchema(Schema):
    """Formato del contrato Reportes -> Catálogo definido en la Entrega 2."""
    producto_id = fields.Integer(attribute="id")
    codigo_sku = fields.String()
    nombre = fields.String()
    categoria = fields.Function(lambda p: p.categoria.nombre if p.categoria else None)
    unidad_medida = fields.String()
    precio_costo = fields.Float()
    precio_venta = fields.Float()
    proveedor_id = fields.Integer()
    activo = fields.Boolean()
    compatibilidad = fields.Function(lambda p: [m.descripcion for m in p.modelos])


class ConsultaLoteRespuestaSchema(Schema):
    productos = fields.List(fields.Nested(ProductoResumenSchema))
    no_encontrados = fields.List(fields.Integer())
