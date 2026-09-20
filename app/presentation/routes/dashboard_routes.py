from flask import Blueprint, current_app, render_template

bp = Blueprint("dashboard", __name__)


@bp.route("/dashboard")
def dashboard():
    data = current_app.extensions["services"].dashboard_service.data()
    return render_template("dashboard.html", **data)
