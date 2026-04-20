from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from ..models import db, Admin, Student, Teacher, Exam, LooBreak, TestPaper, StudentTeacher
from werkzeug.security import generate_password_hash
from datetime import datetime
from sqlalchemy.exc import IntegrityError

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
        data = request.get_json()
        role = data.get('role')
        name = data.get('name')
        email = data.get('email')
        password = generate_password_hash(data.get('password'), method='pbkdf2:sha256')
        uid = data.get('id') # admission_id or employee_id
        
        if role == 'student':
            teacher_ids = data.get('assigned_teacher_ids') or []
            legacy = data.get('assigned_teacher_id') or None
            if not teacher_ids and legacy:
                teacher_ids = [legacy]
            new_user = Student(
                admission_id=uid,
                name=name,
                email=email,
                password=password,
                assigned_teacher_id=(teacher_ids[0] if teacher_ids else None)
            )
            db.session.add(new_user)
            try:
                db.session.flush()
            except IntegrityError:
                db.session.rollback()
                return jsonify({"msg": "User with this ID or email already exists"}), 400
            for tid in teacher_ids:
                db.session.add(StudentTeacher(student_id=uid, teacher_id=tid))
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                return jsonify({"msg": "Could not assign teachers."}), 400
            return jsonify({"msg": "User created"}), 201
        elif role == 'teacher':
            new_user = Teacher(
                employee_id=uid,
                name=name,
                email=email,
                password=password,
                subject=data.get('subject') or 'Mathematics'
            )
        else:
            return jsonify({"msg": "Invalid role"}), 400
            
        db.session.add(new_user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return jsonify({"msg": "User with this ID or email already exists"}), 400
        return jsonify({"msg": "User created"}), 201
        
    students = Student.query.all()
    teachers = Teacher.query.all()
    assignments = StudentTeacher.query.all()
    by_student = {}
    for row in assignments:
        by_student.setdefault(row.student_id, []).append(row.teacher_id)
    return jsonify({
        "students": [{
            "admission_id": s.admission_id,
            "name": s.name,
            "email": s.email,
            "assigned_teacher_id": s.assigned_teacher_id,
            "assigned_teacher_ids": by_student.get(s.admission_id, ([s.assigned_teacher_id] if s.assigned_teacher_id else []))
        } for s in students],
        "teachers": [{
            "employee_id": t.employee_id,
            "name": t.name,
            "email": t.email,
            "subject": t.subject or 'Mathematics'
        } for t in teachers]
    }), 200


@admin_bp.route('/students/<string:student_id>/teachers', methods=['PUT'])
@jwt_required()
def set_student_teachers(student_id):
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({"msg": "Unauthorized"}), 403
    student = Student.query.get(student_id)
    if not student:
        return jsonify({"msg": "Student not found"}), 404
    data = request.get_json() or {}
    teacher_ids = data.get('teacher_ids') or []
    StudentTeacher.query.filter_by(student_id=student_id).delete()
    for tid in teacher_ids:
        db.session.add(StudentTeacher(student_id=student_id, teacher_id=tid))
    student.assigned_teacher_id = teacher_ids[0] if teacher_ids else None
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"msg": "Could not save assignments."}), 400
    return jsonify({"msg": "Assignments updated", "teacher_ids": teacher_ids}), 200

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
        'duration_minutes': test.duration_minutes,
        'scheduled_start': test.scheduled_start.isoformat() if test.scheduled_start else None,
        'scheduled_end': test.scheduled_end.isoformat() if test.scheduled_end else None,
        'max_loo_breaks': test.max_loo_breaks,
        'max_loo_minutes': test.max_loo_minutes,
    } for test in tests]), 200


@admin_bp.route('/tests/<int:test_id>', methods=['PATCH'])
@jwt_required()
def admin_update_test(test_id):
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({"msg": "Unauthorized"}), 403
    test = TestPaper.query.get(test_id)
    if not test:
        return jsonify({"msg": "Test not found"}), 404
    data = request.get_json() or {}

    def _int(v, default, minimum=None):
        try: n = int(v)
        except (TypeError, ValueError): return default
        return max(minimum, n) if minimum is not None else n

    def _dt(v):
        if not v: return None
        try:
            return datetime.fromisoformat(str(v).replace('Z', '+00:00'))
        except (TypeError, ValueError):
            return None

    if 'duration_minutes' in data:
        test.duration_minutes = _int(data.get('duration_minutes'), test.duration_minutes or 60, minimum=1)
    if 'scheduled_start' in data:
        test.scheduled_start = _dt(data.get('scheduled_start'))
    if 'scheduled_end' in data:
        test.scheduled_end = _dt(data.get('scheduled_end'))
    if 'max_loo_breaks' in data:
        test.max_loo_breaks = _int(data.get('max_loo_breaks'), test.max_loo_breaks or 0, minimum=0)
    if 'max_loo_minutes' in data:
        test.max_loo_minutes = _int(data.get('max_loo_minutes'), test.max_loo_minutes or 0, minimum=0)
    db.session.commit()
    return jsonify({"msg": "Test updated"}), 200

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
