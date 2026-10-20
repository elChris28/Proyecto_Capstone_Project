from flask import Blueprint, current_app, jsonify, redirect, render_template, request, url_for

bp = Blueprint("prediction", __name__)


def _services():
    return current_app.extensions["services"]


@bp.route("/predicciones-stock")
def predicciones_stock():
    resumen = _services().prediction_service.summary()
    historial = _services().evaluation_service.latest(limite=6)
    return render_template(
        "predicciones_stock.html",
        resumen=resumen,
        productos=resumen["productos"],
        historial_evaluaciones=historial,
        evaluacion_guardada=request.args.get("evaluacion"),
        error_guardado=request.args.get("error"),
    )


@bp.route("/predicciones-stock/registrar-evaluacion", methods=["POST"])
def registrar_evaluacion_stock():
    evaluacion_id = _services().evaluation_service.register_current()
    if evaluacion_id is None:
        return redirect(url_for("prediction.predicciones_stock", error="1"))
    return redirect(url_for("prediction.predicciones_stock", evaluacion=evaluacion_id))


@bp.route("/api/alertas-riesgo")
def api_alertas_riesgo():
    return jsonify(_services().alert_service.bell_summary())


@bp.route("/api/predicciones-stock")
def api_predicciones_stock():
    dias = request.args.get("dias", default=7, type=int)
    if dias != 7:
        return jsonify({
            "error": "Por ahora el modelo está entrenado únicamente para un horizonte de 7 días."
        }), 400
    return jsonify(_services().prediction_service.summary())


@bp.route("/api/predicciones-stock/<producto_id>")
def api_prediccion_stock_producto(producto_id):
    detalle = _services().prediction_service.product_detail(producto_id)
    if detalle is None:
        return jsonify({"error": "Producto no encontrado o sin historial suficiente."}), 404
    return jsonify(detalle)


@bp.route("/calidad-datos")
def calidad_datos():
    auditoria = _services().data_quality_service.audit()
    return render_template("calidad_datos.html", auditoria=auditoria)


@bp.route("/api/calidad-datos")
def api_calidad_datos():
    return jsonify(_services().data_quality_service.audit())
