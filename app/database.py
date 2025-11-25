from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash

# Initialize SQLAlchemy db instance (import this in models and app factory)
db = SQLAlchemy()
