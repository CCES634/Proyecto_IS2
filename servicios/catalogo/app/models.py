from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def ahora():
    return datetime.now(timezone.utc).replace(tzinfo=None)


# RF15 - Compatibilidad de repuestos (relación muchos a muchos)
compatibilidad = db.Table(
    "producto_compatibilidad",
    db.Column("producto_id", db.Integer, db.ForeignKey("productos.id", ondelete="CASCADE"), primary_key=True),
    db.Column("modelo_id", db.Integer, db.ForeignKey("modelos_moto.id", ondelete="CASCADE"), primary_key=True),
)


class Categoria(db.Model):
    """RF02 - Categorías y subcategorías (autorrelación padre/hijas)."""
    __tablename__ = "categorias"
    __table_args__ = (db.UniqueConstraint("nombre", "padre_id", name="uq_categoria_nombre_padre"),)

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), nullable=False)
    descripcion = db.Column(db.String(255))
    padre_id = db.Column(db.Integer, db.ForeignKey("categorias.id"), nullable=True)

    padre = db.relationship("Categoria", remote_side=[id], backref="subcategorias")


class ModeloMoto(db.Model):
    __tablename__ = "modelos_moto"
    __table_args__ = (db.UniqueConstraint("marca", "modelo", name="uq_modelo_moto"),)

    id = db.Column(db.Integer, primary_key=True)
    marca = db.Column(db.String(50), nullable=False)
    modelo = db.Column(db.String(80), nullable=False)
    cilindraje = db.Column(db.Integer)
    anio_desde = db.Column(db.Integer)
    anio_hasta = db.Column(db.Integer)

    @property
    def descripcion(self):
        return f"{self.marca} {self.modelo}"


class Producto(db.Model):
    """RF01 - Productos. proveedor_id pertenece al servicio de Compras (sin llave foránea)."""
    __tablename__ = "productos"

    id = db.Column(db.Integer, primary_key=True)
    codigo_sku = db.Column(db.String(30), unique=True, nullable=False, index=True)
    nombre = db.Column(db.String(120), nullable=False, index=True)
    descripcion = db.Column(db.String(500))
    categoria_id = db.Column(db.Integer, db.ForeignKey("categorias.id"), nullable=False)
    unidad_medida = db.Column(db.String(20), nullable=False, default="UNIDAD")
    precio_costo = db.Column(db.Numeric(12, 2), nullable=False)
    precio_venta = db.Column(db.Numeric(12, 2), nullable=False)
    proveedor_id = db.Column(db.Integer, index=True)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora)
    actualizado_en = db.Column(db.DateTime, nullable=False, default=ahora, onupdate=ahora)

    categoria = db.relationship("Categoria", lazy="joined")
    modelos = db.relationship("ModeloMoto", secondary=compatibilidad, lazy="selectin")
