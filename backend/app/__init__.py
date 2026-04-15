from flask import Flask
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from .models import db
import os
from dotenv import load_dotenv
from sqlalchemy import inspect, text

# Get the absolute path to .env file
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env'))
load_dotenv(dotenv_path=env_path)


def ensure_schema_updates(app):
    with app.app_context():
        db.create_all()
        inspector = inspect(db.engine)

        if 'questions' in inspector.get_table_names():
            question_columns = {column['name'] for column in inspector.get_columns('questions')}
            statements = []
            if 'topic' not in question_columns:
                statements.append("ALTER TABLE questions ADD COLUMN topic VARCHAR(100) DEFAULT 'General'")
            if 'subtopic' not in question_columns:
                statements.append("ALTER TABLE questions ADD COLUMN subtopic VARCHAR(100) DEFAULT 'General'")
            if 'explanation' not in question_columns:
                statements.append("ALTER TABLE questions ADD COLUMN explanation TEXT DEFAULT ''")
            for statement in statements:
                db.session.execute(text(statement))

        if 'resources' in inspector.get_table_names():
            resource_columns = {column['name'] for column in inspector.get_columns('resources')}
            if 'topic' not in resource_columns:
                db.session.execute(text("ALTER TABLE resources ADD COLUMN topic VARCHAR(100) DEFAULT 'General'"))

        if 'students' in inspector.get_table_names():
            student_columns = {column['name'] for column in inspector.get_columns('students')}
            if 'assigned_teacher_id' not in student_columns:
                db.session.execute(text("ALTER TABLE students ADD COLUMN assigned_teacher_id VARCHAR(50)"))

        if 'teachers' in inspector.get_table_names():
            teacher_columns = {column['name'] for column in inspector.get_columns('teachers')}
            if 'subject' not in teacher_columns:
                db.session.execute(text("ALTER TABLE teachers ADD COLUMN subject VARCHAR(100) DEFAULT 'Mathematics'"))

        if 'exams' in inspector.get_table_names():
            exam_columns = {column['name'] for column in inspector.get_columns('exams')}
            if 'test_id' not in exam_columns:
                db.session.execute(text("ALTER TABLE exams ADD COLUMN test_id INTEGER"))

        db.session.commit()

def create_app():
    # 1. Define paths for Frontend and Database
    # basedir = .../backend/app
    basedir = os.path.abspath(os.path.dirname(__file__))
    project_root = os.path.abspath(os.path.join(basedir, '../..'))
    # frontend_path = .../frontend
    frontend_path = os.path.abspath(os.path.join(project_root, 'frontend'))
    # db_path = .../backend/instance/pratipariksha.db
    db_path = os.path.join(basedir, '..', 'instance', 'pratipariksha.db')

    app = Flask(__name__, static_folder=frontend_path, static_url_path='/static')

    # 2. Database Configuration with Fallback
    # Support both common env var names so the checked-in .env works as expected.
    database_uri = (
        os.getenv('DATABASE_URL')
        or os.getenv('SQLALCHEMY_DATABASE_URI')
        or f'sqlite:///{db_path}'
    )
    if database_uri.startswith('sqlite:///') and not database_uri.startswith('sqlite:////'):
        sqlite_path = database_uri[len('sqlite:///'):]
        database_uri = f"sqlite:///{os.path.join(project_root, sqlite_path)}"
    app.config['SQLALCHEMY_DATABASE_URI'] = database_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Ensure a JWT secret key exists even if the .env file isn't loaded
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY') or 'dev-secret-key-replace-later'

    print(f"Using database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")

    # 3. Initialize Extensions
    from flask_cors import CORS
    from flask_jwt_extended import JWTManager
    
    db.init_app(app)
    JWTManager(app)
    CORS(app)
    ensure_schema_updates(app)

    # 4. Register Blueprints
    from .api.auth import auth_bp
    from .api.student import student_bp
    from .api.teacher import teacher_bp
    from .api.admin import admin_bp
    from .api.exam import exam_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(student_bp, url_prefix='/api/student')
    app.register_blueprint(teacher_bp, url_prefix='/api/teacher')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(exam_bp, url_prefix='/api/exam')

    # 5. Frontend Routing
    @app.route('/')
    def index():
        return app.send_static_file('index.html')

    @app.route('/<path:filename>')
    def serve_frontend(filename):
        if filename.startswith('api/'):
            from flask import abort
            abort(404)
        return app.send_static_file(filename)

    return app
