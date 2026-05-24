from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from database.models import db, User, Patient, Consultation, AuditLog
from datetime import datetime

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Access denied. Admin privileges required.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/')
def root():
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/dashboard')
def dashboard():
    total_users = User.query.filter_by(role='user').count()
    total_patients = Patient.query.count()
    total_consultations = Consultation.query.count()
    recent_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(10).all()
    recent_consultations = Consultation.query.order_by(Consultation.created_at.desc()).limit(5).all()
    return render_template('admin/dashboard.html',
                           total_users=total_users,
                           total_patients=total_patients,
                           total_consultations=total_consultations,
                           recent_logs=recent_logs,
                           recent_consultations=recent_consultations)

@admin_bp.route('/users')
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=all_users)

@admin_bp.route('/users/add', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        full_name = request.form.get('full_name', '').strip()
        profession = request.form.get('profession', '').strip()
        department = request.form.get('department', '').strip()
        role = request.form.get('role', 'user')

        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return render_template('admin/add_user.html')

        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'danger')
            return render_template('admin/add_user.html')

        new_user = User(
            username=username, email=email,
            full_name=full_name, profession=profession,
            department=department, role=role
        )
        new_user.set_password(password)
        db.session.add(new_user)

        log = AuditLog(user_id=current_user.id, action="ADD_USER",
                       details=f"Admin added user: {username}", ip_address=request.remote_addr)
        db.session.add(log)
        db.session.commit()

        flash(f'User {username} created successfully!', 'success')
        return redirect(url_for('admin.users'))

    return render_template('admin/add_user.html')

@admin_bp.route('/users/toggle/<int:user_id>')
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot deactivate your own account.', 'warning')
        return redirect(url_for('admin.users'))
    user.is_active = not user.is_active
    log = AuditLog(user_id=current_user.id, action="TOGGLE_USER",
                   details=f"User {user.username} {'activated' if user.is_active else 'deactivated'}",
                   ip_address=request.remote_addr)
    db.session.add(log)
    db.session.commit()
    flash(f'User {user.username} has been {"activated" if user.is_active else "deactivated"}.', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/patients')
def patients():
    all_patients = Patient.query.order_by(Patient.created_at.desc()).all()
    return render_template('admin/patients.html', patients=all_patients)

@admin_bp.route('/reports')
def reports():
    total_users = User.query.filter_by(role='user').count()
    total_patients = Patient.query.count()
    total_consultations = Consultation.query.count()
    ai_assisted = Consultation.query.filter(Consultation.ai_analysis != None, Consultation.ai_analysis != '').count()
    consultations_by_status = db.session.query(
        Consultation.status, db.func.count(Consultation.id)
    ).group_by(Consultation.status).all()
    return render_template('admin/reports.html',
                           total_users=total_users,
                           total_patients=total_patients,
                           total_consultations=total_consultations,
                           ai_assisted=ai_assisted,
                           consultations_by_status=consultations_by_status)

@admin_bp.route('/audit')
def audit():
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(100).all()
    return render_template('admin/audit.html', logs=logs)
