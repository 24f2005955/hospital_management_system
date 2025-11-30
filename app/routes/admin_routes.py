from datetime import datetime, timedelta
from flask import Blueprint,render_template, request, redirect, url_for,flash,session
from app.utils import hash_password           
from app.database import db
from app.models import Admin,Doctor,Patient,Appointment,Department, StatusEnum

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# ---------- helper functions ----------
def require_admin():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    admin = Admin.query.get(user_id)
    if not admin or admin.role.name.lower() != "admin":
        session.clear()
        return redirect(url_for("auth.login"))

    return admin

@admin_bp.before_request
def before_request():
    # auth
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    last_seen = session.get("last_seen")
    now = datetime.utcnow()
    SESSION_TIMEOUT = timedelta(minutes=30)

    if last_seen:
        last_seen_dt = datetime.strptime(last_seen, "%Y-%m-%d %H:%M:%S")
        if now - last_seen_dt > SESSION_TIMEOUT:
            session.clear()
            return redirect(url_for("auth.login"))

    user = Admin.query.get(user_id)
    if not user:
        session.clear()
        return redirect(url_for("auth.login"))

    session["last_seen"] = now.strftime("%Y-%m-%d %H:%M:%S")


# ---------- Dashboard ----------

@admin_bp.route("/dashboard")
def dashboard():
    doctors_count = Doctor.query.count()
    patients_count = Patient.query.count()
    appointments_count = Appointment.query.count()

    upcoming_appointments = (
        Appointment.query
        .filter(Appointment.appointment_start >= datetime.utcnow())
        .order_by(Appointment.appointment_start.asc())
        .limit(10)
        .all()
    )

    return render_template(
        "admin/dashboard.html",
        doctors_count=doctors_count,
        patients_count=patients_count,
        appointments_count=appointments_count,
        upcoming_appointments=upcoming_appointments,
    )


# ---------- Doctor management ----------

@admin_bp.route("/doctors")
def search_doctors():
    query = request.args.get("query", "").strip()
    department_id = request.args.get("department_id", "").strip()

    doctors_query = Doctor.query

    if query:
        like = f"%{query}%"
        doctors_query = doctors_query.filter(
            (Doctor.name.ilike(like)) | (Doctor.email.ilike(like))
        )

    if department_id:
        doctors_query = doctors_query.filter(Doctor.department_id == int(department_id))

    all_doctors = doctors_query.order_by(Doctor.name.asc()).all()
    departments = Department.query.order_by(Department.name.asc()).all()

    return render_template(
        "admin/manage_doctors.html",
        doctors=all_doctors,
        departments=departments,
        selected_department=department_id,
        query=query,
    )


