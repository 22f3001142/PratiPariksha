from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from ..models import db, Admin, Student, Teacher, Exam, LooBreak, TestPaper
from werkzeug.security import generate_password_hash
from datetime import datetime
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/exam-toggle', methods=['POST'])
@jwt_required()
def toggle_exam():
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({"msg": "Unauthorized"}), 403
        
    data = request.get_json()
    status = data.get('status') # 'started' or 'stopped'
    test_id = data.get('test_id')
    
    exam = Exam.query.first()
    if not exam:
        exam = Exam()
        db.session.add(exam)
        
    exam.status = status
    if test_id:
        exam.test_id = test_id
    if status == 'started':
        exam.start_time = datetime.utcnow()
    else:
        exam.end_time = datetime.utcnow()
        
    db.session.commit()
    return jsonify({"msg": f"Exam {status}", "status": exam.status, "test_id": exam.test_id}), 200

@admin_bp.route('/users', methods=['GET', 'POST'])
@jwt_required()
def manage_users():
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({"msg": "Unauthorized"}), 403
        
    if request.method == 'POST':
        data = request.get_json() or {}
        role = (data.get('role') or '').strip().lower()
        name = (data.get('name') or '').strip()
        email = (data.get('email') or '').strip()
        raw_password = data.get('password') or ''
        uid = (data.get('id') or '').strip() # admission_id or employee_id

        if role not in {'student', 'teacher'}:
            return jsonify({"msg": "Invalid role"}), 400

        if not all([uid, name, email, raw_password]):
            return jsonify({"msg": "ID, name, email, and password are required"}), 400

        password = generate_password_hash(raw_password, method='pbkdf2:sha256')

        if role == 'student':
            new_user = Student(
                admission_id=uid,
                name=name,
                email=email,
                password=password,
                assigned_teacher_id=data.get('assigned_teacher_id') or None
            )
        else:
            new_user = Teacher(
                employee_id=uid,
                name=name,
                email=email,
                password=password,
                subject=data.get('subject') or 'Mathematics'
            )
            
        db.session.add(new_user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return jsonify({"msg": "User with this ID or email already exists"}), 400
        except SQLAlchemyError:
            db.session.rollback()
            return jsonify({"msg": "Database error while creating user. Please try again."}), 500
        return jsonify({"msg": "User created"}), 201
        
    students = Student.query.all()
    teachers = Teacher.query.all()
    return jsonify({
        "students": [{
            "admission_id": s.admission_id,
            "name": s.name,
            "email": s.email,
            "assigned_teacher_id": s.assigned_teacher_id
        } for s in students],
        "teachers": [{
            "employee_id": t.employee_id,
            "name": t.name,
            "email": t.email,
            "subject": t.subject or 'Mathematics'
        } for t in teachers]
    }), 200

@admin_bp.route('/analytics', methods=['GET'])
@jwt_required()
def system_analytics():
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({"msg": "Unauthorized"}), 403
        
    total_students = Student.query.count()
    total_teachers = Teacher.query.count()
    active_exams = Exam.query.filter_by(status='started').count()
    available_tests = TestPaper.query.count()
    
    return jsonify({
        "total_students": total_students,
        "total_teachers": total_teachers,
        "active_exams": active_exams,
        "available_tests": available_tests
    }), 200

@admin_bp.route('/tests', methods=['GET'])
@jwt_required()
def get_tests():
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({"msg": "Unauthorized"}), 403

    tests = TestPaper.query.order_by(TestPaper.created_at.desc()).all()
    return jsonify([{
        'id': test.id,
        'title': test.title,
        'topic': test.topic,
        'created_by': test.created_by,
        'description': test.description,
        'question_count': len(test.questions),
    } for test in tests]), 200

@admin_bp.route('/loo-breaks', methods=['GET'])
@jwt_required()
def monitor_loo_breaks():
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({"msg": "Unauthorized"}), 403
        
    active_breaks = LooBreak.query.filter(LooBreak.end_time == None).all()
    result = []
    for b in active_breaks:
        s = Student.query.get(b.student_id)
        result.append({
            "student_name": s.name if s else "Unknown",
            "student_id": b.student_id,
            "start_time": b.start_time.isoformat()
        })
    return jsonify(result), 200
