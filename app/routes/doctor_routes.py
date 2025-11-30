from datetime import datetime, timedelta

from flask import Blueprint,render_template,request,redirect,url_for,flash,session

from app.models import Appointment, Doctor, Patient, Treatment, StatusEnum
from app.database import db

doctor_bp = Blueprint("doctor", __name__, url_prefix="/doctor")


@doctor_bp.before_request
def before_request():
    doctor_id = session.get("user_id")
    last_seen = session.get("last_seen")

    if not doctor_id or session.get("user_role") != "doctor":
        return redirect(url_for("auth.login"))

    now = datetime.utcnow()
    SESSION_TIMEOUT = timedelta(minutes=30)

    if last_seen:
        last_seen_dt = datetime.strptime(last_seen, "%Y-%m-%d %H:%M:%S")
        if now - last_seen_dt > SESSION_TIMEOUT:
            session.clear()
            return redirect(url_for("auth.login"))

    doctor = Doctor.query.get(doctor_id)
    if not doctor:
        session.clear()
        return redirect(url_for("auth.login"))

    session["doctor_name"] = doctor.name
    session["last_seen"] = now.strftime("%Y-%m-%d %H:%M:%S")


# ---------- Dashboard ----------

@doctor_bp.route("/dashboard")
def dashboard():
    doctor_id = session.get("user_id")
    now = datetime.utcnow()

    upcoming_appointments = (
        Appointment.query
        .filter(
            Appointment.doctor_id == doctor_id,
            Appointment.status == StatusEnum.booked,
            Appointment.appointment_start >= now,
        )
        .order_by(Appointment.appointment_start.asc())
        .all()
    )

    return render_template(
        "doctor/dashboard.html",
        appointments=upcoming_appointments,
        doctor_name=session.get("doctor_name"),
    )


# ---------- Appointment status update (Booked -> Completed/Cancelled) ----------

@doctor_bp.route("/appointment/<int:appointment_id>/status", methods=["POST"])
def update_appointment_status(appointment_id):
    doctor_id = session.get("user_id")
    appointment = Appointment.query.get_or_404(appointment_id)

    if appointment.doctor_id != doctor_id:
        flash("You are not allowed to modify this appointment.", "danger")
        return redirect(url_for("doctor.dashboard"))

    new_status = request.form.get("status", "").strip().lower()
    if new_status not in StatusEnum.__members__:
        flash("Invalid status.", "warning")
        return redirect(url_for("doctor.dashboard"))

    # Only allow transition from Booked to Completed/Cancelled
    if appointment.status != StatusEnum.booked:
        flash("Only booked appointments can be updated.", "warning")
        return redirect(url_for("doctor.dashboard"))

    if new_status not in ("completed", "cancelled"):
        flash("Only 'completed' or 'cancelled' are allowed here.", "warning")
        return redirect(url_for("doctor.dashboard"))

    appointment.status = StatusEnum[new_status]
    db.session.commit()
    flash("Appointment status updated.", "success")
    return redirect(url_for("doctor.dashboard"))


# ---------- Add / edit treatment for an appointment ----------

@doctor_bp.route("/appointment/<int:appointment_id>/treatment", methods=["GET", "POST"])
def add_treatment(appointment_id):
    doctor_id = session.get("user_id")
    appointment = Appointment.query.get_or_404(appointment_id)

    if appointment.doctor_id != doctor_id:
        flash("You are not allowed to modify this appointment.", "danger")
        return redirect(url_for("doctor.dashboard"))

    if request.method == "POST":
        diagnosis = request.form.get("diagnosis", "").strip()
        prescription = request.form.get("prescription", "").strip()
        notes = request.form.get("notes", "").strip()

        if not diagnosis:
            flash("Diagnosis is required.", "warning")
            return render_template(
                "doctor/treatment_form.html",
                appointment=appointment,
                treatment=appointment.treatment,
            )

        # If treatment exists, update; else create
        treatment = appointment.treatment
        if treatment is None:
            treatment = Treatment(
                appointment_id=appointment.id,
                treatment_date=datetime.utcnow(),
                diagnosis=diagnosis,
                prescription=prescription or None,
                notes=notes or None,
            )
            db.session.add(treatment)
        else:
            treatment.diagnosis = diagnosis
            treatment.prescription = prescription or None
            treatment.notes = notes or None
            treatment.treatment_date = datetime.utcnow()

        # Mark appointment as completed
        appointment.status = StatusEnum.completed
        db.session.commit()
        flash("Treatment details saved.", "success")
        return redirect(url_for("doctor.dashboard"))

    return render_template(
        "doctor/treatment_form.html",
        appointment=appointment,
        treatment=appointment.treatment,
    )


# ---------- Patients assigned to doctor ----------

@doctor_bp.route("/patients")
def manage_patients():
    doctor_id = session.get("user_id")

    patients = (
        Patient.query
        .join(Appointment)
        .filter(Appointment.doctor_id == doctor_id)
        .distinct()
        .order_by(Patient.name.asc())
        .all()
    )

    return render_template("doctor/patients.html", patients=patients)


# ---------- Patient history for this doctor ----------

@doctor_bp.route("/patient/<int:patient_id>/history")
def patient_history(patient_id):
    doctor_id = session.get("user_id")

    treatments = (
        Treatment.query
        .join(Appointment)
        .filter(
            Appointment.patient_id == patient_id,
            Appointment.doctor_id == doctor_id,
        )
        .order_by(Treatment.treatment_date.desc())
        .all()
    )

    patient = Patient.query.get_or_404(patient_id)

    return render_template(
        "doctor/patient_history.html",
        treatments=treatments,
        patient=patient,
    )
