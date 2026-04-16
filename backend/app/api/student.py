from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from ..models import db, Student, Forum, Resource, Response, Question, Exam, TestPaper, TestPaperQuestion, Teacher
from sqlalchemy import func
from datetime import datetime
from ..services import build_forum_payload, build_student_snapshot, generate_study_bot_reply, is_correct, topic_label
import os
from dotenv import load_dotenv
import google.generativeai as genai

student_bp = Blueprint('student', __name__)

@student_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def get_dashboard():
    student_id = get_jwt_identity()
    claims = get_jwt()
    if claims.get('role') != 'student':
        return jsonify({"msg": "Unauthorized"}), 403
    
    student = Student.query.get(student_id)
    if not student:
        return jsonify({"msg": "Student not found"}), 404

    snapshot = build_student_snapshot(student_id)
    all_students = Student.query.all()
    scores = {}
    for current_student in all_students:
        current_snapshot = build_student_snapshot(current_student.admission_id)
        scores[current_student.admission_id] = current_snapshot['marks'] if current_snapshot else 0

    sorted_scores = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    rank = next((i + 1 for i, (sid, score) in enumerate(sorted_scores) if sid == student_id), 0)

    return jsonify({
        "total_marks": snapshot['marks'],
        "rank": rank,
        "accuracy": snapshot['accuracy'],
        "points": student.points,
        "level": student.level,
        "badges": student.badges.split(',') if student.badges else [],
        "avatar": student.current_avatar,
        "inventory": student.inventory.split(',') if student.inventory else [],
        "weak_topics": snapshot['weak_topics'],
        "study_plan": snapshot['study_plan'],
        "level_progress": student.points % 50,
        "level_progress_percent": int(((student.points % 50) / 50) * 100),
        "assigned_teacher_id": student.assigned_teacher_id
    }), 200

@student_bp.route('/upcoming-tests', methods=['GET'])
@jwt_required()
def get_upcoming_tests():
    student_id = get_jwt_identity()
    student = Student.query.get(student_id)
    exam = Exam.query.first()
    query = TestPaper.query
    if student and student.assigned_teacher_id:
        teacher = Teacher.query.get(student.assigned_teacher_id)
        query = query.filter_by(created_by=student.assigned_teacher_id)
        if teacher and teacher.subject:
            query = query.filter_by(topic=teacher.subject)
    tests_from_bank = query.order_by(TestPaper.created_at.desc()).all()
    tests = []
    for test in tests_from_bank:
        is_active = bool(exam and exam.status != 'stopped' and exam.test_id == test.id)
        tests.append({
            "id": test.id,
            "test_name": test.title,
            "date": exam.start_time.isoformat() if is_active and exam.start_time else (test.created_at.isoformat() if test.created_at else "TBD"),
            "status": exam.status if is_active else "available",
            "topic": test.topic or "General",
            "description": test.description or "",
            "question_count": len(test.questions),
        })
    return jsonify(tests), 200

@student_bp.route('/leaderboard', methods=['GET'])
@jwt_required()
def get_leaderboard():
    all_students = Student.query.all()
    leaderboard = []
    for s in all_students:
        snapshot = build_student_snapshot(s.admission_id)
        marks = snapshot['marks'] if snapshot else 0
        leaderboard.append({
            "name": s.name,
            "marks": marks,
            "points": s.points,
            "avatar": s.current_avatar
        })
    
    leaderboard.sort(key=lambda x: (x['marks'], x['points']), reverse=True)
    for i, entry in enumerate(leaderboard):
        entry['rank'] = i + 1
        
    return jsonify(leaderboard), 200

@student_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    student_id = get_jwt_identity()
    student = Student.query.get(student_id)
    if not student:
        return jsonify({"msg": "Student not found"}), 404
    return jsonify({
        "name": student.name,
        "admission_id": student.admission_id,
        "email": student.email,
        "points": student.points,
        "level": student.level,
        "avatar": student.current_avatar
    }), 200

@student_bp.route('/forum', methods=['GET', 'POST'])
@jwt_required()
def forum():
    student_id = get_jwt_identity()
    if request.method == 'POST':
        data = request.get_json()
        new_post = Forum(
            student_id=student_id,
            post=data.get('post') or '',
            poll=data.get('poll'),
            reply=None
        )
        db.session.add(new_post)
        db.session.commit()
        return jsonify({"msg": "Post created", "id": new_post.id}), 201

    return jsonify(build_forum_payload()), 200

