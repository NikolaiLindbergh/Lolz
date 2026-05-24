from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from database.models import db, User, Patient, Consultation, AuditLog, SurveyResponse, PatientSurvey, SurveyQuestion, SurveyAnswer
from ai.clinical_ai import analyze_patient
from datetime import datetime
import json

user_bp = Blueprint('user', __name__, url_prefix='/user')

def log_action(action, details=""):
    log = AuditLog(user_id=current_user.id, action=action, details=details,
                   ip_address=request.remote_addr)
    db.session.add(log)
    db.session.commit()

@user_bp.route('/dashboard')
@login_required
def dashboard():
    my_patients = Patient.query.filter_by(created_by=current_user.id).count()
    my_consultations = Consultation.query.filter_by(user_id=current_user.id).count()
    recent_consultations = (Consultation.query
                            .filter_by(user_id=current_user.id)
                            .order_by(Consultation.created_at.desc())
                            .limit(5).all())
    return render_template('user/dashboard.html',
                           my_patients=my_patients,
                           my_consultations=my_consultations,
                           recent_consultations=recent_consultations)

# ── PATIENTS ──────────────────────────────────────────────────
@user_bp.route('/patients')
@login_required
def patients():
    search = request.args.get('search', '').strip()
    query = Patient.query.filter_by(created_by=current_user.id)
    if search:
        query = query.filter(Patient.full_name.ilike(f'%{search}%'))
    all_patients = query.order_by(Patient.created_at.desc()).all()
    return render_template('user/patients.html', patients=all_patients, search=search)

@user_bp.route('/patients/new', methods=['GET', 'POST'])
@login_required
def new_patient():
    if request.method == 'POST':
        # Generate patient ID
        count = Patient.query.count() + 1
        patient_id = f"P-{count:04d}"

        patient = Patient(
            patient_id=patient_id,
            full_name=request.form.get('full_name', '').strip(),
            age=request.form.get('age', type=int),
            gender=request.form.get('gender', ''),
            contact=request.form.get('contact', '').strip(),
            address=request.form.get('address', '').strip(),
            blood_type=request.form.get('blood_type', ''),
            allergies=request.form.get('allergies', '').strip(),
            current_medications=request.form.get('current_medications', '').strip(),
            medical_history=request.form.get('medical_history', '').strip(),
            created_by=current_user.id
        )
        db.session.add(patient)
        db.session.flush()

        log_action("ADD_PATIENT", f"Added patient: {patient.full_name} ({patient_id})")
        flash(f'Patient {patient.full_name} registered successfully (ID: {patient_id}).', 'success')
        return redirect(url_for('user.patient_detail', patient_id=patient.id))

    return render_template('user/new_patient.html')

