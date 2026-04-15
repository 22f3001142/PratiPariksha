from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from ..models import (
    db,
    Student,
    Teacher,
    Question,
    Response,
    Forum,
    Resource,
    TestPaper,
    TestPaperQuestion,
)
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
            created_by=teacher_id
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
        })
    return jsonify(payload), 200

@teacher_bp.route('/forum/reply/<int:post_id>', methods=['POST'])
@jwt_required()
def reply_forum(post_id):
    claims = get_jwt()
    if claims.get('role') != 'teacher':
        return jsonify({"msg": "Unauthorized"}), 403
        
    post = Forum.query.get_or_404(post_id)
    data = request.get_json()
    post.reply = data.get('reply')
    db.session.commit()
    return jsonify({"msg": "Reply added"}), 200

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
        } for resource in resources]), 200

    teacher_id = get_jwt_identity()
    teacher = Teacher.query.get(teacher_id)
    data = request.get_json()
    new_res = Resource(
        title=data.get('title'),
        file_url=data.get('file_url'),
        uploaded_by=teacher_id,
        topic=data.get('topic') or (teacher.subject if teacher else 'General')
    )
    db.session.add(new_res)
    db.session.commit()
    return jsonify({"msg": "Resource uploaded"}), 201
