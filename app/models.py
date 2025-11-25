from datetime import datetime
from sqlalchemy import Enum
import enum
from flask_login import UserMixin
from app.database import db  # Assuming db is initialized in app/__init__.py

class StatusEnum(enum.Enum):
    booked = "Booked"
    completed = "Completed"
    cancelled = "Cancelled"
    active = "Active"
    inactive = "Inactive"
    blacklisted = "Blacklisted"

class Admin(db.Model, UserMixin):
    __tablename__ = 'admin'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Admin {self.username}>'

class Doctor(db.Model, UserMixin):
    __tablename__ = 'doctor'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    specialty = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    availability = db.Column(db.String(200), nullable=False)  # Consider redesigning in future
    status = db.Column(Enum(StatusEnum), default=StatusEnum.active)

    def __repr__(self):
        return f'<Doctor {self.name}>'

class Patient(db.Model, UserMixin):
    __tablename__ = 'patient'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    status = db.Column(Enum(StatusEnum), default=StatusEnum.active)
    notes = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<Patient {self.name}>'

class Appointment(db.Model):
    __tablename__ = 'appointment'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    appointment_date = db.Column(db.DateTime, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(Enum(StatusEnum), default=StatusEnum.booked)

    patient = db.relationship('Patient', backref=db.backref('appointments', lazy=True))
    doctor = db.relationship('Doctor', backref=db.backref('appointments', lazy=True))

    __table_args__ = (
        db.UniqueConstraint('doctor_id', 'appointment_date', name='unique_doctor_appointment'),
    )

    def __repr__(self):
        return f'<Appointment {self.id}>'

class Treatment(db.Model):
    __tablename__ = 'treatment'
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=False)
    treatment_date = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.Text, nullable=False)
    outcome = db.Column(db.String(200), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    prescription = db.Column(db.Text, nullable=True)

    appointment = db.relationship('Appointment', backref=db.backref('treatment', uselist=False))

    def __repr__(self):
        return f'<Treatment {self.id}>'
