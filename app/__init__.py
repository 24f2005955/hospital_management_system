from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
import os
from app.routes.auth_routes import auth_bp
from app.routes.admin_routes import admin_bp
from app.routes.doctor_routes import doctor_bp
from app.routes.patient_routes import patient_bp
from app.routes import home_bp
from app.database import db
from .utils import format_datetime

def create_app():
    app = Flask(__name__)
    app.jinja_env.filters['format_datetime'] = format_datetime

    # Configuration
    BASEDIR = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASEDIR, 'hospital.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = '123'  # Change this to a secure key in production

    # Initialize extensions
    db.init_app(app)

    with app.app_context():
        db.create_all()
        create_default_admin()

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(doctor_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(home_bp)

    return app

def create_default_admin():
    from .models import Admin
    admin_exists = Admin.query.first()
    if not admin_exists:
        default_admin = Admin(
            username='admin',
            email='admin@hospital.com',
            password=generate_password_hash('admin123')  # Securely hash password
        )
        db.session.add(default_admin)
        db.session.commit()
        print("Default admin created: username='admin', password='admin123'")
