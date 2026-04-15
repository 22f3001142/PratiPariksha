from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from ..models import db, Student, Question, Response, Exam, Mood, LooBreak, TestPaperQuestion
from datetime import datetime
from ..services import is_correct

exam_bp = Blueprint('exam', __name__)

@exam_bp.route('/questions', methods=['GET'])
@jwt_required()
def get_exam_questions():
    exam = Exam.query.first()
    if not exam or exam.status != 'started':
        return jsonify({"msg": "Exam not started"}), 403

    if exam.test_id:
        mappings = TestPaperQuestion.query.filter_by(test_id=exam.test_id).order_by(TestPaperQuestion.sort_order.asc()).all()
        question_ids = [mapping.question_id for mapping in mappings]
        questions = Question.query.filter(Question.id.in_(question_ids)).all() if question_ids else []
        questions.sort(key=lambda question: question_ids.index(question.id) if question.id in question_ids else 0)
    else:
        questions = Question.query.order_by(Question.topic.asc(), Question.id.asc()).limit(20).all()

    return jsonify([{
        "id": q.id,
        "question": q.question,
        "type": q.type,
        "options": q.options,
        "topic": q.topic or 'General',
        "subtopic": q.subtopic or 'General'
    } for q in questions]), 200

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
            
        # Gamification Logic: Check if correct
        question = Question.query.get(q_id)
        if question and is_correct(question, ans):
            correct_count += 1
            points_earned += 10 # 10 Points per correct answer
            
    # Update Student Stats
    student.points += points_earned
    # Level up: 1 level per 50 points
    student.level = (student.points // 50) + 1 
    
    # Award Badge if perfect score (assuming 20 questions)
    if correct_count == 20 and "Perfect Score" not in (student.badges or ""):
        student.badges = (student.badges + ",Perfect Score").strip(',')
            
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
    new_break = LooBreak(student_id=student_id, start_time=datetime.utcnow())
    db.session.add(new_break)
    db.session.commit()
    
    # Track currently on loo break
    count = LooBreak.query.filter(LooBreak.end_time == None).count()
    return jsonify({"msg": "Loo break started", "current_on_break": count}), 201

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