@user_bp.route('/patients/<int:patient_id>')
@login_required
def patient_detail(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    consultations = (Consultation.query
                     .filter_by(patient_id=patient.id)
                     .order_by(Consultation.created_at.desc()).all())
    return render_template('user/patient_detail.html', patient=patient, consultations=consultations)

# ── AI CONSULTATION ───────────────────────────────────────────
@user_bp.route('/ai-consult/<int:patient_id>', methods=['GET', 'POST'])
@login_required
def ai_consult(patient_id):
    patient = Patient.query.get_or_404(patient_id)

    if request.method == 'POST':
        symptoms = request.form.get('symptoms', '').strip()
        chief_complaint = request.form.get('chief_complaint', '').strip()
        doctor_notes = request.form.get('doctor_notes', '').strip()

        vital_signs = {
            'bp': request.form.get('bp', ''),
            'hr': request.form.get('hr', ''),
            'temp': request.form.get('temp', ''),
            'spo2': request.form.get('spo2', ''),
            'rr': request.form.get('rr', '')
        }

        if not symptoms:
            flash('Please enter the patient symptoms.', 'warning')
            return render_template('user/ai_consult.html', patient=patient)

        # Call the AI
        patient_data = {
            'full_name': patient.full_name,
            'age': patient.age,
            'gender': patient.gender,
            'blood_type': patient.blood_type,
            'allergies': patient.allergies,
            'current_medications': patient.current_medications,
            'medical_history': patient.medical_history
        }

        ai_result = analyze_patient(patient_data, symptoms, vital_signs)

        # Save consultation
        consultation = Consultation(
            patient_id=patient.id,
            user_id=current_user.id,
            chief_complaint=chief_complaint,
            symptoms=symptoms,
            vital_signs=json.dumps(vital_signs),
            ai_analysis=ai_result.get('clinical_summary', ''),
            ai_diagnosis=json.dumps(ai_result.get('possible_diagnoses', [])),
            ai_recommendations=json.dumps({
                'tests': ai_result.get('recommended_tests', []),
                'red_flags': ai_result.get('red_flags', []),
                'immediate_actions': ai_result.get('immediate_actions', ''),
                'recommendations': ai_result.get('recommendations', []),
                'disclaimer': ai_result.get('disclaimer', '')
            }),
            doctor_notes=doctor_notes,
            status='pending'
        )
        db.session.add(consultation)
        log_action("AI_CONSULT", f"AI consultation for patient {patient.patient_id}")

        return render_template('user/ai_result.html', patient=patient,
                               consultation=consultation, ai_result=ai_result)

    return render_template('user/ai_consult.html', patient=patient)

@user_bp.route('/consultations/<int:consultation_id>/review', methods=['POST'])
@login_required
def review_consultation(consultation_id):
    consultation = Consultation.query.get_or_404(consultation_id)
    doctor_notes = request.form.get('doctor_notes', '').strip()
    consultation.doctor_notes = doctor_notes
    consultation.status = 'reviewed'
    log_action("REVIEW_CONSULT", f"Reviewed consultation #{consultation_id}")
    flash('Consultation marked as reviewed.', 'success')
    return redirect(url_for('user.patient_detail', patient_id=consultation.patient_id))

@user_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.full_name = request.form.get('full_name', '').strip()
        current_user.email = request.form.get('email', '').strip()
        current_user.profession = request.form.get('profession', '').strip()
        current_user.department = request.form.get('department', '').strip()

        new_pass = request.form.get('new_password', '')
        if new_pass:
            current_user.set_password(new_pass)

        db.session.commit()
        flash('Profile updated successfully.', 'success')

    return render_template('user/profile.html')

@user_bp.route('/patients/<int:patient_id>/patient-survey', methods=['GET', 'POST'])
@login_required
def patient_survey(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    if request.method == 'POST':
        patient_satisfaction = request.form.get('patient_satisfaction', type=int)
        care_quality = request.form.get('care_quality', type=int)
        comfort_level = request.form.get('comfort_level', type=int)
        comments = request.form.get('comments', '').strip()

        survey = PatientSurvey(
            patient_id=patient.id,
            user_id=current_user.id,
            patient_satisfaction=patient_satisfaction,
            care_quality=care_quality,
            comfort_level=comfort_level,
            comments=comments
        )
        db.session.add(survey)
        log_action('PATIENT_SURVEY', f'Patient survey created for {patient.patient_id}')
        flash('Patient survey submitted successfully.', 'success')
        return redirect(url_for('user.patient_detail', patient_id=patient.id))

    return render_template('user/patient_survey.html', patient=patient)
@user_bp.route('/reports')
@login_required
def reports():
    my_patients = Patient.query.filter_by(created_by=current_user.id).count()
    my_consultations = Consultation.query.filter_by(user_id=current_user.id).count()
    ai_assisted = Consultation.query.filter(
        Consultation.user_id == current_user.id,
        Consultation.ai_analysis != None,
        Consultation.ai_analysis != ''
    ).count()
    consultations_by_status = db.session.query(
        Consultation.status, db.func.count(Consultation.id)
    ).filter(Consultation.user_id == current_user.id).group_by(Consultation.status).all()
    return render_template('user/reports.html',
                           my_patients=my_patients,
                           my_consultations=my_consultations,
                           ai_assisted=ai_assisted,
                           consultations_by_status=consultations_by_status)

@user_bp.route('/analytics')
@login_required
def analytics():
    my_consultations = Consultation.query.filter_by(user_id=current_user.id).count()
    ai_assisted = Consultation.query.filter(
        Consultation.user_id == current_user.id,
        Consultation.ai_analysis != None,
        Consultation.ai_analysis != ''
    ).count()
    ai_assist_rate = round((ai_assisted / my_consultations * 100), 1) if my_consultations else 0
    consultations_by_status = db.session.query(
        Consultation.status, db.func.count(Consultation.id)
    ).filter(Consultation.user_id == current_user.id).group_by(Consultation.status).all()
    top_patients = db.session.query(
        Patient.full_name, db.func.count(Consultation.id).label('count')
    ).join(Consultation, Consultation.patient_id == Patient.id)
    top_patients = top_patients.filter(Consultation.user_id == current_user.id).group_by(Patient.id).order_by(db.desc('count')).limit(5).all()
    total_surveys = SurveyResponse.query.count()
    average_satisfaction = db.session.query(db.func.avg(SurveyResponse.satisfaction)).scalar() or 0
    average_usefulness = db.session.query(db.func.avg(SurveyResponse.usefulness)).scalar() or 0
    return render_template('user/analytics.html',
                           my_consultations=my_consultations,
                           ai_assisted=ai_assisted,
                           ai_assist_rate=ai_assist_rate,
                           consultations_by_status=consultations_by_status,
                           top_patients=top_patients,
                           total_surveys=total_surveys,
                           average_satisfaction=round(average_satisfaction, 2),
                           average_usefulness=round(average_usefulness, 2))

@user_bp.route('/survey', methods=['GET', 'POST'])
@login_required
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

        log_action('SURVEY_RESPONSE', f'Added survey response from {respondent_name}')
        db.session.commit()
        flash('Survey response submitted successfully.', 'success')
        return redirect(url_for('user.survey'))

    survey_responses = SurveyResponse.query.order_by(SurveyResponse.created_at.desc()).limit(20).all()
    total_surveys = SurveyResponse.query.count()
    average_satisfaction = db.session.query(db.func.avg(SurveyResponse.satisfaction)).scalar() or 0
    average_usefulness = db.session.query(db.func.avg(SurveyResponse.usefulness)).scalar() or 0
    average_ease = db.session.query(db.func.avg(SurveyResponse.ease_of_use)).scalar() or 0
    return render_template('user/survey.html',
                           survey_responses=survey_responses,
                           total_surveys=total_surveys,
                           average_satisfaction=round(average_satisfaction, 2),
                           average_usefulness=round(average_usefulness, 2),
                           average_ease=round(average_ease, 2),
                           survey_questions=survey_questions)