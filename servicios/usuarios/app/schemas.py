from marshmallow import Schema, fields, validate

ROLES_VALIDOS = ["ADMIN", "OPERADOR"]
PASSWORD = validate.Length(min=8, max=72, error="La contraseña debe tener entre 8 y 72 caracteres.")


class LoginSchema(Schema):
    correo = fields.Email(required=True)
    password = fields.String(required=True, load_only=True)


class UsuarioSchema(Schema):
    id = fields.Integer(dump_only=True)
    nombre = fields.String(required=True, validate=validate.Length(min=3, max=100))
    correo = fields.Email(required=True)
    rol = fields.Function(lambda u: u.rol.nombre, dump_only=True)
    activo = fields.Boolean(dump_only=True)
    ultimo_acceso = fields.DateTime(dump_only=True)
    creado_en = fields.DateTime(dump_only=True)
    actualizado_en = fields.DateTime(dump_only=True)


class UsuarioCrearSchema(Schema):
    nombre = fields.String(required=True, validate=validate.Length(min=3, max=100))
    correo = fields.Email(required=True)
    password = fields.String(required=True, load_only=True, validate=PASSWORD)
    rol = fields.String(required=True, validate=validate.OneOf(ROLES_VALIDOS))


class UsuarioActualizarSchema(Schema):
    nombre = fields.String(validate=validate.Length(min=3, max=100))
    correo = fields.Email()
    rol = fields.String(validate=validate.OneOf(ROLES_VALIDOS))
    activo = fields.Boolean()


class UsuarioFiltroSchema(Schema):
    rol = fields.String(validate=validate.OneOf(ROLES_VALIDOS))
    activo = fields.Boolean()
    q = fields.String(metadata={"description": "Busca por nombre o correo"})
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    limit = fields.Integer(load_default=20, validate=validate.Range(min=1, max=500))


class TokenRespuestaSchema(Schema):
    token = fields.String()
    tipo = fields.String()
    expira_en_minutos = fields.Integer()
    usuario = fields.Nested(UsuarioSchema)


class CambioPasswordSchema(Schema):
    password_actual = fields.String(required=True, load_only=True)
    password_nueva = fields.String(required=True, load_only=True, validate=PASSWORD)


class RecuperarSchema(Schema):
    correo = fields.Email(required=True)


class RestablecerSchema(Schema):
    token = fields.String(required=True)
    password_nueva = fields.String(required=True, load_only=True, validate=PASSWORD)


class MensajeSchema(Schema):
    mensaje = fields.String()
    token_demo = fields.String(metadata={"description": "Solo en MODO_DEMO: token de recuperación"})


class RolSchema(Schema):
    id = fields.Integer()
    nombre = fields.String()
    descripcion = fields.String()
