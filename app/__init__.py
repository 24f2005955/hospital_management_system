import os

from flask import Flask

from app.database import db
from app.routes.auth_routes import auth_bp
from app.routes.admin_routes import admin_bp
from app.routes.doctor_routes import doctor_bp
from app.routes.patient_routes import patient_bp
from app.routes import home_bp
from app.utils import format_datetime


def create_app():
    app = Flask(__name__)

    # Jinja filter
    app.jinja_env.filters["format_datetime"] = format_datetime

    # ---------- Config ----------
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(
        basedir, "hospital.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = "change-this-secret-key"

    # ---------- Extensions ----------
    db.init_app(app)

    # ---------- Blueprints ----------
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(doctor_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(home_bp)

    # ---------- DB + default admin ----------
    with app.app_context():
        from app.models import create_default_admin  # uses same db instance

        db.create_all()
        create_default_admin()  # uses db.session bound to this app

    return app
