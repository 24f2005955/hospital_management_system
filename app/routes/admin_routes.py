from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import Doctor, Patient, Appointment
from app.forms import DoctorForm
from datetime import datetime
from app.database import db

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    # Decorator to allow access only to admin users - implement based on your auth system
    pass

@admin_bp.route('/dashboard')
@login_required
# Add @admin_required decorator here after implementation
def dashboard():
    doctors_count = Doctor.query.count()
    patients_count = Patient.query.count()
    appointments_count = Appointment.query.count()
    return render_template('admin/dashboard.html', doctors_count=doctors_count,
                           patients_count=patients_count, appointments_count=appointments_count)

@admin_bp.route('/doctors')
@login_required
def doctors():
    all_doctors = Doctor.query.all()
    return render_template('doctor/dashboard.html', doctors=all_doctors)

@admin_bp.route('/doctor/add', methods=['GET', 'POST'])
@login_required
def add_doctor():
    if request.method == 'POST':
        name = request.form.get('name')
        specialty = request.form.get('specialty')
        email = request.form.get('email')
        availability = request.form.get('availability')
        status = request.form.get('status')
        
        if not (name and specialty and email and availability and status):
            flash('Please fill in all fields.', 'warning')
            return render_template('admin/add_doctor.html')
        
        existing = Doctor.query.filter_by(email=email).first()
        if existing:
            flash('A doctor with that email already exists.', 'danger')
            return render_template('admin/add_doctor.html')
        
        new_doctor = Doctor(
            name=name,
            specialty=specialty,
            email=email,
            availability=availability,
            status=status
        )
        db.session.add(new_doctor)
        db.session.commit()
        print('doctor added')
        flash('Doctor profile added successfully.', 'success')
        return redirect(url_for('admin.dashboard'))
    
    return render_template('admin/add_doctor.html')

# Additional admin routes: update doctor, delete doctor, manage appointments, search
@admin_bp.route('/doctor/edit/<int:doctor_id>', methods=['GET', 'POST'])
@login_required
def edit_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)

    if request.method == 'POST':
        doctor.name = request.form.get('name')
        doctor.specialty = request.form.get('specialty')
        doctor.email = request.form.get('email')
        doctor.availability = request.form.get('availability')
        doctor.status = request.form.get('status')

        if not (doctor.name and doctor.specialty and doctor.email and doctor.availability and doctor.status):
            flash('Please fill in all fields.', 'warning')
            return render_template('admin/edit_doctor.html', doctor=doctor)

        # Check if new email conflicts with another doctor
        existing = Doctor.query.filter(Doctor.email == doctor.email, Doctor.id != doctor.id).first()
        if existing:
            flash('Another doctor with that email already exists.', 'danger')
            return render_template('admin/edit_doctor.html', doctor=doctor)

        db.session.commit()
        flash('Doctor profile updated successfully.', 'success')
        return redirect(url_for('admin.doctors'))

    return render_template('admin/edit_doctor.html', doctor=doctor)

@admin_bp.route('/patient/add', methods=['GET', 'POST'])
@login_required
def add_patient():
    if request.method == 'POST':
        name = request.form.get('name')
        age = request.form.get('age')
        gender = request.form.get('gender')
        email = request.form.get('email')
        phone = request.form.get('phone')
        status = request.form.get('status')

        # Basic validation
        if not (name and age and gender and email and phone and status):
            flash('Please fill in all fields.', 'warning')
            return render_template('patient/add_patient.html')

        # Ensure age is an integer
        try:
            age = int(age)
        except ValueError:
            flash('Age must be a valid number.', 'warning')
            return render_template('patient/add_patient.html')

        # Check if email already exists
        existing = Patient.query.filter_by(email=email).first()
        if existing:
            flash('A patient with that email already exists.', 'danger')
            return render_template('patient/add_patient.html')

        new_patient = Patient(
            name=name,
            age=age,
            gender=gender,
            email=email,
            phone=phone,
            status=status
        )
        db.session.add(new_patient)
        db.session.commit()
        flash('Patient added successfully.', 'success')
        return redirect(url_for('admin.dashboard'))

    return render_template('patient/add_patient.html')

@admin_bp.route('/appointment/add', methods=['GET', 'POST'])
@login_required
def add_appointment():
    if request.method == 'POST':
        patient_id = request.form.get('patient_id')
        doctor_id = request.form.get('doctor_id')
        appointment_date = request.form.get('appointment_date')  # Expected format: 'YYYY-MM-DD HH:MM'
        reason = request.form.get('reason')
        status = 'booked'  # Default status when creating

        try:
            # Remove 'T' and use fromisoformat
            appointment_date = datetime.fromisoformat(appointment_date)
        except ValueError:
            flash('Invalid date/time format.', 'danger')
            # reload form with existing data
            patients = Patient.query.filter_by(status='active').all()
            doctors = Doctor.query.filter_by(status='active').all()
            return render_template('admin/book_appointment.html', patients=patients, doctors=doctors)
        
        # Basic validation
        if not (patient_id and doctor_id and appointment_date and reason):
            flash('Please fill in all fields.', 'warning')
            # Re-render form below with patient and doctor lists
        else:
            # Check if doctor is already booked for the given date/time
            conflict = Appointment.query.filter_by(doctor_id=doctor_id, appointment_date=appointment_date).first()
            if conflict:
                flash('The doctor already has an appointment at this date and time.', 'danger')
            else:
                new_appointment = Appointment(
                    patient_id=patient_id,
                    doctor_id=doctor_id,
                    appointment_date=appointment_date,
                    reason=reason,
                    status=status
                )
                db.session.add(new_appointment)
                db.session.commit()
                flash('Appointment created successfully.', 'success')
                return redirect(url_for('admin.dashboard'))

    # GET request or validation failure - render form
    patients = Patient.query.filter_by(status='active').all()
    doctors = Doctor.query.filter_by(status='active').all()
    return render_template('admin/book_appointment.html', patients=patients, doctors=doctors)