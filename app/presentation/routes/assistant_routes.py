from flask import Blueprint, current_app, redirect, render_template, request, session, url_for

bp = Blueprint("assistant", __name__)


def _services():
    return current_app.extensions["services"]


@bp.route("/", methods=["GET", "POST"])
def index():
    if "chat" not in session:
        session["chat"] = []

    if request.method == "POST":
        pregunta = request.form["pregunta"]
        respuesta = _services().assistant_service.respond(pregunta, session)
        historial = session["chat"]
        historial.append({"tipo": "usuario", "mensaje": pregunta})
        historial.append({"tipo": "bot", "mensaje": respuesta})
        session["chat"] = historial

    return render_template("index.html", chat=session["chat"])


@bp.route("/clear")
def clear_chat():
    session["chat"] = []
    return redirect(url_for("assistant.index"))
