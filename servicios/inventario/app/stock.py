"""Lógica de negocio del inventario: registra movimientos y actualiza saldos
dentro de una única transacción (todo o nada)."""
import time
import uuid

from flask import current_app
from flask_smorest import abort
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import lazyload

from .clientes import llamar_servicio
from .common import obtener_logger, usuario_actual
from .models import Bodega, DetalleMovimiento, Existencia, Movimiento, UmbralStock, ahora, db

REINTENTOS = 3

PREFIJOS = {
    "ENTRADA": "ENT",
    "SALIDA": "SAL",
    "AJUSTE": "AJU",
    "TRASLADO": "TRA",
    "DEVOLUCION_CLIENTE": "DVC",
    "DEVOLUCION_PROVEEDOR": "DVP",
}


def bodega_activa(bodega_id):
    bodega = db.session.get(Bodega, bodega_id)
    if not bodega:
        abort(404, message=f"La bodega {bodega_id} no existe.")
    if not bodega.activa:
        abort(409, message=f"La bodega {bodega.nombre} está inactiva.")
    return bodega


def validar_productos(ids, exigir_activos=True):
    """Valida contra el servicio de Catálogo que los productos existan (y estén activos)."""
    if not current_app.config["VALIDAR_PRODUCTOS"]:
        return
    ids = sorted(set(ids))
    respuesta = llamar_servicio(
        "catálogo", "POST", f"{current_app.config['CATALOGO_URL']}/api/catalogo/productos/consulta",
        json={"productos_ids": ids},
    )
    if respuesta.status_code != 200:
        abort(502, message="No fue posible validar los productos con el servicio de catálogo.")
    cuerpo = respuesta.json()
    if cuerpo.get("no_encontrados"):
        abort(404, message=f"Productos inexistentes en el catálogo: {cuerpo['no_encontrados']}")
    if exigir_activos:
        inactivos = [p["producto_id"] for p in cuerpo["productos"] if not p.get("activo", True)]
        if inactivos:
            abort(409, message=f"Productos dados de baja en el catálogo: {inactivos}")


def _existencia_bloqueada(producto_id, bodega_id):
    """Obtiene (o crea) el saldo bloqueando SOLO esa fila (SELECT ... FOR UPDATE).

    Se evita el JOIN con bodegas: con FOR UPDATE también bloquearía la fila de
    la bodega y provocaba deadlocks con la llave foránea de los movimientos.
    """
    existencia = (
        Existencia.query.options(lazyload(Existencia.bodega))
        .filter_by(producto_id=producto_id, bodega_id=bodega_id)
        .with_for_update(of=Existencia)
        .first()
    )
    if existencia is None:
        existencia = Existencia(producto_id=producto_id, bodega_id=bodega_id, cantidad=0, costo_promedio=0)
        db.session.add(existencia)
        db.session.flush()
    return existencia


def saldo_actual(producto_id, bodega_id):
    existencia = Existencia.query.filter_by(producto_id=producto_id, bodega_id=bodega_id).first()
    return existencia.cantidad if existencia else 0


def registrar_movimiento(tipo, bodega_id, lineas, **datos):
    """Registra un movimiento reintentando si la base de datos detecta un deadlock
    o un conflicto al crear el mismo saldo de forma concurrente."""
    for intento in range(1, REINTENTOS + 1):
        try:
            return _registrar_movimiento(tipo, bodega_id, lineas, **datos)
        except (OperationalError, IntegrityError) as error:
            db.session.rollback()
            if intento == REINTENTOS:
                raise
            obtener_logger(current_app).warning(
                "conflicto de concurrencia, reintentando",
                extra={"datos": {"intento": intento, "error": str(error.orig)[:120]}},
            )
            time.sleep(0.05 * intento)


