"""RF07 - Gestión de usuarios y roles (solo administradores)."""
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from sqlalchemy import or_

from .common import ROL_ADMIN, esquema_paginado, paginar, requiere_rol, usuario_actual
from .models import Rol, Usuario, db
from .schemas import (
    RolSchema,
    UsuarioActualizarSchema,
    UsuarioCrearSchema,
    UsuarioFiltroSchema,
    UsuarioSchema,
)
from .security import cifrar_password

blp = Blueprint("usuarios", __name__, url_prefix="/api/usuarios", description="Gestión de usuarios y roles")

UsuariosPaginadosSchema = esquema_paginado(UsuarioSchema, "UsuariosPaginados")


def _rol(nombre):
    rol = Rol.query.filter_by(nombre=nombre).first()
    if not rol:
        abort(400, message=f"El rol {nombre} no existe.")
    return rol


def _usuario_o_404(usuario_id):
    usuario = db.session.get(Usuario, usuario_id)
    if not usuario:
        abort(404, message="Usuario no encontrado.")
    return usuario


@blp.route("/")
class Usuarios(MethodView):
    @blp.arguments(UsuarioFiltroSchema, location="query")
    @blp.response(200, UsuariosPaginadosSchema)
    @requiere_rol(ROL_ADMIN)
    def get(self, filtros):
        """Lista usuarios con filtros y paginación"""
        consulta = Usuario.query
        if "rol" in filtros:
            consulta = consulta.join(Rol).filter(Rol.nombre == filtros["rol"])
        if "activo" in filtros:
            consulta = consulta.filter(Usuario.activo == filtros["activo"])
        if filtros.get("q"):
            patron = f"%{filtros['q']}%"
            consulta = consulta.filter(or_(Usuario.nombre.ilike(patron), Usuario.correo.ilike(patron)))
        return paginar(consulta.order_by(Usuario.id), filtros["page"], filtros["limit"])

    @blp.arguments(UsuarioCrearSchema)
    @blp.response(201, UsuarioSchema)
    @requiere_rol(ROL_ADMIN)
    def post(self, datos):
        """Registra un usuario y le asigna un rol"""
        correo = datos["correo"].lower()
        if Usuario.query.filter_by(correo=correo).first():
            abort(409, message="Ya existe un usuario con ese correo.")
        usuario = Usuario(
            nombre=datos["nombre"],
            correo=correo,
            password_hash=cifrar_password(datos["password"]),
            rol=_rol(datos["rol"]),
        )
        db.session.add(usuario)
        db.session.commit()
        return usuario


@blp.route("/<int:usuario_id>")
class UsuarioPorId(MethodView):
    @blp.response(200, UsuarioSchema)
    @requiere_rol(ROL_ADMIN)
    def get(self, usuario_id):
        """Consulta un usuario"""
        return _usuario_o_404(usuario_id)

    @blp.arguments(UsuarioActualizarSchema)
    @blp.response(200, UsuarioSchema)
    @requiere_rol(ROL_ADMIN)
    def put(self, datos, usuario_id):
        """Actualiza datos, rol o estado de un usuario"""
        usuario = _usuario_o_404(usuario_id)
        if "correo" in datos:
            correo = datos["correo"].lower()
            existente = Usuario.query.filter_by(correo=correo).first()
            if existente and existente.id != usuario.id:
                abort(409, message="Ya existe un usuario con ese correo.")
            usuario.correo = correo
        if "nombre" in datos:
            usuario.nombre = datos["nombre"]
        if "rol" in datos:
            usuario.rol = _rol(datos["rol"])
        if "activo" in datos:
            if usuario.id == usuario_actual()["id"] and not datos["activo"]:
                abort(400, message="No puede desactivar su propio usuario.")
            usuario.activo = datos["activo"]
        db.session.commit()
        return usuario

    @blp.response(204)
    @requiere_rol(ROL_ADMIN)
    def delete(self, usuario_id):
        """Desactiva (da de baja) un usuario"""
        usuario = _usuario_o_404(usuario_id)
        if usuario.id == usuario_actual()["id"]:
            abort(400, message="No puede eliminar su propio usuario.")
        usuario.activo = False
        db.session.commit()


@blp.route("/roles")
class Roles(MethodView):
    @blp.response(200, RolSchema(many=True))
    @requiere_rol(ROL_ADMIN)
    def get(self):
        """Lista los roles disponibles"""
        return Rol.query.order_by(Rol.id).all()
