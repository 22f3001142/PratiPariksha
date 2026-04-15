from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from werkzeug.security import check_password_hash, generate_password_hash
from ..models import db, Admin, Student, Teacher

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    role = data.get('role')
    username = data.get('username')
    password = data.get('password')

    if role == 'admin':
        user = Admin.query.filter_by(username=username).first()
        display_name = 'Administrator' if user else None
    elif role == 'student':
        user = Student.query.filter_by(admission_id=username).first()
        display_name = user.name if user else None
    elif role == 'teacher':
        user = Teacher.query.filter_by(employee_id=username).first()
        display_name = user.name if user else None
    else:
        return jsonify({"msg": "Invalid role"}), 400

    if user and check_password_hash(user.password, password):
        # Pass only username as identity string to avoid "Subject must be a string" error in some versions or configurations
        # or use additional_claims for the role
        access_token = create_access_token(identity=username, additional_claims={"role": role})
        return jsonify(
            access_token=access_token,
            role=role,
            username=username,
            user_id=username,
            display_name=display_name or username
        ), 200

    return jsonify({"msg": "Bad username or password"}), 401

@auth_bp.route('/setup-test-users', methods=['POST'])
def setup_test_users():
    if not Student.query.filter_by(admission_id='S101').first():
        student = Student(
            admission_id='S101',
            name='Test Student',
            email='student@test.com',
            password=generate_password_hash('password123', method='pbkdf2:sha256'),
            points=100,
            level=2,
            badges='Top Performer'
        )
        db.session.add(student)
    
    if not Teacher.query.filter_by(employee_id='T201').first():
        teacher = Teacher(
            employee_id='T201',
            name='Test Teacher',
            email='teacher@test.com',
            password=generate_password_hash('password123', method='pbkdf2:sha256')
        )
        db.session.add(teacher)
    
    db.session.commit()
    return jsonify({"msg": "Test users created"}), 201
