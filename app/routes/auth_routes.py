import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request,session
from app.models import Admin, Doctor, Patient
from app.forms import LoginForm, PatientRegistrationForm
from app.utils import verify_password
from app.database import db

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    email = request.form.get('username')
    password = request.form.get('password')
    print(email, password)
    role='admin'
    user = Admin.query.filter_by(email=email).first()
    if not user:
        user = Doctor.query.filter_by(email=email).first()
        role='doctor'
        if not user:
            user = Patient.query.filter_by(email=email).first()
            role='patient'
    
    if user and verify_password(user.password, password):
        flash('Logged in successfully.', 'success')
        set_user_session(user, role)

        if isinstance(user, Admin):
            return redirect(url_for('admin.dashboard'))
        elif isinstance(user, Doctor):
            return redirect(url_for('doctor.dashboard'))
        else:
            return redirect(url_for('patient.dashboard'))
    
    return render_template('auth/login.html')

def set_user_session(user, role):
    session['user_id'] = user.id
    session['user_role'] = role
    session['last_seen'] = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    user = session.get('user_id')
    role = session.get('user_role')
    if user:
        if role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif role == 'doctor':
            return redirect(url_for('doctor.dashboard'))
        elif role == 'patient':
            return redirect(url_for('patient.dashboard'))

    name = request.form.get('name')
    email = request.form.get('email')
    gender = request.form.get('gender')
    age = request.form.get('age')
    phone = request.form.get('phone')
    password = request.form.get('password')
    
    if request.method == 'POST':
        existing_user = Patient.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered.', 'error')
        else:
            new_patient = Patient(
                name=name,
                age=age,
                gender=gender,
                phone=phone,
                email=email,
                status='active',
                password=generate_password_hash(password),
            )
            db.session.add(new_patient)
            db.session.commit()
            flash('Registration successful. Please log in.', 'success')
            return redirect(url_for('auth.login'))
    return render_template('auth/register.html')
