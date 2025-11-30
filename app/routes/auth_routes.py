import datetime

from flask import Blueprint,render_template,redirect,url_for,flash,request, session

from app.models import Admin, Doctor, Patient, StatusEnum
from app.utils import verify_password, hash_password
from app.database import db

auth_bp = Blueprint("auth", __name__)


# ---------- Helpers ----------

def set_user_session(user, role: str):
    session["user_id"] = user.id
    session["user_role"] = role  # "admin", "doctor", "patient"
    session["last_seen"] = datetime.datetime.utcnow().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


# ---------- Login ----------

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not (email and password):
            flash("Please enter both email and password.", "warning")
            return render_template("auth/login.html")

        user = None
        role = None

        user = Admin.query.filter_by(email=email).first()
        if user:
            role = "admin"
        else:
            # Try Doctor
            user = Doctor.query.filter_by(email=email).first()
            if user:
                role = "doctor"
            else:
                # Try Patient
                user = Patient.query.filter_by(email=email).first()
                if user:
                    role = "patient"

        if not user:
            flash("Invalid credentials.", "danger")
            return render_template("auth/login.html")

        if hasattr(user, "status") and user.status in (StatusEnum.inactive, StatusEnum.blacklisted):
            flash("Your account is not active. Please contact admin.", "danger")
            return render_template("auth/login.html")

        stored_hash = getattr(user, "password_hash", None)
        if not stored_hash or not verify_password(stored_hash, password):
            flash("Invalid credentials.", "danger")
            return render_template("auth/login.html")

        set_user_session(user, role)
        flash("Logged in successfully.", "success")

        if role == "admin":
            return redirect(url_for("admin.dashboard"))
        if role == "doctor":
            return redirect(url_for("doctor.dashboard"))
        return redirect(url_for("patient.dashboard"))

    return render_template("auth/login.html")


# ---------- Logout ----------

@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("auth.login"))


# ---------- Patient registration ----------

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    user_id = session.get("user_id")
    role = session.get("user_role")
    if user_id and role:
        if role == "admin":
            return redirect(url_for("admin.dashboard"))
        if role == "doctor":
            return redirect(url_for("doctor.dashboard"))
        if role == "patient":
            return redirect(url_for("patient.dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        gender = request.form.get("gender", "").strip()
        age = request.form.get("age", "").strip()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "").strip()
        confirm = request.form.get("confirm_password", "").strip()

        if not (name and email and gender and age and phone and password and confirm):
            flash("Please fill in all fields.", "warning")
            return render_template("auth/register.html")

        if password != confirm:
            flash("Passwords do not match.", "warning")
            return render_template("auth/register.html")

        try:
            age_val = int(age)
        except ValueError:
            flash("Age must be a valid number.", "warning")
            return render_template("auth/register.html")

        existing_user = Patient.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already registered.", "danger")
            return render_template("auth/register.html")

        new_patient = Patient(
            name=name,
            age=age_val,
            gender=gender,
            phone=phone,
            email=email,
            status=StatusEnum.active,
            password_hash=hash_password(password),
        )

        db.session.add(new_patient)
        db.session.commit()
        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")
