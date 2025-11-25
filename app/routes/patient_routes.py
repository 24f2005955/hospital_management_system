from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from app.models import Doctor, Appointment, Treatment
from app.forms import AppointmentForm
from app.database import db

patient_bp = Blueprint('patient', __name__, url_prefix='/patient')

def patient_required(f):
    # Implement access control decorator for patients
    pass


@patient_bp.route('/dashboard')
@login_required
def dashboard():
    # Upcoming or booked appointments
    upcoming_appointments = Appointment.query.filter(
        Appointment.patient_id == current_user.id,
        Appointment.status == 'Booked',
        Appointment.appointment_date >= datetime.now()
    ).order_by(Appointment.appointment_date).all()

    # Past appointments completed
    past_appointments = Appointment.query.filter(
        Appointment.patient_id == patient_id,
        Appointment.status == 'Completed'
    ).order_by(Appointment.appointment_date.desc()).all()

    return render_template('patient/dashboard.html',
                           upcoming_appointments=upcoming_appointments,
                           past_appointments=past_appointments,
                           patient_name=session.get('patient_name'))

@patient_bp.route('/book-appointment', methods=['GET', 'POST'])
@login_required
def book_appointment():
    form = AppointmentForm()
    # populate doctor choices dynamically
    form.doctor_id.choices = [(d.id, f'{d.name} - {d.specialty}') for d in Doctor.query.filter_by(status='Active').all()]
    if form.validate_on_submit():
        new_appointment = Appointment(
            patient_id=current_user.id,
            doctor_id=form.doctor_id.data,
            appointment_date=form.appointment_date.data,
            reason=form.reason.data,
            status='Booked'
        )
        db.session.add(new_appointment)
        db.session.commit()
        flash('Appointment booked successfully.', 'success')
        return redirect(url_for('patient.dashboard'))
    return render_template('patient/book_appointment.html', form=form)
