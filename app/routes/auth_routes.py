from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import Admin, Doctor, Patient
from app.forms import LoginForm, PatientRegistrationForm
from app.utils import verify_password
from app.database import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard'))  # Or role-based redirect

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        # Check if user is Admin
        user = Admin.query.filter_by(email=email).first()
        role = 'admin'
        if not user:
            user = Doctor.query.filter_by(email=email).first()
            role = 'doctor'
        if not user:
            user = Patient.query.filter_by(email=email).first()
            role = 'patient'

        if user and verify_password(user.password, password):
            login_user(user)
            flash('Logged in successfully.', 'success')
            # Redirect based on role - customize this logic
            if role == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif role == 'doctor':
                return redirect(url_for('doctor.dashboard'))
            else:
                return redirect(url_for('patient.dashboard'))
        else:
            flash('Invalid email or password', 'danger')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    # Only patients register here; Admins and Doctors added by admin
    if current_user.is_authenticated:
        return redirect(url_for('patient.dashboard'))
    form = PatientRegistrationForm()
    if form.validate_on_submit():
        new_patient = Patient(
            name=form.name.data,
            age=form.age.data,
            gender=form.gender.data,
            email=form.email.data,
            phone=form.phone.data,
            status='Active',
            password=generate_password_hash(form.password.data)
        )
        db.session.add(new_patient)
        db.session.commit()
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form)
