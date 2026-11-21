from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def ahora():
    return datetime.now(timezone.utc).replace(tzinfo=None)


TIPOS_MOVIMIENTO = ["ENTRADA", "SALIDA", "AJUSTE", "TRASLADO", "DEVOLUCION_CLIENTE", "DEVOLUCION_PROVEEDOR"]


class Bodega(db.Model):
    """RF05 - Bodegas o almacenes."""
    __tablename__ = "bodegas"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    direccion = db.Column(db.String(200))
    activa = db.Column(db.Boolean, nullable=False, default=True)


class Existencia(db.Model):
    """RF04 - Saldo disponible de un producto en una bodega."""
    __tablename__ = "existencias"
    __table_args__ = (db.UniqueConstraint("producto_id", "bodega_id", name="uq_existencia_producto_bodega"),)

    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, nullable=False, index=True)  # pertenece a Catálogo
    bodega_id = db.Column(db.Integer, db.ForeignKey("bodegas.id"), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False, default=0)
    costo_promedio = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    actualizado_en = db.Column(db.DateTime, nullable=False, default=ahora, onupdate=ahora)

    bodega = db.relationship("Bodega", lazy="joined")


class UmbralStock(db.Model):
    """RF09 - Stock mínimo configurable por producto."""
    __tablename__ = "umbrales_stock"

    producto_id = db.Column(db.Integer, primary_key=True)
    stock_minimo = db.Column(db.Integer, nullable=False)


class Movimiento(db.Model):
    """RF10 - Cabecera del movimiento: quién, cuándo y qué operación se hizo."""
    __tablename__ = "movimientos"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(30), unique=True, nullable=False, index=True)
    tipo = db.Column(db.String(25), nullable=False, index=True)
    bodega_id = db.Column(db.Integer, db.ForeignKey("bodegas.id"), nullable=False)
    bodega_destino_id = db.Column(db.Integer, db.ForeignKey("bodegas.id"))
    referencia = db.Column(db.String(50), comment="Orden de compra, comprobante, etc.")
    proveedor_id = db.Column(db.Integer)
    observacion = db.Column(db.String(300))
    usuario_id = db.Column(db.Integer, nullable=False)
    usuario_correo = db.Column(db.String(120))
    fecha = db.Column(db.DateTime, nullable=False, default=ahora, index=True)

    detalles = db.relationship("DetalleMovimiento", backref="movimiento", lazy="selectin",
                               cascade="all, delete-orphan")


class DetalleMovimiento(db.Model):
    """Línea del kardex: variación (+/-) del saldo de un producto en una bodega."""
    __tablename__ = "detalles_movimiento"

    id = db.Column(db.Integer, primary_key=True)
    movimiento_id = db.Column(db.Integer, db.ForeignKey("movimientos.id"), nullable=False)
    producto_id = db.Column(db.Integer, nullable=False, index=True)
    bodega_id = db.Column(db.Integer, db.ForeignKey("bodegas.id"), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)  # positiva = entra, negativa = sale
    costo_unitario = db.Column(db.Numeric(12, 2))
    precio_unitario = db.Column(db.Numeric(12, 2))
    saldo_resultante = db.Column(db.Integer, nullable=False)
