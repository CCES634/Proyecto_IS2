"""Endpoints del servicio de Catálogo: RF01, RF02, RF12 y RF15."""
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from sqlalchemy import and_, or_

from .common import ROL_ADMIN, esquema_paginado, paginar, requiere_rol
from .models import Categoria, ModeloMoto, Producto, db
from .schemas import (
    CategoriaActualizarSchema,
    CategoriaDetalleSchema,
    CategoriaFiltroSchema,
    CategoriaSchema,
    CompatiblesFiltroSchema,
    ConsultaLoteRespuestaSchema,
    ConsultaLoteSchema,
    ModeloMotoSchema,
    ProductoActualizarSchema,
    ProductoFiltroSchema,
    ProductoSchema,
)

blp = Blueprint("catalogo", __name__, url_prefix="/api/catalogo", description="Productos, categorías y compatibilidad")

ProductosPaginadosSchema = esquema_paginado(ProductoSchema, "ProductosPaginados")


# ----------------------------------------------------------------- helpers
def _obtener(modelo, id_, nombre):
    obj = db.session.get(modelo, id_)
    if not obj:
        abort(404, message=f"{nombre} no encontrado(a).")
    return obj


def _validar_padre(padre_id, categoria_id=None):
    if padre_id is None:
        return
    padre = _obtener(Categoria, padre_id, "Categoría padre")
    # Evita ciclos: una categoría no puede ser su propio ancestro
    while padre is not None:
        if padre.id == categoria_id:
            abort(400, message="La categoría no puede ser subcategoría de sí misma.")
        padre = padre.padre


def _ids_categoria_con_hijas(categoria_id):
    ids, pendientes = [], [categoria_id]
    while pendientes:
        actual = pendientes.pop()
        ids.append(actual)
        pendientes.extend(c.id for c in Categoria.query.filter_by(padre_id=actual).all())
    return ids


def _modelos(ids):
    if not ids:
        return []
    modelos = ModeloMoto.query.filter(ModeloMoto.id.in_(ids)).all()
    faltantes = set(ids) - {m.id for m in modelos}
    if faltantes:
        abort(400, message=f"Modelos de moto inexistentes: {sorted(faltantes)}")
    return modelos


# -------------------------------------------------------------- categorías
@blp.route("/categorias")
class Categorias(MethodView):
    @blp.arguments(CategoriaFiltroSchema, location="query")
    @blp.response(200, CategoriaSchema(many=True))
    @requiere_rol()
    def get(self, filtros):
        """Lista categorías (o subcategorías de una categoría)"""
        consulta = Categoria.query
        if "padre_id" in filtros:
            consulta = consulta.filter_by(padre_id=filtros["padre_id"])
        elif filtros.get("raiz"):
            consulta = consulta.filter(Categoria.padre_id.is_(None))
        return consulta.order_by(Categoria.nombre).all()

    @blp.arguments(CategoriaSchema)
    @blp.response(201, CategoriaSchema)
    @requiere_rol(ROL_ADMIN)
    def post(self, datos):
        """Crea una categoría o subcategoría"""
        _validar_padre(datos.get("padre_id"))
        categoria = Categoria(**datos)
        db.session.add(categoria)
        db.session.commit()
        return categoria


@blp.route("/categorias/<int:categoria_id>")
class CategoriaPorId(MethodView):
    @blp.response(200, CategoriaDetalleSchema)
    @requiere_rol()
    def get(self, categoria_id):
        """Consulta una categoría con sus subcategorías"""
        return _obtener(Categoria, categoria_id, "Categoría")

    @blp.arguments(CategoriaActualizarSchema)
    @blp.response(200, CategoriaSchema)
    @requiere_rol(ROL_ADMIN)
    def put(self, datos, categoria_id):
        """Actualiza una categoría"""
        categoria = _obtener(Categoria, categoria_id, "Categoría")
        if "padre_id" in datos:
            _validar_padre(datos["padre_id"], categoria.id)
        for campo, valor in datos.items():
            setattr(categoria, campo, valor)
        db.session.commit()
        return categoria

    @blp.response(204)
    @requiere_rol(ROL_ADMIN)
    def delete(self, categoria_id):
        """Elimina una categoría sin productos ni subcategorías"""
        categoria = _obtener(Categoria, categoria_id, "Categoría")
        if Categoria.query.filter_by(padre_id=categoria.id).first():
            abort(409, message="La categoría tiene subcategorías; elimínelas o muévalas primero.")
        if Producto.query.filter_by(categoria_id=categoria.id).first():
            abort(409, message="La categoría tiene productos asociados.")
        db.session.delete(categoria)
        db.session.commit()


# ------------------------------------------------------- modelos de moto
@blp.route("/modelos")
class Modelos(MethodView):
    @blp.response(200, ModeloMotoSchema(many=True))
    @requiere_rol()
    def get(self):
        """Lista los modelos de moto registrados"""
        return ModeloMoto.query.order_by(ModeloMoto.marca, ModeloMoto.modelo).all()

    @blp.arguments(ModeloMotoSchema)
    @blp.response(201, ModeloMotoSchema)
    @requiere_rol(ROL_ADMIN)
    def post(self, datos):
        """Registra un modelo de moto"""
        modelo = ModeloMoto(**datos)
        db.session.add(modelo)
        db.session.commit()
        return modelo


