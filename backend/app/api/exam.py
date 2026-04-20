from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from ..models import db, Student, Question, Response, Exam, Mood, LooBreak, TestPaperQuestion, TestPaper
from datetime import datetime
from ..services import is_correct

exam_bp = Blueprint('exam', __name__)

@exam_bp.route('/questions', methods=['GET'])
@jwt_required()
def get_exam_questions():
    exam = Exam.query.first()
    if not exam or exam.status != 'started':
        return jsonify({"msg": "Exam not started"}), 403

    test = TestPaper.query.get(exam.test_id) if exam.test_id else None
    now = datetime.utcnow()
    if test and test.scheduled_start and now < test.scheduled_start:
        return jsonify({"msg": f"Exam starts at {test.scheduled_start.isoformat()}"}), 403

    if exam.test_id:
        mappings = TestPaperQuestion.query.filter_by(test_id=exam.test_id).order_by(TestPaperQuestion.sort_order.asc()).all()
        question_ids = [mapping.question_id for mapping in mappings]
        questions = Question.query.filter(Question.id.in_(question_ids)).all() if question_ids else []
        questions.sort(key=lambda question: question_ids.index(question.id) if question.id in question_ids else 0)
    else:
        questions = Question.query.order_by(Question.topic.asc(), Question.id.asc()).limit(20).all()

    duration_minutes = (test.duration_minutes if test and test.duration_minutes else 60)
    exam_start = exam.start_time or now
    elapsed_seconds = int((now - exam_start).total_seconds()) if exam_start else 0
    remaining_seconds = max(0, duration_minutes * 60 - elapsed_seconds)

    return jsonify({
        "questions": [{
            "id": q.id,
            "question": q.question,
            "type": q.type,
            "options": q.options,
            "topic": q.topic or 'General',
            "subtopic": q.subtopic or 'General'
        } for q in questions],
        "duration_minutes": duration_minutes,
        "remaining_seconds": remaining_seconds,
        "exam_start": exam_start.isoformat() if exam_start else None,
        "scheduled_start": test.scheduled_start.isoformat() if test and test.scheduled_start else None,
        "scheduled_end": test.scheduled_end.isoformat() if test and test.scheduled_end else None,
        "max_loo_breaks": (test.max_loo_breaks if test else 0) or 0,
        "max_loo_minutes": (test.max_loo_minutes if test else 0) or 0,
    }), 200

@exam_bp.route('/submit', methods=['POST'])
@jwt_required()
def submit_response():
    student_id = get_jwt_identity()
    student = Student.query.get(student_id) # Get the student to update points
    data = request.get_json() or []
    if isinstance(data, dict):
        data = data.get('responses') or []
    
    points_earned = 0
    correct_count = 0
    
    for r in data:
        q_id = r.get('question_id')
        ans = r.get('answer')
        
        # Save Response
        existing = Response.query.filter_by(student_id=student_id, question_id=q_id).first()
        if existing:
            existing.answer = ans
        else:
            new_resp = Response(student_id=student_id, question_id=q_id, answer=ans)
            db.session.add(new_resp)
            
        question = Question.query.get(q_id)
        if question and is_correct(question, ans):
            correct_count += 1
            points_earned += 1

    total_questions = len(data)
    student.points += points_earned
    student.level = (student.points // 10) + 1

    if total_questions > 0 and correct_count == total_questions and "Perfect Score" not in (student.badges or ""):
        student.badges = ((student.badges or '') + ",Perfect Score").strip(',')
            
    db.session.commit()
    
    return jsonify({
        "msg": "Exam submitted", 
        "score": correct_count, 
        "points_earned": points_earned,
        "new_total_points": student.points
    }), 200

@exam_bp.route('/mood', methods=['POST'])
@jwt_required()
def log_mood():
    student_id = get_jwt_identity()
    data = request.get_json()
    new_mood = Mood(student_id=student_id, mood=data.get('mood'))
    db.session.add(new_mood)
    db.session.commit()
    return jsonify({"msg": "Mood logged"}), 201

@exam_bp.route('/loo-break/start', methods=['POST'])
@jwt_required()
def start_loo_break():
    student_id = get_jwt_identity()
    exam = Exam.query.first()
    test = TestPaper.query.get(exam.test_id) if exam and exam.test_id else None
    max_breaks = (test.max_loo_breaks if test else 0) or 0
    if max_breaks <= 0:
        return jsonify({"msg": "Breaks are not permitted for this test."}), 403
    if exam and exam.start_time:
        used = LooBreak.query.filter(
            LooBreak.student_id == student_id,
            LooBreak.start_time >= exam.start_time
        ).count()
        if used >= max_breaks:
            return jsonify({"msg": "Break limit reached."}), 403

    active_existing = LooBreak.query.filter_by(student_id=student_id, end_time=None).first()
    if active_existing:
        return jsonify({"msg": "You are already on a break."}), 400

    new_break = LooBreak(student_id=student_id, start_time=datetime.utcnow())
    db.session.add(new_break)
    db.session.commit()

    count = LooBreak.query.filter(LooBreak.end_time == None).count()
    return jsonify({
        "msg": "Loo break started",
        "current_on_break": count,
        "max_loo_minutes": (test.max_loo_minutes if test else 0) or 0,
    }), 201

@exam_bp.route('/loo-break/end', methods=['POST'])
@jwt_required()
def end_loo_break():
    student_id = get_jwt_identity()
    active_break = LooBreak.query.filter_by(student_id=student_id, end_time=None).first()
    if active_break:
        active_break.end_time = datetime.utcnow()
        db.session.commit()
        
    count = LooBreak.query.filter(LooBreak.end_time == None).count()
    return jsonify({"msg": "Loo break ended", "current_on_break": count}), 200

@exam_bp.route('/status', methods=['GET'])
@jwt_required()
def exam_status():
    exam = Exam.query.first()
    count = LooBreak.query.filter(LooBreak.end_time == None).count()
    return jsonify({
        "status": exam.status if exam else "stopped",
        "students_on_loo_break": count
    }), 200
