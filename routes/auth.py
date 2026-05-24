from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from database.models import db, User, AuditLog

auth_bp = Blueprint('auth', __name__)

def log_action(user_id, action, details="", request=None):
    ip = request.remote_addr if request else "unknown"
    log = AuditLog(user_id=user_id, action=action, details=details, ip_address=ip)
    db.session.add(log)
    db.session.commit()

@auth_bp.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('user.dashboard'))
    return render_template('index.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('user.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password) and user.is_active:
            login_user(user, remember=False)
            log_action(user.id, "LOGIN", f"User logged in: {username}", request)
            flash(f'Welcome back, {user.full_name or user.username}!', 'success')
            if user.is_admin():
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('user.dashboard'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('user.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        full_name = request.form.get('full_name', '').strip()
        password = request.form.get('password', '')

        if not username or not email or not full_name or not password:
            flash('Please complete all registration fields.', 'warning')
            return render_template('auth/register.html')

        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return render_template('auth/register.html')

        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'danger')
            return render_template('auth/register.html')

        user = User(
            username=username,
            email=email,
            full_name=full_name,
            role='user',
            is_active=True
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        log_action(user.id, 'REGISTER', f'New user registered: {username}', request)
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('auth.user_login'))

    return render_template('auth/register.html')

@auth_bp.route('/user/register', methods=['GET', 'POST'])
def user_register():
    return register()

@auth_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    return redirect(url_for('admin.root'))

@auth_bp.route('/user/login', methods=['GET', 'POST'])
def user_login():
    return login()

@auth_bp.route('/logout')
@login_required
def logout():
    log_action(current_user.id, "LOGOUT", f"User logged out: {current_user.username}", request)
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