@student_bp.route('/forum/vote/<int:post_id>', methods=['POST'])
@jwt_required()
def vote(post_id):
    post = Forum.query.get_or_404(post_id)
    post.vote += 1
    db.session.commit()
    return jsonify({"msg": "Voted", "votes": post.vote}), 200

@student_bp.route('/resources', methods=['GET'])
@jwt_required()
def get_resources():
    student_id = get_jwt_identity()
    student = Student.query.get(student_id)
    query = Resource.query
    if student and student.assigned_teacher_id:
        teacher = Teacher.query.get(student.assigned_teacher_id)
        query = query.filter_by(uploaded_by=student.assigned_teacher_id)
        if teacher and teacher.subject:
            query = query.filter_by(topic=teacher.subject)
    resources = query.all()
    return jsonify([{
        "id": r.id,
        "title": r.title,
        "file_url": r.file_url,
        "topic": r.topic or 'General'
    } for r in resources]), 200

@student_bp.route('/chatbot', methods=['POST'])
@jwt_required()
def chatbot_ask():
    data = request.get_json()
    query = data.get('query', '')
    
    if not query:
        return jsonify({"reply": "Please ask a question."}), 400

    try:
        from dotenv import load_dotenv, find_dotenv
        import os
        import google.generativeai as genai
        
        # This will automatically search every folder going upwards until it finds a .env file!
        env_file_location = find_dotenv()
        load_dotenv(env_file_location, override=True)
        
        api_key = os.getenv("GEMINI_API_KEY")
        
        print(f"DEBUG: Found .env file at -> {env_file_location}")
        print(f"DEBUG: Found API Key? {'Yes' if api_key else 'No (It is None)'}")

        if not api_key:
            return jsonify({"reply": f"API key missing. Checked file: {env_file_location}"}), 500

        # Configure Gemini
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = f"You are a helpful AI tutor for an app called PratiPariksha. Give a short, helpful answer. The student asks: {query}"
        
        print("DEBUG: Asking Gemini...")
        response = model.generate_content(prompt)
        print("DEBUG: Gemini Replied!")
        
        return jsonify({"reply": response.text}), 200
        
    except Exception as e:
        # This will print the EXACT reason it crashed to your VS Code terminal
        import traceback
        print("\n=== CHATBOT CRASHED ===")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        print(traceback.format_exc())
        print("=======================\n")
        
        return jsonify({"reply": f"System Error: {str(e)}"}), 500

@student_bp.route('/study-plan', methods=['GET'])
@jwt_required()
def get_study_plan():
    student_id = get_jwt_identity()
    snapshot = build_student_snapshot(student_id)
    if not snapshot:
        return jsonify({"msg": "Student not found"}), 404
    return jsonify({
        "student_id": snapshot['student_id'],
        "student_name": snapshot['student_name'],
        "weak_topics": snapshot['weak_topics'],
        "improvement_areas": snapshot['improvement_areas'],
        "study_plan": snapshot['study_plan']
    }), 200

@student_bp.route('/shop/buy', methods=['POST'])
@jwt_required()
def buy_avatar():
    student_id = get_jwt_identity()
    student = Student.query.get(student_id)
    data = request.get_json()
    
    avatar = data.get('avatar')
    price = int(data.get('price', 0) or 0)

    if not avatar:
        return jsonify({"msg": "Select an avatar first."}), 400
    
    inventory = student.inventory.split(',') if student.inventory else []
    
    if avatar in inventory:
        # Already owns it, just equip it
        student.current_avatar = avatar
        db.session.commit()
        return jsonify({"msg": "Avatar equipped!", "avatar": student.current_avatar, "points": student.points}), 200
        
    if student.points >= price:
        # Buy and equip
        student.points -= price
        inventory.append(avatar)
        student.inventory = ",".join(inventory)
        student.current_avatar = avatar
        db.session.commit()
        return jsonify({"msg": "Purchase successful!", "points": student.points, "avatar": student.current_avatar}), 200
    else:
        return jsonify({"msg": "Not enough points!"}), 400