# --------------------------------------------------------------- productos
@blp.route("/productos")
class Productos(MethodView):
    @blp.arguments(ProductoFiltroSchema, location="query")
    @blp.response(200, ProductosPaginadosSchema)
    @requiere_rol()
    def get(self, filtros):
        """Busca y filtra productos (nombre, código, categoría, proveedor, compatibilidad)"""
        consulta = Producto.query
        if filtros.get("activo") is not None:
            consulta = consulta.filter(Producto.activo == filtros["activo"])
        if filtros.get("q"):
            patron = f"%{filtros['q']}%"
            consulta = consulta.filter(or_(Producto.nombre.ilike(patron), Producto.codigo_sku.ilike(patron)))
        if filtros.get("codigo"):
            consulta = consulta.filter(Producto.codigo_sku == filtros["codigo"].upper())
        if "categoria_id" in filtros:
            consulta = consulta.filter(Producto.categoria_id.in_(_ids_categoria_con_hijas(filtros["categoria_id"])))
        if "proveedor_id" in filtros:
            consulta = consulta.filter(Producto.proveedor_id == filtros["proveedor_id"])
        if filtros.get("compatible"):
            patron = f"%{filtros['compatible']}%"
            consulta = consulta.filter(Producto.modelos.any(or_(
                ModeloMoto.modelo.ilike(patron), ModeloMoto.marca.ilike(patron)
            )))
        return paginar(consulta.order_by(Producto.nombre), filtros["page"], filtros["limit"])

    @blp.arguments(ProductoSchema)
    @blp.response(201, ProductoSchema)
    @requiere_rol(ROL_ADMIN)
    def post(self, datos):
        """Crea un producto"""
        _obtener(Categoria, datos["categoria_id"], "Categoría")
        if Producto.query.filter_by(codigo_sku=datos["codigo_sku"]).first():
            abort(409, message="Ya existe un producto con ese código SKU.")
        modelos = _modelos(datos.pop("modelos_ids", []))
        producto = Producto(**datos)
        producto.modelos = modelos
        db.session.add(producto)
        db.session.commit()
        return producto


@blp.route("/productos/compatibles")
class ProductosCompatibles(MethodView):
    @blp.arguments(CompatiblesFiltroSchema, location="query")
    @blp.response(200, ProductosPaginadosSchema)
    @requiere_rol()
    def get(self, filtros):
        """RF15 - Repuestos compatibles con un modelo (y opcionalmente marca/año) de moto"""
        condiciones = [ModeloMoto.modelo.ilike(f"%{filtros['modelo']}%")]
        if filtros.get("marca"):
            condiciones.append(ModeloMoto.marca.ilike(f"%{filtros['marca']}%"))
        if filtros.get("anio"):
            anio = filtros["anio"]
            condiciones.append(or_(ModeloMoto.anio_desde.is_(None), ModeloMoto.anio_desde <= anio))
            condiciones.append(or_(ModeloMoto.anio_hasta.is_(None), ModeloMoto.anio_hasta >= anio))
        consulta = Producto.query.filter(Producto.activo.is_(True), Producto.modelos.any(and_(*condiciones)))
        return paginar(consulta.order_by(Producto.nombre), filtros["page"], filtros["limit"])


@blp.route("/productos/<int:producto_id>")
class ProductoPorId(MethodView):
    @blp.response(200, ProductoSchema)
    @requiere_rol()
    def get(self, producto_id):
        """Consulta un producto"""
        return _obtener(Producto, producto_id, "Producto")

    @blp.arguments(ProductoActualizarSchema)
    @blp.response(200, ProductoSchema)
    @requiere_rol(ROL_ADMIN)
    def put(self, datos, producto_id):
        """Actualiza un producto (solo los campos enviados)"""
        producto = _obtener(Producto, producto_id, "Producto")
        if "categoria_id" in datos:
            _obtener(Categoria, datos["categoria_id"], "Categoría")
        if "codigo_sku" in datos and datos["codigo_sku"] != producto.codigo_sku:
            if Producto.query.filter_by(codigo_sku=datos["codigo_sku"]).first():
                abort(409, message="Ya existe un producto con ese código SKU.")
        costo = datos.get("precio_costo", float(producto.precio_costo))
        venta = datos.get("precio_venta", float(producto.precio_venta))
        if venta < costo:
            abort(422, message="El precio de venta no puede ser menor al precio de costo.")
        if "modelos_ids" in datos:
            producto.modelos = _modelos(datos.pop("modelos_ids"))
        for campo, valor in datos.items():
            setattr(producto, campo, valor)
        db.session.commit()
        return producto

    @blp.response(204)
    @requiere_rol(ROL_ADMIN)
    def delete(self, producto_id):
        """Da de baja un producto (borrado lógico para conservar la trazabilidad)"""
        producto = _obtener(Producto, producto_id, "Producto")
        producto.activo = False
        db.session.commit()


@blp.route("/productos/consulta")
class ProductosConsulta(MethodView):
    @blp.arguments(ConsultaLoteSchema)
    @blp.response(200, ConsultaLoteRespuestaSchema)
    @requiere_rol()
    def post(self, datos):
        """Consulta varios productos por id (contrato usado por Reportes e Inventario)"""
        ids = list(dict.fromkeys(datos["productos_ids"]))
        productos = Producto.query.filter(Producto.id.in_(ids)).all()
        encontrados = {p.id for p in productos}
        return {"productos": productos, "no_encontrados": [i for i in ids if i not in encontrados]}
