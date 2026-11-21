from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def ahora():
    return datetime.now(timezone.utc).replace(tzinfo=None)


ESTADOS_ORDEN = ["BORRADOR", "ENVIADA", "RECIBIDA_PARCIAL", "RECIBIDA", "CANCELADA"]


class Proveedor(db.Model):
    """RF03 - Proveedores."""
    __tablename__ = "proveedores"

    id = db.Column(db.Integer, primary_key=True)
    nit = db.Column(db.String(20), unique=True, nullable=False)
    razon_social = db.Column(db.String(150), nullable=False)
    contacto = db.Column(db.String(100))
    telefono = db.Column(db.String(20))
    correo = db.Column(db.String(120))
    direccion = db.Column(db.String(200))
    activo = db.Column(db.Boolean, nullable=False, default=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora)

    productos = db.relationship("ProveedorProducto", backref="proveedor", lazy="selectin",
                                cascade="all, delete-orphan")


class ProveedorProducto(db.Model):
    """Asociación proveedor - producto (el producto pertenece a Catálogo, sin llave foránea)."""
    __tablename__ = "proveedor_productos"

    proveedor_id = db.Column(db.Integer, db.ForeignKey("proveedores.id"), primary_key=True)
    producto_id = db.Column(db.Integer, primary_key=True)
    costo_referencia = db.Column(db.Numeric(12, 2))


class OrdenCompra(db.Model):
    """RF06 - Órdenes de compra."""
    __tablename__ = "ordenes_compra"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True, nullable=False)
    proveedor_id = db.Column(db.Integer, db.ForeignKey("proveedores.id"), nullable=False)
    bodega_id = db.Column(db.Integer, nullable=False)  # pertenece a Inventario
    estado = db.Column(db.String(20), nullable=False, default="BORRADOR", index=True)
    observacion = db.Column(db.String(300))
    fecha_creacion = db.Column(db.DateTime, nullable=False, default=ahora)
    fecha_esperada = db.Column(db.Date)
    actualizado_en = db.Column(db.DateTime, nullable=False, default=ahora, onupdate=ahora)
    usuario_id = db.Column(db.Integer, nullable=False)

    proveedor = db.relationship("Proveedor", lazy="joined")
    detalles = db.relationship("DetalleOrden", backref="orden", lazy="selectin", cascade="all, delete-orphan")
    recepciones = db.relationship("Recepcion", backref="orden", lazy="selectin", cascade="all, delete-orphan")

    @property
    def total(self):
        return float(sum(d.cantidad * d.costo_unitario for d in self.detalles))


class DetalleOrden(db.Model):
    __tablename__ = "detalles_orden"

    id = db.Column(db.Integer, primary_key=True)
    orden_id = db.Column(db.Integer, db.ForeignKey("ordenes_compra.id"), nullable=False)
    producto_id = db.Column(db.Integer, nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    cantidad_recibida = db.Column(db.Integer, nullable=False, default=0)
    costo_unitario = db.Column(db.Numeric(12, 2), nullable=False)

    @property
    def pendiente(self):
        return self.cantidad - self.cantidad_recibida


class Recepcion(db.Model):
    """Recepción de mercancía contra una orden; guarda la transacción de Inventario."""
    __tablename__ = "recepciones"

    id = db.Column(db.Integer, primary_key=True)
    orden_id = db.Column(db.Integer, db.ForeignKey("ordenes_compra.id"), nullable=False)
    transaccion_inventario = db.Column(db.String(30), nullable=False)
    observacion = db.Column(db.String(300))
    usuario_id = db.Column(db.Integer, nullable=False)
    fecha = db.Column(db.DateTime, nullable=False, default=ahora)

    detalles = db.relationship("DetalleRecepcion", lazy="selectin", cascade="all, delete-orphan")


class DetalleRecepcion(db.Model):
    __tablename__ = "detalles_recepcion"

    id = db.Column(db.Integer, primary_key=True)
    recepcion_id = db.Column(db.Integer, db.ForeignKey("recepciones.id"), nullable=False)
    producto_id = db.Column(db.Integer, nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
