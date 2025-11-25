from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import Appointment, Patient, Treatment
from app.forms import TreatmentForm
from app.database import db

doctor_bp = Blueprint('doctor', __name__, url_prefix='/doctor')

def doctor_required(f):
    # Implement access control decorator for doctors
    pass

@doctor_bp.route('/dashboard')
@login_required
# Add @doctor_required decorator after implementation
def dashboard():
    # Show upcoming appointments for the doctor
    appointments = Appointment.query.filter_by(doctor_id=current_user.id).order_by(Appointment.appointment_date).all()
    return render_template('doctor/dashboard.html', appointments=appointments)

@doctor_bp.route('/appointment/<int:appointment_id>/treatment', methods=['GET', 'POST'])
@login_required
def add_treatment(appointment_id):
    form = TreatmentForm()
    appointment = Appointment.query.get_or_404(appointment_id)
    if form.validate_on_submit():
        treatment = Treatment(
            appointment_id=appointment.id,
            treatment_date=appointment.appointment_date,
            description=form.diagnosis.data,
            prescription=form.prescription.data,
            notes=form.notes.data
        )
        # Mark the appointment status as completed if needed
        appointment.status = 'Completed'
        db.session.add(treatment)
        db.session.commit()
        flash('Treatment details saved', 'success')
        return redirect(url_for('doctor.dashboard'))
    return render_template('doctor/treatment_form.html', form=form, appointment=appointment)
