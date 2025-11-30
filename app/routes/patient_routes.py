from datetime import datetime, timedelta

from flask import Blueprint,render_template,request,redirect,url_for,flash,session

from app.models import Doctor,Appointment,Patient,Treatment,Department,StatusEnum
from app.database import db

patient_bp = Blueprint("patient", __name__, url_prefix="/patient")


# ---------- Session guard ----------

@patient_bp.before_request
def before_request():
    user_id = session.get("user_id")
    last_seen = session.get("last_seen")

    if not user_id or session.get("user_role") != "patient":
        return redirect(url_for("auth.login"))

    now = datetime.utcnow()
    SESSION_TIMEOUT = timedelta(minutes=30)

    if last_seen:
        last_seen_dt = datetime.strptime(last_seen, "%Y-%m-%d %H:%M:%S")
        if now - last_seen_dt > SESSION_TIMEOUT:
            session.clear()
            return redirect(url_for("auth.login"))

    patient = Patient.query.get(user_id)
    if not patient:
        session.clear()
        return redirect(url_for("auth.login"))

    session["patient_name"] = patient.name
    session["last_seen"] = now.strftime("%Y-%m-%d %H:%M:%S")


# ---------- Dashboard ----------

@patient_bp.route("/dashboard")
def dashboard():
    patient_id = session.get("user_id")
    now = datetime.utcnow()

    upcoming_appointments = (
        Appointment.query
        .filter(
            Appointment.patient_id == patient_id,
            Appointment.status == StatusEnum.booked,
            Appointment.appointment_start >= now,
        )
        .order_by(Appointment.appointment_start.asc())
        .all()
    )

    past_appointments = (
        Appointment.query
        .filter(
            Appointment.patient_id == patient_id,
            Appointment.status.in_([StatusEnum.completed, StatusEnum.cancelled]),
        )
        .order_by(Appointment.appointment_start.desc())
        .all()
    )

    # Departments for dashboard listing
    departments = Department.query.order_by(Department.name.asc()).all()

    return render_template(
        "patient/dashboard.html",
        upcoming_appointments=upcoming_appointments,
        past_appointments=past_appointments,
        departments=departments,
        patient_name=session.get("patient_name"),
    )


# ---------- Search doctors (name/specialization/department) ----------

@patient_bp.route("/doctors")
def list_doctors():
    dept_id = request.args.get("department_id", "").strip()
    q = request.args.get("q", "").strip()

    doctors_query = Doctor.query.filter(Doctor.status == StatusEnum.active)

    if dept_id:
        doctors_query = doctors_query.filter(Doctor.department_id == int(dept_id))
    if q:
        like = f"%{q}%"
        doctors_query = doctors_query.filter(Doctor.name.ilike(like))

    doctors = doctors_query.order_by(Doctor.name.asc()).all()
    departments = Department.query.order_by(Department.name.asc()).all()

    return render_template(
        "patient/doctors.html",
        doctors=doctors,
        departments=departments,
        selected_department=dept_id,
        query=q,
    )


# ---------- Book appointment ----------

@patient_bp.route("/book-appointment", methods=["GET", "POST"])
def book_appointment():
    patient = Patient.query.get(session.get("user_id"))
    doctors = Doctor.query.filter(Doctor.status == StatusEnum.active).all()

    if request.method == "POST":
        doctor_id = request.form.get("doctor_id")
        appointment_dt_str = request.form.get("appointment_date")
        reason = request.form.get("reason", "").strip()

        if not (doctor_id and appointment_dt_str and reason):
            flash("Please fill in all fields.", "warning")
            return render_template(
                "admin/book_appointment.html",
                doctors=doctors,
                patient=patient,
            )

        try:
            appointment_start = datetime.fromisoformat(appointment_dt_str)
        except ValueError:
            flash("Invalid date/time format.", "danger")
            return render_template(
                "admin/book_appointment.html",
                doctors=doctors,
                patient=patient,
            )

        if appointment_start <= datetime.utcnow():
            flash("Appointment time must be in the future.", "warning")
            return render_template(
                "admin/book_appointment.html",
                doctors=doctors,
                patient=patient,
            )

        # default duration: 50 minutes
        from datetime import timedelta as _td
        appointment_end = appointment_start + _td(minutes=50)

        # Check for doctor double-booking
        conflict = Appointment.query.filter_by(
            doctor_id=int(doctor_id),
            appointment_start=appointment_start,
        ).first()
        if conflict:
            flash("The doctor already has an appointment at this time.", "danger")
            return render_template(
                "admin/book_appointment.html",
                doctors=doctors,
                patient=patient,
            )

        new_appointment = Appointment(
            patient_id=patient.id,
            doctor_id=int(doctor_id),
            appointment_start=appointment_start,
            appointment_end=appointment_end,
            reason=reason,
            status=StatusEnum.booked,
        )

        db.session.add(new_appointment)
        db.session.commit()
        flash("Appointment booked successfully.", "success")
        return redirect(url_for("patient.dashboard"))

    return render_template(
        "admin/book_appointment.html", doctors=doctors, patient=patient
    )


# ---------- Profile ----------

@patient_bp.route("/profile", methods=["GET", "POST"])
def profile():
    patient = Patient.query.get_or_404(session.get("user_id"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        gender = request.form.get("gender", "").strip()
        age = request.form.get("age", "").strip()

        if not (name and email and phone):
            flash("Name, email and phone are required.", "warning")
            return render_template("patient/profile.html", patient=patient)

        # email uniqueness check
        existing = Patient.query.filter(
            Patient.email == email, Patient.id != patient.id
        ).first()
        if existing:
            flash("Another patient with that email already exists.", "danger")
            return render_template("patient/profile.html", patient=patient)

        patient.name = name
        patient.email = email
        patient.phone = phone
        patient.gender = gender

        try:
            patient.age = int(age) if age else None
        except ValueError:
            flash("Age must be a valid number.", "warning")
            return render_template("patient/profile.html", patient=patient)

        db.session.commit()
        session["patient_name"] = patient.name
        flash("Profile updated successfully.", "success")
        return redirect(url_for("patient.profile"))

    return render_template("patient/profile.html", patient=patient)


# ---------- Treatment history ----------

@patient_bp.route("/treatments")
def treatments():
    patient_id = session.get("user_id")

    # Treatments are linked via Appointment -> Patient
    treatments = (
        Treatment.query
        .join(Appointment)
        .filter(Appointment.patient_id == patient_id)
        .order_by(Treatment.treatment_date.desc())
        .all()
    )

    return render_template("patient/treatments.html", treatments=treatments)
