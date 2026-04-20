from flask import Flask
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from .models import db
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import event, inspect, text
from sqlalchemy.exc import OperationalError

# Get the absolute path to .env file
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env'))
load_dotenv(dotenv_path=env_path)


def normalize_database_uri(database_uri, project_root):
    if database_uri.startswith('sqlite:///') and not database_uri.startswith('sqlite:////'):
        sqlite_path = database_uri[len('sqlite:///'):]
        if not os.path.isabs(sqlite_path):
            sqlite_path = os.path.join(project_root, sqlite_path)
        database_uri = "sqlite:///" + os.path.abspath(sqlite_path).replace("\\", "/")
    return database_uri


def sqlite_db_path(database_uri):
    if database_uri.startswith('sqlite:///'):
        return Path(database_uri[len('sqlite:///'):]).resolve()
    return None


def recover_sqlite_journal(database_uri):
    db_path = sqlite_db_path(database_uri)
    if not db_path:
        return False

    journal_path = db_path.with_name(f"{db_path.name}-journal")
    if not journal_path.exists():
        return False

    backup_path = journal_path.with_name(f"{journal_path.name}.stale")
    counter = 1
    while backup_path.exists():
        backup_path = journal_path.with_name(f"{journal_path.name}.stale{counter}")
        counter += 1

    os.replace(journal_path, backup_path)
    return True


def ensure_schema_updates(app):
    with app.app_context():
        try:
            db.create_all()
            inspector = inspect(db.engine)
        except OperationalError as exc:
            if 'disk I/O error' not in str(exc) or not recover_sqlite_journal(app.config['SQLALCHEMY_DATABASE_URI']):
                raise
            db.session.remove()
            db.engine.dispose()
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
            if 'notes_url' not in resource_columns:
                db.session.execute(text("ALTER TABLE resources ADD COLUMN notes_url VARCHAR(255)"))

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

        if 'test_papers' in inspector.get_table_names():
            test_columns = {column['name'] for column in inspector.get_columns('test_papers')}
            if 'duration_minutes' not in test_columns:
                db.session.execute(text("ALTER TABLE test_papers ADD COLUMN duration_minutes INTEGER DEFAULT 60"))
            if 'scheduled_start' not in test_columns:
                db.session.execute(text("ALTER TABLE test_papers ADD COLUMN scheduled_start DATETIME"))
            if 'scheduled_end' not in test_columns:
                db.session.execute(text("ALTER TABLE test_papers ADD COLUMN scheduled_end DATETIME"))
            if 'max_loo_breaks' not in test_columns:
                db.session.execute(text("ALTER TABLE test_papers ADD COLUMN max_loo_breaks INTEGER DEFAULT 1"))
            if 'max_loo_minutes' not in test_columns:
                db.session.execute(text("ALTER TABLE test_papers ADD COLUMN max_loo_minutes INTEGER DEFAULT 5"))

        db.session.commit()


def configure_sqlite_connection(app):
    database_uri = app.config['SQLALCHEMY_DATABASE_URI']
    if not database_uri.startswith('sqlite:///'):
        return

    @event.listens_for(db.engine, 'connect')
    def set_sqlite_pragmas(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.execute('PRAGMA journal_mode=MEMORY')
        cursor.execute('PRAGMA temp_store=MEMORY')
        cursor.close()

def create_app():
    # 1. Define paths for Frontend and Database
    # basedir = .../backend/app
    basedir = os.path.abspath(os.path.dirname(__file__))
    project_root = os.path.abspath(os.path.join(basedir, '../..'))
    # frontend_path = .../frontend
    frontend_path = os.path.abspath(os.path.join(project_root, 'frontend'))
    # db_path = .../backend/instance/pratipariksha.db
    instance_dir = os.path.abspath(os.path.join(basedir, '..', 'instance'))
    os.makedirs(instance_dir, exist_ok=True)
    db_path = os.path.join(instance_dir, 'pratipariksha.db')
    uploads_path = os.path.abspath(os.path.join(basedir, '..', 'uploads'))
    os.makedirs(os.path.join(uploads_path, 'resources'), exist_ok=True)
    os.makedirs(os.path.join(uploads_path, 'notes'), exist_ok=True)

    app = Flask(__name__, static_folder=frontend_path, static_url_path='/static')
    app.config['UPLOAD_FOLDER'] = uploads_path
    app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB cap

    # 2. Database Configuration with Fallback
    # Support both common env var names so the checked-in .env works as expected.
    database_uri = (
        os.getenv('DATABASE_URL')
        or os.getenv('SQLALCHEMY_DATABASE_URI')
        or f'sqlite:///{db_path}'
    )
    database_uri = normalize_database_uri(database_uri, project_root)
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
    with app.app_context():
        configure_sqlite_connection(app)
    ensure_schema_updates(app)

    # 4. Register Blueprints
    from .api.auth import auth_bp
    from .api.student import student_bp
    from .api.teacher import teacher_bp
    from .api.admin import admin_bp
    from .api.exam import exam_bp
    from focus_mode import create_focus_mode_blueprint

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(student_bp, url_prefix='/api/student')
    app.register_blueprint(teacher_bp, url_prefix='/api/teacher')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(exam_bp, url_prefix='/api/exam')
    app.register_blueprint(create_focus_mode_blueprint(), url_prefix='/api/focus-mode')

    # 5. Frontend Routing
    @app.route('/')
    def index():
        return app.send_static_file('index.html')

    @app.route('/uploads/<path:filename>')
    def serve_upload(filename):
        from flask import send_from_directory
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    @app.route('/<path:filename>')
    def serve_frontend(filename):
        if filename.startswith('api/') or filename.startswith('uploads/'):
            from flask import abort
            abort(404)
        return app.send_static_file(filename)

    return app
