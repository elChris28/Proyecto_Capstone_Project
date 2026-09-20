from __future__ import annotations

from pathlib import Path


def create_app():
    """Application Factory de Flask.

    Los imports dependientes de Flask y de infraestructura se realizan dentro
    de la fábrica para que módulos offline (entrenamiento/análisis) puedan
    reutilizar utilidades del paquete sin inicializar la aplicación web.
    """
    from flask import Flask

    from app.container import ServiceContainer
    from app.presentation.routes.assistant_routes import bp as assistant_bp
    from app.presentation.routes.dashboard_routes import bp as dashboard_bp
    from app.presentation.routes.prediction_routes import bp as prediction_bp

    base = Path(__file__).resolve().parent
    app = Flask(
        __name__,
        template_folder=str(base / "presentation" / "templates"),
        static_folder=str(base / "presentation" / "static"),
        static_url_path="/static",
    )

    from config import SECRET_KEY

    app.secret_key = SECRET_KEY
    app.extensions["services"] = ServiceContainer()

    app.register_blueprint(assistant_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(prediction_bp)

    return app
