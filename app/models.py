from datetime import datetime, date, time
import enum

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Enum, UniqueConstraint
from app.database import db
from app.utils import hash_password


# ---------- Enums ----------

class StatusEnum(enum.Enum):
    booked = "Booked"
    completed = "Completed"
    cancelled = "Cancelled"
    active = "Active"
    inactive = "Inactive"
    blacklisted = "Blacklisted"


class UserRole(enum.Enum):
    admin = "Admin"
    doctor = "Doctor"
    patient = "Patient"


# ---------- Department / Specialization ----------

class Department(db.Model):
    __tablename__ = "department"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)

    # Number of doctors can be derived by counting doctors in this department,
    # but a cached integer column is allowed by your brief; kept nullable here.
    doctors_count = db.Column(db.Integer, default=0)

    doctors = db.relationship("Doctor", back_populates="department", lazy=True)

    def __repr__(self):
        return f"<Department {self.name}>"


# ---------- Core Users ----------

class Admin(db.Model):
    __tablename__ = "admin"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(Enum(StatusEnum), default=StatusEnum.active, nullable=False)

    role = db.Column(Enum(UserRole), default=UserRole.admin, nullable=False)

    def __repr__(self):
        return f"<Admin {self.username}>"


class Doctor(db.Model):
    __tablename__ = "doctor"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    phone = db.Column(db.String(20), nullable=True)

    department_id = db.Column(db.Integer, db.ForeignKey("department.id"), nullable=False)
    department = db.relationship("Department", back_populates="doctors")

    bio = db.Column(db.Text, nullable=True)  # profile / about doctor
    years_of_experience = db.Column(db.Integer, nullable=True)

    status = db.Column(Enum(StatusEnum), default=StatusEnum.active, nullable=False)
    role = db.Column(Enum(UserRole), default=UserRole.doctor, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    schedules = db.relationship(
        "DoctorSchedule",
        back_populates="doctor",
        cascade="all, delete-orphan",
        lazy=True,
    )
    time_offs = db.relationship(
        "DoctorTimeOff",
        back_populates="doctor",
        cascade="all, delete-orphan",
        lazy=True,
    )
    appointments = db.relationship(
        "Appointment",
        back_populates="doctor",
        lazy=True,
    )

    def __repr__(self):
        return f"<Doctor {self.name}>"


class Patient(db.Model):
    __tablename__ = "patient"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    age = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.String(10), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)

    status = db.Column(Enum(StatusEnum), default=StatusEnum.active, nullable=False)
    role = db.Column(Enum(UserRole), default=UserRole.patient, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)

    appointments = db.relationship(
        "Appointment",
        back_populates="patient",
        lazy=True,
    )

    def __repr__(self):
        return f"<Patient {self.name}>"


# ---------- Doctor availability (next 7 days, recurring) ----------

class DoctorSchedule(db.Model):
    """
    Recurring weekly schedule block for a doctor (e.g. Monday 09:00–13:00).
    Use this plus DoctorTimeOff to compute availability for the coming 7 days.
    """
    __tablename__ = "doctor_schedule"

    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctor.id"), nullable=False)

    weekday = db.Column(db.Integer, nullable=False)

    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)

    max_patients = db.Column(db.Integer, nullable=True)  

    doctor = db.relationship("Doctor", back_populates="schedules")

    __table_args__ = (
        UniqueConstraint(
            "doctor_id",
            "weekday",
            "start_time",
            "end_time",
            name="uq_doctor_weekday_time_block",
        ),
    )

    def __repr__(self):
        return (
            f"<DoctorSchedule doc={self.doctor_id} "
            f"weekday={self.weekday} {self.start_time}-{self.end_time}>"
        )


class DoctorTimeOff(db.Model):
    """
    AI generated
    One-off exceptions to the recurring schedule (vacation, leave, etc.).
    Either entire day (start_time/end_time = NULL) or a partial window.
    """
    __tablename__ = "doctor_time_off"

    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctor.id"), nullable=False)

    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=True)
    end_time = db.Column(db.Time, nullable=True)

    reason = db.Column(db.String(255), nullable=True)

    doctor = db.relationship("Doctor", back_populates="time_offs")

    __table_args__ = (
        UniqueConstraint(
            "doctor_id",
            "date",
            "start_time",
            "end_time",
            name="uq_doctor_time_off_block",
        ),
    )

    def __repr__(self):
        return f"<DoctorTimeOff doc={self.doctor_id} {self.date}>"


# ---------- Appointments and slots ----------

class Appointment(db.Model):
    __tablename__ = "appointment"

    id = db.Column(db.Integer, primary_key=True)

    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctor.id"), nullable=False)

    # full DateTime (used for uniqueness + schedule queries)
    appointment_start = db.Column(db.DateTime, nullable=False)
    appointment_end = db.Column(db.DateTime, nullable=False)

    status = db.Column(Enum(StatusEnum), default=StatusEnum.booked, nullable=False)

    reason = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # For rescheduling tracking
    last_updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    patient = db.relationship("Patient", back_populates="appointments")
    doctor = db.relationship("Doctor", back_populates="appointments")
    treatment = db.relationship(
        "Treatment",
        back_populates="appointment",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "doctor_id",
            "appointment_start",
            name="uq_doctor_appointment_start",
        ),
    )

    def __repr__(self):
        return f"<Appointment {self.id} doc={self.doctor_id} pat={self.patient_id}>"


class TimeSlot(db.Model):
    """
    AI generated
    Optional helper table if you want explicit slots (e.g. every 15 minutes)
    for the next 7 days. A NULL appointment_id means the slot is free.
    You can generate these from DoctorSchedule + DoctorTimeOff in a cron/task.
    """
    __tablename__ = "time_slot"

    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctor.id"), nullable=False)

    start = db.Column(db.DateTime, nullable=False)
    end = db.Column(db.DateTime, nullable=False)

    appointment_id = db.Column(db.Integer, db.ForeignKey("appointment.id"), nullable=True)

    doctor = db.relationship("Doctor", lazy=True)
    appointment = db.relationship("Appointment", lazy=True)

    __table_args__ = (
        UniqueConstraint("doctor_id", "start", name="uq_doctor_slot_start"),
    )

    def __repr__(self):
        return f"<TimeSlot doc={self.doctor_id} {self.start}-{self.end}>"


# ---------- Treatment / medical history ----------

class Treatment(db.Model):
    __tablename__ = "treatment"

    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey("appointment.id"), nullable=False)

    diagnosis = db.Column(db.Text, nullable=True)
    prescription = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)

    treatment_date = db.Column(db.DateTime, default=datetime.utcnow)

    appointment = db.relationship("Appointment", back_populates="treatment")

    def __repr__(self):
        return f"<Treatment {self.id} appt={self.appointment_id}>"


# ---------- Utility: programmatic admin creation ----------

def create_default_admin(username: str = "admin", email: str = "admin@example.com", password_hash: str = "admin"):

    existing = Admin.query.filter(
        (Admin.username == username) | (Admin.email == email)
    ).first()
    if existing:
        return existing

    admin = Admin(
        username=username,
        email=email,
        password_hash=hash_password(password_hash),
        status=StatusEnum.active,
    )
    db.session.add(admin)
    db.session.commit()
    return admin
