"""RF08 - Autenticación: inicio y cierre de sesión, cambio y recuperación de contraseña."""
from datetime import datetime, timedelta, timezone

from flask import current_app, request
from flask.views import MethodView
from flask_smorest import Blueprint, abort

from .common import obtener_logger, usuario_actual
from .models import TokenRecuperacion, TokenRevocado, Usuario, ahora, db
from .schemas import (
    CambioPasswordSchema,
    LoginSchema,
    MensajeSchema,
    RecuperarSchema,
    RestablecerSchema,
    TokenRespuestaSchema,
    UsuarioSchema,
)
from .security import (
    cifrar_password,
    emitir_token,
    generar_token_recuperacion,
    hash_token,
    verificar_password,
)

blp = Blueprint("auth", __name__, url_prefix="/api/auth", description="Autenticación de usuarios (JWT)")


@blp.route("/login")
class Login(MethodView):
    @blp.arguments(LoginSchema)
    @blp.response(200, TokenRespuestaSchema)
    @blp.doc(security=[])
    def post(self, datos):
        """Inicia sesión y devuelve un JWT"""
        usuario = Usuario.query.filter_by(correo=datos["correo"].lower()).first()
        if not usuario or not verificar_password(usuario.password_hash, datos["password"]):
            abort(401, message="Correo o contraseña incorrectos.")
        if not usuario.activo:
            abort(403, message="El usuario está inactivo.")
        usuario.ultimo_acceso = ahora()
        db.session.commit()
        token, minutos = emitir_token(usuario)
        return {"token": token, "tipo": "Bearer", "expira_en_minutos": minutos, "usuario": usuario}


@blp.route("/logout")
class Logout(MethodView):
    @blp.response(200, MensajeSchema)
    def post(self):
        """Cierra la sesión revocando el token actual"""
        usuario_actual()
        jti = request.headers.get("X-Token-Jti")
        exp = request.headers.get("X-Token-Exp")
        if not jti or not exp:
            abort(400, message="No se pudo identificar el token de la sesión.")
        if not db.session.get(TokenRevocado, jti):
            db.session.add(TokenRevocado(jti=jti, expira_en=datetime.fromtimestamp(int(exp), timezone.utc).replace(tzinfo=None)))
            db.session.commit()
        return {"mensaje": "Sesión cerrada correctamente."}


@blp.route("/yo")
class Perfil(MethodView):
    @blp.response(200, UsuarioSchema)
    def get(self):
        """Datos del usuario autenticado"""
        return _usuario_o_404(usuario_actual()["id"])


@blp.route("/password")
class CambioPassword(MethodView):
    @blp.arguments(CambioPasswordSchema)
    @blp.response(200, MensajeSchema)
    def put(self, datos):
        """Cambia la contraseña del usuario autenticado"""
        usuario = _usuario_o_404(usuario_actual()["id"])
        if not verificar_password(usuario.password_hash, datos["password_actual"]):
            abort(400, message="La contraseña actual no es correcta.")
        if datos["password_actual"] == datos["password_nueva"]:
            abort(400, message="La nueva contraseña debe ser diferente a la actual.")
        usuario.password_hash = cifrar_password(datos["password_nueva"])
        db.session.commit()
        return {"mensaje": "Contraseña actualizada correctamente."}


@blp.route("/recuperar")
class Recuperar(MethodView):
    @blp.arguments(RecuperarSchema)
    @blp.response(200, MensajeSchema)
    @blp.doc(security=[])
    def post(self, datos):
        """Solicita la recuperación de contraseña"""
        respuesta = {"mensaje": "Si el correo está registrado, se enviarán las instrucciones de recuperación."}
        usuario = Usuario.query.filter_by(correo=datos["correo"].lower(), activo=True).first()
        if usuario:
            token, token_hash = generar_token_recuperacion()
            minutos = current_app.config["RECUPERACION_EXPIRACION_MINUTOS"]
            db.session.add(TokenRecuperacion(
                usuario_id=usuario.id, token_hash=token_hash, expira_en=ahora() + timedelta(minutes=minutos)
            ))
            db.session.commit()
            obtener_logger(current_app).info(
                "token de recuperacion generado", extra={"datos": {"usuario_id": usuario.id}}
            )
            # Sin servidor de correo en el alcance: en modo demo se devuelve el token
            if current_app.config["MODO_DEMO"]:
                respuesta["token_demo"] = token
        return respuesta


@blp.route("/restablecer")
class Restablecer(MethodView):
    @blp.arguments(RestablecerSchema)
    @blp.response(200, MensajeSchema)
    @blp.doc(security=[])
    def post(self, datos):
        """Restablece la contraseña con el token de recuperación"""
        registro = TokenRecuperacion.query.filter_by(token_hash=hash_token(datos["token"])).first()
        if not registro or registro.usado or registro.expira_en < ahora():
            abort(400, message="El token de recuperación no es válido o ya expiró.")
        usuario = _usuario_o_404(registro.usuario_id)
        usuario.password_hash = cifrar_password(datos["password_nueva"])
        registro.usado = True
        db.session.commit()
        return {"mensaje": "Contraseña restablecida. Ya puede iniciar sesión."}


def _usuario_o_404(usuario_id):
    usuario = db.session.get(Usuario, usuario_id)
    if not usuario:
        abort(404, message="Usuario no encontrado.")
    return usuario


# --------------------------------------------------------------------------
# Endpoint interno (NO expuesto por el Gateway): consulta de tokens revocados
# --------------------------------------------------------------------------
interno = Blueprint("interno", __name__, url_prefix="/internal", description="Uso interno entre servicios")


@interno.route("/tokens-revocados/<string:jti>")
class Revocado(MethodView):
    def get(self, jti):
        """Indica si un token (jti) fue revocado"""
        return {"jti": jti, "revocado": db.session.get(TokenRevocado, jti) is not None}
