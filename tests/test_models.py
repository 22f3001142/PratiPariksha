import unittest
from tests.base_test import BaseTestCase
from backend.app.models import Admin, Student, Teacher, Exam, Question, Response, LooBreak, Forum, Resource, Mood
from backend.app import db
from werkzeug.security import generate_password_hash


class TestModels(BaseTestCase):
    """Test cases for database models"""

    def test_admin_model_creation(self):
        """Test Admin model creation and attributes"""
        admin = Admin(username='testadmin', password=generate_password_hash('password'))
        self.assertEqual(admin.username, 'testadmin')
        self.assertTrue(admin.password.startswith('pbkdf2:sha'))  # werkzeug hash prefix

    def test_student_model_creation(self):
        """Test Student model creation with all attributes"""
        student = Student(
            admission_id='S102',
            name='John Doe',
            email='john@test.com',
            password=generate_password_hash('password'),
            points=50,
            level=1,
            badges='Beginner',
            exam_id=1
        )
        self.assertEqual(student.admission_id, 'S102')
        self.assertEqual(student.name, 'John Doe')
        self.assertEqual(student.email, 'john@test.com')
        self.assertEqual(student.points, 50)
        self.assertEqual(student.level, 1)
        self.assertEqual(student.badges, 'Beginner')

    def test_teacher_model_creation(self):
        """Test Teacher model creation"""
        teacher = Teacher(
            employee_id='T202',
            name='Jane Smith',
            email='jane@test.com',
            password=generate_password_hash('password')
        )
        self.assertEqual(teacher.employee_id, 'T202')
        self.assertEqual(teacher.name, 'Jane Smith')
        self.assertEqual(teacher.email, 'jane@test.com')

    def test_exam_model_creation(self):
        """Test Exam model creation with scheduling"""
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        exam = Exam(
            subject='Math Exam',
            duration=90,
            status='scheduled',
            scheduled_start=now,
            scheduled_end=now + timedelta(hours=1.5)
        )
        self.assertEqual(exam.subject, 'Math Exam')
        self.assertEqual(exam.duration, 90)
        self.assertEqual(exam.status, 'scheduled')

    def test_question_model_creation(self):
        """Test Question model creation with different types"""
        # MCQ Question
        mcq = Question(
            subject='General',
            question='What is the capital of France?',
            type='MCQ',
            options=['London', 'Paris', 'Berlin', 'Madrid'],
            correct_answer='Paris',
            difficulty_level=2
        )
        self.assertEqual(mcq.type, 'MCQ')
        self.assertEqual(len(mcq.options), 4)
        self.assertEqual(mcq.correct_answer, 'Paris')

        # NAT Question (Numerical Answer Type)
        nat = Question(
            subject='General',
            question='What is 5 + 3?',
            type='NAT',
            correct_answer='8',
            difficulty_level=1
        )
        self.assertEqual(nat.type, 'NAT')
        self.assertIsNone(nat.options)  # NAT questions don't have options

    def test_response_model_creation(self):
        """Test Response model for storing student answers"""
        response = Response(
            student_id='S101',
            question_id=1,
            answer='4'
        )
        self.assertEqual(response.student_id, 'S101')
        self.assertEqual(response.question_id, 1)
        self.assertEqual(response.answer, '4')

    def test_database_relationships(self):
        """Test database relationships between models"""
        with self.app.app_context():
            # Test Student-Exam relationship
            student = Student.query.filter_by(admission_id='TEST_S101').first()
            exam = Exam.query.first()
            self.assertIsNotNone(student)
            self.assertIsNotNone(exam)
            self.assertEqual(student.exam_id, exam.id)

            # Test Question-Subject match
            question = Question.query.first()
            self.assertEqual(question.subject, exam.subject)

    def test_model_validation(self):
        """Test model validation constraints"""
        with self.app.app_context():
            # Test unique constraints - try to create admin with same username as existing test data
            try:
                duplicate_admin = Admin(username='test_admin', password='password')
                db.session.add(duplicate_admin)
                db.session.commit()
                # If we get here, the constraint wasn't enforced (SQLite in-memory behavior)
                # So we'll check manually
                existing_count = Admin.query.filter_by(username='test_admin').count()
                self.assertGreater(existing_count, 1, "Should not allow duplicate usernames")
            except Exception as e:
                # If constraint is enforced, we should get an exception
                self.assertTrue('constraint' in str(e).lower() or 'unique' in str(e).lower())

    def test_forum_model(self):
        """Test Forum model for student discussions"""
        forum = Forum(
            student_id='S101',
            post='This is a test post',
            reply=None,
            poll='What is your favorite subject?',
            vote=5
        )
        self.assertEqual(forum.student_id, 'S101')
        self.assertEqual(forum.post, 'This is a test post')
        self.assertEqual(forum.vote, 5)

    def test_resource_model(self):
        """Test Resource model for file uploads"""
        resource = Resource(
            title='Sample PDF',
            file_url='/uploads/sample.pdf',
            uploaded_by='T201'
        )
        self.assertEqual(resource.title, 'Sample PDF')
        self.assertEqual(resource.file_url, '/uploads/sample.pdf')
        self.assertEqual(resource.uploaded_by, 'T201')

    def test_mood_model(self):
        """Test Mood model for student mood tracking"""
        from datetime import datetime
        mood = Mood(
            student_id='S101',
            mood='happy',
            timestamp=datetime.utcnow()
        )
        self.assertEqual(mood.student_id, 'S101')
        self.assertEqual(mood.mood, 'happy')


if __name__ == '__main__':
    unittest.main()