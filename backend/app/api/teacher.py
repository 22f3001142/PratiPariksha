from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from werkzeug.utils import secure_filename
from ..models import (
    db,
    Student,
    Teacher,
    Question,
    Response,
    Forum,
    ForumReply,
    Resource,
    TestPaper,
    TestPaperQuestion,
)
from ..uploads import save_upload, ALLOWED_EXTENSIONS
import pandas as pd
import numpy as np
from ..services import build_forum_payload, build_teacher_analytics

teacher_bp = Blueprint('teacher', __name__)

@teacher_bp.route('/analytics', methods=['GET'])
@jwt_required()
def get_analytics():
    claims = get_jwt()
    if claims.get('role') != 'teacher':
        return jsonify({"msg": "Unauthorized"}), 403

    return jsonify(build_teacher_analytics(get_jwt_identity())), 200

@teacher_bp.route('/questions', methods=['GET', 'POST'])
@jwt_required()
def manage_questions():
    claims = get_jwt()
    if claims.get('role') != 'teacher':
        return jsonify({"msg": "Unauthorized"}), 403

    if request.method == 'POST':
        teacher = Teacher.query.get(get_jwt_identity())
        data = request.get_json()
        new_q = Question(
            question=data.get('question'),
            type=data.get('type'),
            options=data.get('options'),
            correct_answer=data.get('correct_answer'),
            difficulty_level=data.get('difficulty_level', 1),
            topic=data.get('topic') or (teacher.subject if teacher else 'General'),
            subtopic=data.get('subtopic') or data.get('topic') or (teacher.subject if teacher else 'General'),
            explanation=data.get('explanation') or ''
        )
        db.session.add(new_q)
        db.session.commit()
        return jsonify({"msg": "Question created", "id": new_q.id}), 201

    teacher = Teacher.query.get(get_jwt_identity())
    topic = request.args.get('topic')
    subtopic = request.args.get('subtopic')
    query = Question.query
    if teacher and teacher.subject:
        query = query.filter_by(topic=teacher.subject)
    if topic:
        query = query.filter_by(topic=topic)
    if subtopic:
        query = query.filter_by(subtopic=subtopic)
    questions = query.order_by(Question.topic.asc(), Question.subtopic.asc(), Question.id.asc()).all()
    return jsonify([{
        "id": q.id,
        "question": q.question,
        "type": q.type,
        "options": q.options,
        "correct_answer": q.correct_answer,
        "difficulty_level": q.difficulty_level,
        "topic": q.topic or 'General',
        "subtopic": q.subtopic or 'General',
        "explanation": q.explanation or ''
    } for q in questions]), 200

@teacher_bp.route('/question-topics', methods=['GET'])
@jwt_required()
def get_question_topics():
    claims = get_jwt()
    if claims.get('role') != 'teacher':
        return jsonify({"msg": "Unauthorized"}), 403

    teacher = Teacher.query.get(get_jwt_identity())
    query = Question.query
    if teacher and teacher.subject:
        query = query.filter_by(topic=teacher.subject)
    questions = query.order_by(Question.topic.asc(), Question.subtopic.asc()).all()
    grouped = {}
    for question in questions:
        topic = question.topic or 'General'
        grouped.setdefault(topic, set()).add(question.subtopic or 'General')
    return jsonify([
        {
            'topic': topic,
            'subtopics': sorted(list(subtopics))
        }
        for topic, subtopics in grouped.items()
    ]), 200

@teacher_bp.route('/tests', methods=['GET', 'POST'])
@jwt_required()
def manage_tests():
    claims = get_jwt()
    if claims.get('role') != 'teacher':
        return jsonify({"msg": "Unauthorized"}), 403

    if request.method == 'POST':
        teacher_id = get_jwt_identity()
        teacher = Teacher.query.get(teacher_id)
        data = request.get_json()
        question_ids = data.get('question_ids') or []
        if not question_ids:
            return jsonify({"msg": "Select at least one question"}), 400

        test = TestPaper(
            title=data.get('title') or 'Untitled Test',
            topic=data.get('topic') or (teacher.subject if teacher else 'General'),
            description=data.get('description') or '',
            created_by=teacher_id,
            duration_minutes=_parse_int(data.get('duration_minutes'), 60, minimum=1),
            scheduled_start=_parse_dt(data.get('scheduled_start')),
            scheduled_end=_parse_dt(data.get('scheduled_end')),
            max_loo_breaks=_parse_int(data.get('max_loo_breaks'), 1, minimum=0),
            max_loo_minutes=_parse_int(data.get('max_loo_minutes'), 5, minimum=0),
        )
        db.session.add(test)
        db.session.flush()

        for index, question_id in enumerate(question_ids):
            db.session.add(TestPaperQuestion(
                test_id=test.id,
                question_id=question_id,
                sort_order=index
            ))

        db.session.commit()
        return jsonify({"msg": "Test created", "test_id": test.id}), 201

    teacher_id = get_jwt_identity()
    teacher = Teacher.query.get(teacher_id)
    query = TestPaper.query.filter_by(created_by=teacher_id)
    if teacher and teacher.subject:
        query = query.filter_by(topic=teacher.subject)
    tests = query.order_by(TestPaper.created_at.desc()).all()
    payload = []
    for test in tests:
        payload.append({
            'id': test.id,
            'title': test.title,
            'topic': test.topic,
            'description': test.description,
            'created_at': test.created_at.isoformat() if test.created_at else None,
            'question_count': len(test.questions),
            'duration_minutes': test.duration_minutes,
            'scheduled_start': test.scheduled_start.isoformat() if test.scheduled_start else None,
            'scheduled_end': test.scheduled_end.isoformat() if test.scheduled_end else None,
            'max_loo_breaks': test.max_loo_breaks,
            'max_loo_minutes': test.max_loo_minutes,
        })
    return jsonify(payload), 200