@admin_bp.route("/doctor/add", methods=["GET", "POST"])
def add_doctor():
    departments = Department.query.order_by(Department.name.asc()).all()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        department_id = request.form.get("department_id")
        status_str = request.form.get("status", "active").strip().lower()
        password = request.form.get("password", "").strip()
        bio = request.form.get("bio", "").strip()
        years_of_experience = request.form.get("years_of_experience", "").strip()

        if not (name and email and department_id and status_str and password):
            flash("Please fill in all required fields.", "warning")
            return render_template("admin/add_doctor.html", departments=departments)

        existing = Doctor.query.filter_by(email=email).first()
        if existing:
            flash("A doctor with that email already exists.", "danger")
            return render_template("admin/add_doctor.html", departments=departments)

        try:
            status = StatusEnum[status_str] if status_str in StatusEnum.__members__ else StatusEnum.active
        except KeyError:
            status = StatusEnum.active

        try:
            years_val = int(years_of_experience) if years_of_experience else None
        except ValueError:
            flash("Years of experience must be a number.", "warning")
            return render_template("admin/add_doctor.html", departments=departments)

        new_doctor = Doctor(
            name=name,
            email=email,
            phone=phone or None,
            department_id=int(department_id),
            status=status,
            password_hash=hash_password(password),
            bio=bio or None,
            years_of_experience=years_val,
        )

        db.session.add(new_doctor)
        db.session.commit()
        flash("Doctor profile added successfully.", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("admin/add_doctor.html", departments=departments)


@admin_bp.route("/doctor/edit/<int:doctor_id>", methods=["GET", "POST"])
def edit_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    departments = Department.query.order_by(Department.name.asc()).all()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        department_id = request.form.get("department_id")
        status_str = request.form.get("status", "").strip().lower()
        bio = request.form.get("bio", "").strip()
        years_of_experience = request.form.get("years_of_experience", "").strip()

        if not (name and email and department_id and status_str):
            flash("Please fill in all required fields.", "warning")
            return render_template(
                "admin/edit_doctor.html", doctor=doctor, departments=departments
            )

        existing = Doctor.query.filter(
            Doctor.email == email, Doctor.id != doctor.id
        ).first()
        if existing:
            flash("Another doctor with that email already exists.", "danger")
            return render_template(
                "admin/edit_doctor.html", doctor=doctor, departments=departments
            )

        try:
            status = StatusEnum[status_str] if status_str in StatusEnum.__members__ else doctor.status
        except KeyError:
            status = doctor.status

        doctor.name = name
        doctor.email = email
        doctor.phone = phone or None
        doctor.department_id = int(department_id)
        doctor.status = status
        doctor.bio = bio or None
        try:
            doctor.years_of_experience = int(years_of_experience) if years_of_experience else None
        except ValueError:
            flash("Years of experience must be a number.", "warning")
            return render_template(
                "admin/edit_doctor.html", doctor=doctor, departments=departments
            )

        # optional: allow resetting password
        new_password = request.form.get("password", "").strip()
        if new_password:
            doctor.password_hash = hash_password(new_password)

        db.session.commit()
        flash("Doctor profile updated successfully.", "success")
        return redirect(url_for("admin.search_doctors"))

    return render_template("admin/edit_doctor.html", doctor=doctor, departments=departments)


@admin_bp.route("/doctor/delete/<int:doctor_id>", methods=["POST"])
def delete_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    db.session.delete(doctor)
    db.session.commit()
    flash("Doctor profile deleted successfully.", "success")
    return redirect(url_for("admin.search_doctors"))


# ---------- Patient management ----------

@admin_bp.route("/patient/add", methods=["GET", "POST"])
def add_patient():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        age = request.form.get("age", "").strip()
        gender = request.form.get("gender", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        status_str = request.form.get("status", "active").strip().lower()
        password = request.form.get("password", "").strip()

        if not (name and age and gender and email and phone and status_str and password):
            flash("Please fill in all fields.", "warning")
            return render_template("admin/add_patient.html")

        try:
            age_val = int(age)
        except ValueError:
            flash("Age must be a valid number.", "warning")
            return render_template("admin/add_patient.html")

        existing = Patient.query.filter_by(email=email).first()
        if existing:
            flash("A patient with that email already exists.", "danger")
            return render_template("admin/add_patient.html")

        try:
            status = StatusEnum[status_str] if status_str in StatusEnum.__members__ else StatusEnum.active
        except KeyError:
            status = StatusEnum.active

        new_patient = Patient(
            name=name,
            age=age_val,
            gender=gender,
            email=email,
            phone=phone,
            status=status,
            password_hash=hash_password(password),
        )

        db.session.add(new_patient)
        db.session.commit()
        flash("Patient added successfully.", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("admin/add_patient.html")


@admin_bp.route("/patient/edit/<int:patient_id>", methods=["GET", "POST"])
def edit_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)

    if request.method == "POST":
        patient.name = request.form.get("name", "").strip()
        age = request.form.get("age", "").strip()
        patient.gender = request.form.get("gender", "").strip()
        patient.email = request.form.get("email", "").strip()
        patient.phone = request.form.get("phone", "").strip()
        status_str = request.form.get("status", "").strip().lower()

        try:
            patient.age = int(age) if age else None
        except ValueError:
            flash("Age must be a valid number.", "warning")
            return render_template("admin/edit_patient.html", patient=patient)

        if status_str in StatusEnum.__members__:
            patient.status = StatusEnum[status_str]

        new_password = request.form.get("password", "").strip()
        if new_password:
            patient.password_hash = hash_password(new_password)

        db.session.commit()
        flash("Patient updated successfully.", "success")
        return redirect(url_for("admin.search_patients"))

    return render_template("admin/edit_patient.html", patient=patient)


@admin_bp.route("/patient/delete/<int:patient_id>", methods=["POST"])
def delete_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    db.session.delete(patient)
    db.session.commit()
    flash("Patient deleted successfully.", "success")
    return redirect(url_for("admin.search_patients"))


@admin_bp.route("/patient/search", methods=["GET", "POST"])
def search_patients():
    patients = []
    if request.method == "POST":
        search_term = request.form.get("query", "").strip()
        if search_term:
            like = f"%{search_term}%"
            patients = Patient.query.filter(
                (Patient.name.ilike(like))
                | (Patient.email.ilike(like))
                | (Patient.phone.ilike(like))
            ).all()
            if not patients:
                flash("No patients found matching the search criteria.", "info")
        else:
            flash("Please enter a search term.", "warning")

    if not patients:
        patients = Patient.query.order_by(Patient.name.asc()).all()

    return render_template("admin/search_patient.html", patients=patients)


# ---------- Appointment management ----------

@admin_bp.route("/appointment/add", methods=["GET", "POST"])
def add_appointment():
    patients = Patient.query.filter(Patient.status == StatusEnum.active).all()
    doctors = Doctor.query.filter(Doctor.status == StatusEnum.active).all()

    if request.method == "POST":
        patient_id = request.form.get("patient_id")
        doctor_id = request.form.get("doctor_id")
        appointment_dt_str = request.form.get("appointment_date")  # 'YYYY-MM-DDTHH:MM'
        reason = request.form.get("reason", "").strip()

        if not (patient_id and doctor_id and appointment_dt_str and reason):
            flash("Please fill in all fields.", "warning")
            return render_template(
                "admin/book_appointment.html", patients=patients, doctors=doctors
            )

        try:
            appointment_start = datetime.fromisoformat(appointment_dt_str)
        except ValueError:
            flash("Invalid date/time format.", "danger")
            return render_template(
                "admin/book_appointment.html", patients=patients, doctors=doctors
            )

        # default duration: 50 minutes
        from datetime import timedelta as _td
        appointment_end = appointment_start + _td(minutes=50)

        # Prevent double booking for the same doctor at the same start time
        conflict = Appointment.query.filter_by(
            doctor_id=int(doctor_id),
            appointment_start=appointment_start,
        ).first()
        if conflict:
            flash("The doctor already has an appointment at this date and time.", "danger")
            return render_template(
                "admin/book_appointment.html", patients=patients, doctors=doctors
            )

        new_appointment = Appointment(
            patient_id=int(patient_id),
            doctor_id=int(doctor_id),
            appointment_start=appointment_start,
            appointment_end=appointment_end,
            reason=reason,
            status=StatusEnum.booked,
        )

        db.session.add(new_appointment)
        db.session.commit()
        flash("Appointment created successfully.", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template(
        "admin/book_appointment.html", patients=patients, doctors=doctors
    )

@admin_bp.route("/add_department", methods=["GET", "POST"])
def add_department():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()

        if not name:
            flash("Department name is required.", "warning")
            return render_template("admin/add_department.html")

        existing = Department.query.filter_by(name=name).first()
        if existing:
            flash("A department with that name already exists.", "danger")
            return render_template("admin/add_department.html")

        new_department = Department(
            name=name,
            description=description or None,
        )

        db.session.add(new_department)
        db.session.commit()
        flash("Department added successfully.", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("admin/add_department.html")

@admin_bp.route("/departments", methods=["GET", "POST"])
def search_departments():
    query = request.args.get("query", "").strip()

    departments_query = Department.query

    if query:
        like = f"%{query}%"
        departments_query = departments_query.filter(
            Department.name.ilike(like)
        )

    all_departments = departments_query.order_by(Department.name.asc()).all()

    return render_template(
        "admin/manage_departments.html",
        departments=all_departments,
        query=query,
    )

@admin_bp.route('edit_department/<int:department_id>', methods=['GET', 'POST'] )
def edit_department(department_id):
    department = Department.query.get_or_404(department_id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()

        if not name:
            flash("Department name is required.", "warning")
            return render_template("admin/edit_department.html", department=department)

        existing = Department.query.filter(
            Department.name == name, Department.id != department.id
        ).first()
        if existing:
            flash("Another department with that name already exists.", "danger")
            return render_template("admin/edit_department.html", department=department)

        department.name = name
        department.description = description or None

        db.session.commit()
        flash("Department updated successfully.", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("admin/edit_department.html", department=department)

@admin_bp.route("/delete_department/<int:department_id>", methods=["POST"])
def delete_department(department_id):
    department = Department.query.get_or_404(department_id)
    db.session.delete(department)
    db.session.commit()
    flash("Department deleted successfully.", "success")
    return redirect(url_for("admin.dashboard"))
