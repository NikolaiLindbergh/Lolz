from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from database.models import db, User, Patient, Consultation, AuditLog, SurveyResponse, PatientSurvey, SurveyQuestion, SurveyAnswer
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
@admin_required
def root():
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/dashboard')
@admin_required
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
@admin_required
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=all_users)

@admin_bp.route('/users/add', methods=['GET', 'POST'])
@admin_required
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
@admin_required
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
@admin_required
def patients():
    all_patients = Patient.query.order_by(Patient.created_at.desc()).all()
    return render_template('admin/patients.html', patients=all_patients)

@admin_bp.route('/reports')
@admin_required
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

@admin_bp.route('/survey', methods=['GET', 'POST'])
@admin_required
def survey():
    survey_questions = SurveyQuestion.query.filter_by(active=True).order_by(SurveyQuestion.order).all()

    if request.method == 'POST':
        respondent_name = request.form.get('respondent_name', '').strip() or 'Anonymous'
        department = request.form.get('department', '').strip() or 'Unknown'
        comments = request.form.get('comments', '').strip()

        response = SurveyResponse(
            respondent_name=respondent_name,
            department=department,
            comments=comments
        )
        db.session.add(response)
        db.session.flush()

        if survey_questions:
            for question in survey_questions:
                answer_text = request.form.get(f'question_{question.id}', '').strip()
                answer = SurveyAnswer(
                    response_id=response.id,
                    question_id=question.id,
                    answer_text=answer_text
                )
                db.session.add(answer)
        else:
            satisfaction = request.form.get('satisfaction', type=int)
            usefulness = request.form.get('usefulness', type=int)
            ease_of_use = request.form.get('ease_of_use', type=int)
            response.satisfaction = satisfaction
            response.usefulness = usefulness
            response.ease_of_use = ease_of_use

        log = AuditLog(user_id=current_user.id, action='SURVEY_RESPONSE',
                       details=f'Added survey response from {respondent_name}',
                       ip_address=request.remote_addr)
        db.session.add(log)
        db.session.commit()
        flash('Survey response saved successfully.', 'success')
        return redirect(url_for('admin.survey'))

    survey_responses = SurveyResponse.query.order_by(SurveyResponse.created_at.desc()).limit(20).all()
    total_surveys = SurveyResponse.query.count()
    average_satisfaction = db.session.query(db.func.avg(SurveyResponse.satisfaction)).scalar() or 0
    average_usefulness = db.session.query(db.func.avg(SurveyResponse.usefulness)).scalar() or 0
    average_ease = db.session.query(db.func.avg(SurveyResponse.ease_of_use)).scalar() or 0
    return render_template('admin/survey.html',
                           survey_responses=survey_responses,
                           total_surveys=total_surveys,
                           average_satisfaction=round(average_satisfaction, 2),
                           average_usefulness=round(average_usefulness, 2),
                           average_ease=round(average_ease, 2),
                           survey_questions=survey_questions)

@admin_bp.route('/survey/questions', methods=['POST'])
@admin_required
def add_survey_question():
    question_text = request.form.get('question_text', '').strip()
    question_type = request.form.get('question_type', 'text')
    options = request.form.get('options', '').strip()
    is_required = request.form.get('is_required') == 'on'
    order = request.form.get('order', type=int) or 0

    if not question_text:
        flash('Question text cannot be empty.', 'danger')
        return redirect(url_for('admin.survey'))

    question = SurveyQuestion(
        question_text=question_text,
        question_type=question_type,
        options=options,
        is_required=is_required,
        order=order
    )
    db.session.add(question)
    db.session.commit()
    flash('Survey question added successfully.', 'success')
    return redirect(url_for('admin.survey'))

@admin_bp.route('/survey/questions/<int:question_id>/delete')
@admin_required
def delete_survey_question(question_id):
    question = SurveyQuestion.query.get_or_404(question_id)
    db.session.delete(question)
    db.session.commit()
    flash('Survey question removed.', 'success')
    return redirect(url_for('admin.survey'))

@admin_bp.route('/analytics')
@admin_required
def analytics():
    total_consultations = Consultation.query.count()
    ai_assisted = Consultation.query.filter(Consultation.ai_analysis != None, Consultation.ai_analysis != '').count()
    ai_assist_rate = round((ai_assisted / total_consultations * 100), 1) if total_consultations else 0
    consultations_by_status = db.session.query(
        Consultation.status, db.func.count(Consultation.id)
    ).group_by(Consultation.status).all()
    top_clinicians = db.session.query(
        User.full_name, db.func.count(Consultation.id).label('count')
    ).join(Consultation, Consultation.user_id == User.id)
    top_clinicians = top_clinicians.group_by(User.id).order_by(db.desc('count')).limit(5).all()
    total_surveys = SurveyResponse.query.count()
    average_satisfaction = db.session.query(db.func.avg(SurveyResponse.satisfaction)).scalar() or 0
    average_usefulness = db.session.query(db.func.avg(SurveyResponse.usefulness)).scalar() or 0
    return render_template('admin/analytics.html',
                           total_consultations=total_consultations,
                           ai_assisted=ai_assisted,
                           ai_assist_rate=ai_assist_rate,
                           consultations_by_status=consultations_by_status,
                           top_clinicians=top_clinicians,
                           total_surveys=total_surveys,
                           average_satisfaction=round(average_satisfaction, 2),
                           average_usefulness=round(average_usefulness, 2))

@admin_bp.route('/patient-surveys')
@admin_required
def patient_surveys():
    surveys = PatientSurvey.query.order_by(PatientSurvey.created_at.desc()).all()
    return render_template('admin/patient_surveys.html', surveys=surveys)

@admin_bp.route('/patient-surveys/<int:survey_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_patient_survey(survey_id):
    survey = PatientSurvey.query.get_or_404(survey_id)
    if request.method == 'POST':
        survey.patient_satisfaction = request.form.get('patient_satisfaction', type=int)
        survey.care_quality = request.form.get('care_quality', type=int)
        survey.comfort_level = request.form.get('comfort_level', type=int)
        survey.comments = request.form.get('comments', '').strip()
        survey.review_notes = request.form.get('review_notes', '').strip()
        db.session.commit()
        flash('Patient survey updated successfully.', 'success')
        return redirect(url_for('admin.patient_surveys'))
    return render_template('admin/edit_patient_survey.html', survey=survey)

@admin_bp.route('/survey/<int:survey_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_survey_response(survey_id):
    survey = SurveyResponse.query.get_or_404(survey_id)
    if request.method == 'POST':
        survey.respondent_name = request.form.get('respondent_name', '').strip() or 'Anonymous'
        survey.department = request.form.get('department', '').strip() or 'Unknown'
        survey.satisfaction = request.form.get('satisfaction', type=int)
        survey.usefulness = request.form.get('usefulness', type=int)
        survey.ease_of_use = request.form.get('ease_of_use', type=int)
        survey.comments = request.form.get('comments', '').strip()
        db.session.commit()
        flash('Survey response updated successfully.', 'success')
        return redirect(url_for('admin.survey'))
    return render_template('admin/edit_survey.html', survey=survey)

@admin_bp.route('/audit')
@admin_required
def audit():
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(100).all()
    return render_template('admin/audit.html', logs=logs)