@teacher_bp.route('/tests/<int:test_id>', methods=['PATCH'])
@jwt_required()
def update_test(test_id):
    claims = get_jwt()
    if claims.get('role') != 'teacher':
        return jsonify({"msg": "Unauthorized"}), 403
    teacher_id = get_jwt_identity()
    test = TestPaper.query.filter_by(id=test_id, created_by=teacher_id).first()
    if not test:
        return jsonify({"msg": "Test not found"}), 404
    data = request.get_json() or {}
    if 'duration_minutes' in data:
        test.duration_minutes = _parse_int(data.get('duration_minutes'), test.duration_minutes or 60, minimum=1)
    if 'scheduled_start' in data:
        test.scheduled_start = _parse_dt(data.get('scheduled_start'))
    if 'scheduled_end' in data:
        test.scheduled_end = _parse_dt(data.get('scheduled_end'))
    if 'max_loo_breaks' in data:
        test.max_loo_breaks = _parse_int(data.get('max_loo_breaks'), test.max_loo_breaks or 0, minimum=0)
    if 'max_loo_minutes' in data:
        test.max_loo_minutes = _parse_int(data.get('max_loo_minutes'), test.max_loo_minutes or 0, minimum=0)
    db.session.commit()
    return jsonify({"msg": "Test updated"}), 200


def _parse_int(value, default, minimum=None):
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    if minimum is not None and n < minimum:
        return minimum
    return n


def _parse_dt(value):
    if not value:
        return None
    try:
        s = str(value).replace('Z', '+00:00')
        from datetime import datetime as _dt
        return _dt.fromisoformat(s)
    except (TypeError, ValueError):
        return None

@teacher_bp.route('/forum/reply/<int:post_id>', methods=['POST'])
@jwt_required()
def reply_forum(post_id):
    claims = get_jwt()
    if claims.get('role') != 'teacher':
        return jsonify({"msg": "Unauthorized"}), 403

    Forum.query.get_or_404(post_id)
    teacher_id = get_jwt_identity()
    data = request.get_json() or {}
    body = (data.get('body') or data.get('reply') or '').strip()
    if not body:
        return jsonify({"msg": "Reply cannot be empty."}), 400
    reply = ForumReply(post_id=post_id, author_role='teacher', author_id=teacher_id, body=body)
    db.session.add(reply)
    db.session.commit()
    return jsonify({"msg": "Reply added", "id": reply.id}), 201

@teacher_bp.route('/forum', methods=['GET'])
@jwt_required()
def get_forum():
    claims = get_jwt()
    if claims.get('role') != 'teacher':
        return jsonify({"msg": "Unauthorized"}), 403
    return jsonify(build_forum_payload(get_jwt_identity())), 200

@teacher_bp.route('/resources', methods=['GET', 'POST'])
@jwt_required()
def upload_resource():
    claims = get_jwt()
    if claims.get('role') != 'teacher':
        return jsonify({"msg": "Unauthorized"}), 403

    if request.method == 'GET':
        teacher_id = get_jwt_identity()
        teacher = Teacher.query.get(teacher_id)
        query = Resource.query.filter_by(uploaded_by=teacher_id)
        if teacher and teacher.subject:
            query = query.filter_by(topic=teacher.subject)
        resources = query.order_by(Resource.topic.asc(), Resource.title.asc()).all()
        return jsonify([{
            'id': resource.id,
            'title': resource.title,
            'topic': resource.topic or 'General',
            'file_url': resource.file_url,
            'notes_url': resource.notes_url,
        } for resource in resources]), 200

    teacher_id = get_jwt_identity()
    teacher = Teacher.query.get(teacher_id)

    if request.content_type and request.content_type.startswith('multipart/form-data'):
        title = (request.form.get('title') or '').strip()
        topic = (request.form.get('topic') or '').strip() or (teacher.subject if teacher else 'General')
        url_field = (request.form.get('file_url') or '').strip()
        file = request.files.get('file')
        if file and file.filename:
            try:
                file_url = save_upload(file, 'resources')
            except ValueError as exc:
                return jsonify({"msg": str(exc)}), 400
        elif url_field:
            file_url = url_field
        else:
            return jsonify({"msg": "Provide a file or a URL."}), 400
    else:
        data = request.get_json() or {}
        title = (data.get('title') or '').strip()
        topic = (data.get('topic') or '').strip() or (teacher.subject if teacher else 'General')
        file_url = (data.get('file_url') or '').strip()
        if not file_url:
            return jsonify({"msg": "Provide a file or a URL."}), 400

    if not title:
        return jsonify({"msg": "Title is required."}), 400

    new_res = Resource(
        title=title,
        file_url=file_url,
        uploaded_by=teacher_id,
        topic=topic,
    )
    db.session.add(new_res)
    db.session.commit()
    return jsonify({"msg": "Resource uploaded", "id": new_res.id, "file_url": file_url}), 201
