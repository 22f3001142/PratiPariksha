import unittest
import os
from backend.app import create_app, db
from backend.app.models import Admin, Student, Teacher, Exam, Question, Response


class BaseTestCase(unittest.TestCase):
    """Base test case with database setup and teardown"""

    def setUp(self):
        """Set up test database before each test"""
        # Set testing environment variable to prevent .env loading
        os.environ['TESTING'] = '1'
        # Set a default database URL for testing
        os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['JWT_SECRET_KEY'] = 'test-secret-key'
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()
            # Create test data
            self._create_test_data()

    def tearDown(self):
        """Clean up after each test"""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

        # Remove testing flag and database URL
        os.environ.pop('TESTING', None)
        os.environ.pop('DATABASE_URL', None)

    def _create_test_data(self):
        """Create test data for all tests"""
        # Clear existing data first
        try:
            db.session.query(Response).delete()
            db.session.query(Forum).delete()
            db.session.query(Mood).delete()
            db.session.query(LooBreak).delete()
            db.session.query(Resource).delete()
            db.session.query(Question).delete()
            db.session.query(Exam).delete()
            db.session.query(Student).delete()
            db.session.query(Teacher).delete()
            db.session.query(Admin).delete()
            db.session.commit()
        except:
            db.session.rollback()

        # Create admin with unique test username
        admin = Admin(username='test_admin', password='hashed_password')
        db.session.add(admin)

        # Create exam
        exam = Exam(
            subject='Test Exam',
            duration=60,
            status='started',  # Set to 'started' for testing submit functionality
            scheduled_start=None,
            scheduled_end=None
        )
        db.session.add(exam)

        # Create student with unique test ID
        student = Student(
            admission_id='TEST_S101',
            name='Test Student',
            email='test_student@test.com',
            password='hashed_password',
            points=100,
            level=2,
            badges='Top Performer',
            exam_id=1
        )
        db.session.add(student)

        # Create teacher with unique test ID
        teacher = Teacher(
            employee_id='TEST_T201',
            name='Test Teacher',
            email='test_teacher@test.com',
            password='hashed_password'
        )
        db.session.add(teacher)

        # Create question
        question = Question(
            subject='Test Exam',
            question='What is 2+2?',
            type='MCQ',
            options=['3', '4', '5', '6'],
            correct_answer='4',
            difficulty_level=1
        )
        db.session.add(question)

        db.session.commit()

    def get_auth_token(self, role='admin', username='test_admin', password='admin123'):
        """Helper method to get authentication token"""
        from werkzeug.security import generate_password_hash, check_password_hash

        # Update password hash for test user
        with self.app.app_context():
            if role == 'admin':
                user = Admin.query.filter_by(username=username).first()
            elif role == 'student':
                user = Student.query.filter_by(admission_id=username).first()
            elif role == 'teacher':
                user = Teacher.query.filter_by(employee_id=username).first()

            if user:
                user.password = generate_password_hash(password)
                db.session.commit()

        # Login to get token
        response = self.client.post('/api/auth/login', json={
            'role': role,
            'username': username,
            'password': password
        })
        if response.status_code == 200:
            return response.get_json()['access_token']
        return None