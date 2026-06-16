from flask import Flask, render_template, request, session, redirect, url_for

from config import SECRET_KEY
from predictor import metricas
from asistente import asistente

from database import (
    obtener_total_consultas,
    obtener_consultas_por_intencion,
    obtener_productos_mas_buscados,
    obtener_stock_critico,
    obtener_productos_por_vencer
)


app = Flask(__name__)
app.secret_key = SECRET_KEY


@app.route("/", methods=["GET", "POST"])
def index():

    if "chat" not in session:
        session["chat"] = []

    if request.method == "POST":
        pregunta = request.form["pregunta"]
        respuesta = asistente(pregunta, session)

        historial = session["chat"]

        historial.append({
            "tipo": "usuario",
            "mensaje": pregunta
        })

        historial.append({
            "tipo": "bot",
            "mensaje": respuesta
        })

        session["chat"] = historial

    return render_template(
        "index.html",
        chat=session["chat"]
    )


@app.route("/dashboard")
def dashboard():

    total_consultas = obtener_total_consultas()
    consultas_por_intencion = obtener_consultas_por_intencion()
    productos_mas_buscados = obtener_productos_mas_buscados()
    stock_critico = obtener_stock_critico()
    productos_por_vencer = obtener_productos_por_vencer()

    # 🔥 FIX CRÍTICO PARA GRÁFICO
    labels = []
    values = []

    if consultas_por_intencion:
        labels = [item[0] for item in consultas_por_intencion]
        values = [item[1] for item in consultas_por_intencion]

    return render_template(
        "dashboard.html",
        accuracy=round(metricas["accuracy"] * 100, 2),
        precision=round(metricas["precision"] * 100, 2),
        recall=round(metricas["recall"] * 100, 2),
        f1=round(metricas["f1"] * 100, 2),

        total_consultas=total_consultas,
        consultas_por_intencion=consultas_por_intencion,
        productos_mas_buscados=productos_mas_buscados,
        stock_critico=stock_critico,
        productos_por_vencer=productos_por_vencer,
        labels=labels,
        values=values
    )

@app.route("/clear")
def clear_chat():
    session["chat"] = []
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)