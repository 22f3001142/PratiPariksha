from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from ..models import db, Student, Forum, ForumReply, Resource, Response, Question, Exam, TestPaper, TestPaperQuestion, Teacher, StudentTeacher


def _assigned_teacher_ids(student):
    if not student:
        return []
    ids = [row.teacher_id for row in StudentTeacher.query.filter_by(student_id=student.admission_id).all()]
    if not ids and student.assigned_teacher_id:
        ids = [student.assigned_teacher_id]
    return ids
from sqlalchemy import func
from datetime import datetime
from ..services import build_forum_payload, build_student_snapshot, generate_study_bot_reply, is_correct, topic_label
from ..uploads import save_upload
import os

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

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
        "level_progress": student.points % 10,
        "level_progress_percent": int(((student.points % 10) / 10) * 100),
        "assigned_teacher_id": student.assigned_teacher_id
    }), 200

@student_bp.route('/upcoming-tests', methods=['GET'])
@jwt_required()
def get_upcoming_tests():
    student_id = get_jwt_identity()
    student = Student.query.get(student_id)
    exam = Exam.query.first()
    teacher_ids = _assigned_teacher_ids(student)
    query = TestPaper.query
    if teacher_ids:
        query = query.filter(TestPaper.created_by.in_(teacher_ids))
    tests_from_bank = query.order_by(TestPaper.created_at.desc()).all()
    tests = []
    for test in tests_from_bank:
        is_active = bool(exam and exam.status != 'stopped' and exam.test_id == test.id)
        tests.append({
            "id": test.id,
            "test_name": test.title,
            "date": exam.start_time.isoformat() if is_active and exam.start_time else (test.scheduled_start.isoformat() if test.scheduled_start else (test.created_at.isoformat() if test.created_at else "TBD")),
            "status": exam.status if is_active else "available",
            "topic": test.topic or "General",
            "description": test.description or "",
            "question_count": len(test.questions),
            "duration_minutes": test.duration_minutes or 60,
            "scheduled_start": test.scheduled_start.isoformat() if test.scheduled_start else None,
            "scheduled_end": test.scheduled_end.isoformat() if test.scheduled_end else None,
            "max_loo_breaks": test.max_loo_breaks or 0,
            "max_loo_minutes": test.max_loo_minutes or 0,
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


@student_bp.route('/forum/<int:post_id>/reply', methods=['POST'])
@jwt_required()
def student_reply(post_id):
    student_id = get_jwt_identity()
    Forum.query.get_or_404(post_id)
    data = request.get_json() or {}
    body = (data.get('body') or '').strip()
    if not body:
        return jsonify({"msg": "Reply cannot be empty."}), 400
    reply = ForumReply(post_id=post_id, author_role='student', author_id=student_id, body=body)
    db.session.add(reply)
    db.session.commit()
    return jsonify({"msg": "Reply posted", "id": reply.id}), 201

@student_bp.route('/resources', methods=['GET'])
@jwt_required()
def get_resources():
    student_id = get_jwt_identity()
    student = Student.query.get(student_id)
    teacher_ids = _assigned_teacher_ids(student)
    query = Resource.query
    if teacher_ids:
        query = query.filter(Resource.uploaded_by.in_(teacher_ids))
    resources = query.all()
    return jsonify([{
        "id": r.id,
        "title": r.title,
        "file_url": r.file_url,
        "topic": r.topic or 'General',
        "notes_url": r.notes_url,
    } for r in resources]), 200


@student_bp.route('/resources/<int:resource_id>/notes', methods=['POST'])
@jwt_required()
def add_resource_notes(resource_id):
    resource = Resource.query.get_or_404(resource_id)
    data = request.get_json() or {}
    notes_url = (data.get('notes_url') or '').strip()
    if not notes_url or not (notes_url.startswith('http://') or notes_url.startswith('https://')):
        return jsonify({"msg": "Provide a valid http(s) URL."}), 400
    resource.notes_url = notes_url
    db.session.commit()
    return jsonify({"msg": "Notes linked", "notes_url": resource.notes_url}), 200


@student_bp.route('/resources/<int:resource_id>/notes-upload', methods=['POST'])
@jwt_required()
def upload_resource_notes(resource_id):
    resource = Resource.query.get_or_404(resource_id)
    file = request.files.get('file')
    if not file or not file.filename:
        return jsonify({"msg": "No file provided."}), 400
    try:
        notes_url = save_upload(file, 'notes')
    except ValueError as exc:
        return jsonify({"msg": str(exc)}), 400
    resource.notes_url = notes_url
    db.session.commit()
    return jsonify({"msg": "Notes uploaded", "notes_url": notes_url}), 200


@student_bp.route('/chatbot', methods=['POST'])
@jwt_required()
def chatbot_ask():
    data = request.get_json()
    query = data.get('query', '')

    if not query:
        return jsonify({"reply": "Please ask a question."}), 400

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or OpenAI is None:
        return jsonify({"reply": "AI tutor is not configured. Set OPENAI_API_KEY in the environment."}), 503

    model_name = os.getenv("OPENAI_CHATBOT_MODEL", "gpt-4.1-mini")
    prompt = f"You are a helpful AI tutor for an app called PratiPariksha. Give a short, helpful answer. The student asks: {query}"

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
        )
        reply_text = (response.choices[0].message.content or '').strip()
        if not reply_text:
            return jsonify({"reply": "I could not generate a reply. Please try again."}), 502
        return jsonify({"reply": reply_text}), 200
    except Exception:
        return jsonify({"reply": "The AI tutor is temporarily unavailable. Please try again later."}), 502

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