def _registrar_movimiento(tipo, bodega_id, lineas, bodega_destino_id=None, referencia=None,
                          proveedor_id=None, observacion=None):
    """lineas: lista de dict con producto_id, bodega_id, cantidad (+/-),
    costo_unitario y precio_unitario opcionales. Todo ocurre en una transacción."""
    usuario = usuario_actual()

    # 1) Bloquear los saldos en un orden fijo (evita esperas circulares entre transacciones)
    saldos = {}
    for clave in sorted({(l["producto_id"], l["bodega_id"]) for l in lineas}):
        saldos[clave] = _existencia_bloqueada(*clave)

    # 2) Validar y actualizar saldos
    resultantes = []
    costo_salida = {}  # en traslados, la bodega destino hereda el costo de la bodega origen
    for linea in lineas:
        existencia = saldos[(linea["producto_id"], linea["bodega_id"])]
        nuevo_saldo = existencia.cantidad + linea["cantidad"]
        if nuevo_saldo < 0:
            db.session.rollback()
            abort(409, message=(
                f"Stock insuficiente del producto {linea['producto_id']} en la bodega {linea['bodega_id']}: "
                f"disponible {existencia.cantidad}, solicitado {-linea['cantidad']}."
            ))
        # Costo promedio ponderado: solo cambia cuando entra mercancía con costo
        costo = linea.get("costo_unitario")
        if linea["cantidad"] < 0:
            costo_salida[linea["producto_id"]] = float(existencia.costo_promedio or 0)
        elif costo is None and tipo == "TRASLADO":
            costo = costo_salida.get(linea["producto_id"])
            linea["costo_unitario"] = costo
        if linea["cantidad"] > 0 and costo is not None:
            valor_anterior = existencia.cantidad * float(existencia.costo_promedio or 0)
            existencia.costo_promedio = round((valor_anterior + linea["cantidad"] * costo) / nuevo_saldo, 2)
        existencia.cantidad = nuevo_saldo
        resultantes.append(nuevo_saldo)

    # 3) Registrar el movimiento y sus líneas (kardex)
    movimiento = Movimiento(
        codigo=f"TMP-{uuid.uuid4().hex[:20]}", tipo=tipo, bodega_id=bodega_id,
        bodega_destino_id=bodega_destino_id, referencia=referencia, proveedor_id=proveedor_id,
        observacion=observacion, usuario_id=usuario["id"], usuario_correo=usuario["correo"], fecha=ahora(),
    )
    db.session.add(movimiento)
    db.session.flush()
    movimiento.codigo = f"MOV-{PREFIJOS[tipo]}-{movimiento.fecha.year}-{movimiento.id:05d}"
    for linea, saldo in zip(lineas, resultantes):
        db.session.add(DetalleMovimiento(
            movimiento=movimiento,
            producto_id=linea["producto_id"],
            bodega_id=linea["bodega_id"],
            cantidad=linea["cantidad"],
            costo_unitario=linea.get("costo_unitario"),
            precio_unitario=linea.get("precio_unitario"),
            saldo_resultante=saldo,
        ))
    db.session.commit()
    return movimiento


# ------------------------------------------------------------- alertas RF09
def estado_alerta(stock_total, stock_minimo):
    if stock_minimo is None:
        return "SIN_UMBRAL"
    if stock_total == 0:
        return "AGOTADO"
    if stock_total <= stock_minimo * 0.5:
        return "CRITICO"
    if stock_total < stock_minimo:
        return "BAJO"
    return "OK"


def stock_de_producto(producto_id, existencias=None, umbral=None):
    if existencias is None:
        existencias = Existencia.query.filter_by(producto_id=producto_id).all()
    if umbral is None:
        registro = db.session.get(UmbralStock, producto_id)
        umbral = registro.stock_minimo if registro else None
    total = sum(e.cantidad for e in existencias)
    return {
        "producto_id": producto_id,
        "stock_total": total,
        "stock_minimo_configurado": umbral,
        "estado_alerta": estado_alerta(total, umbral),
        "desglose_bodegas": [
            {"bodega_id": e.bodega_id, "nombre": e.bodega.nombre, "cantidad": e.cantidad}
            for e in sorted(existencias, key=lambda x: x.bodega_id)
            if e.cantidad > 0
        ],
    }
