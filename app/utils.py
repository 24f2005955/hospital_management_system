from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

def hash_password(password):
    return generate_password_hash(password)

def verify_password(hashed_password, password):
    return check_password_hash(hashed_password, password)

def format_datetime(value, format='%Y-%m-%d %H:%M'):
    """
    Format a datetime object into a string for display.
    Usage in Jinja2: {{ appointment.appointment_date | format_datetime }}
    """
    if value is None:
        return ""
    return value.strftime(format)

def parse_availability_string(avail_str):
    """
    Simple parsing example: expects 'Mon-Fri 9am-5pm'
    Can be extended to return structured data like JSON for availability slots.
    """
    return avail_str.strip()

# Add other helper functions as needed for your app
