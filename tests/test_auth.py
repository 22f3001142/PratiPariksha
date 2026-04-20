import unittest
import json
from tests.base_test import BaseTestCase
from backend.app.models import Admin, Student, Teacher
from backend.app import db
from werkzeug.security import generate_password_hash


class TestAuthAPI(BaseTestCase):
    """Test cases for authentication API endpoints"""

    def test_admin_login_success(self):
        """Test successful admin login"""
        # Update admin password
        with self.app.app_context():
            admin = Admin.query.filter_by(username='test_admin').first()
            admin.password = generate_password_hash('admin123')
            db.session.commit()

        response = self.client.post('/api/auth/login', json={
            'role': 'admin',
            'username': 'test_admin',
            'password': 'admin123'
        })

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('access_token', data)
        self.assertEqual(data['role'], 'admin')
        self.assertEqual(data['username'], 'test_admin')

    def test_student_login_success(self):
        """Test successful student login"""
        # Update student password
        with self.app.app_context():
            student = Student.query.filter_by(admission_id='TEST_S101').first()
            student.password = generate_password_hash('student123')
            db.session.commit()

        response = self.client.post('/api/auth/login', json={
            'role': 'student',
            'username': 'TEST_S101',
            'password': 'student123'
        })

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('access_token', data)
        self.assertEqual(data['role'], 'student')
        self.assertEqual(data['username'], 'TEST_S101')

    def test_teacher_login_success(self):
        """Test successful teacher login"""
        # Update teacher password
        with self.app.app_context():
            teacher = Teacher.query.filter_by(employee_id='TEST_T201').first()
            teacher.password = generate_password_hash('teacher123')
            db.session.commit()

        response = self.client.post('/api/auth/login', json={
            'role': 'teacher',
            'username': 'TEST_T201',
            'password': 'teacher123'
        })

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('access_token', data)
        self.assertEqual(data['role'], 'teacher')
        self.assertEqual(data['username'], 'TEST_T201')

    def test_login_invalid_role(self):
        """Test login with invalid role - validation and error handling"""
        response = self.client.post('/api/auth/login', json={
            'role': 'invalid_role',
            'username': 'admin',
            'password': 'admin123'
        })

        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertEqual(data['msg'], 'Invalid role. Must be one of: admin, student, teacher')

    def test_login_wrong_password(self):
        """Test login with wrong password - validation and error handling"""
        response = self.client.post('/api/auth/login', json={
            'role': 'admin',
            'username': 'admin',
            'password': 'wrongpassword'
        })

        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertEqual(data['msg'], 'Bad username or password')

    def test_login_nonexistent_user(self):
        """Test login with nonexistent user - validation and error handling"""
        response = self.client.post('/api/auth/login', json={
            'role': 'admin',
            'username': 'nonexistent',
            'password': 'password'
        })

        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertEqual(data['msg'], 'Bad username or password')

    def test_login_missing_fields(self):
        """Test login with missing required fields - validation and error handling"""
        # Missing role
        response = self.client.post('/api/auth/login', json={
            'username': 'admin',
            'password': 'admin123'
        })
        self.assertEqual(response.status_code, 400)

        # Missing username
        response = self.client.post('/api/auth/login', json={
            'role': 'admin',
            'password': 'admin123'
        })
        self.assertEqual(response.status_code, 400)

        # Missing password
        response = self.client.post('/api/auth/login', json={
            'role': 'admin',
            'username': 'admin'
        })
        self.assertEqual(response.status_code, 400)

    def test_login_empty_request(self):
        """Test login with empty request body - validation and error handling"""
        response = self.client.post('/api/auth/login', json={})
        self.assertEqual(response.status_code, 400)

    def test_login_invalid_json(self):
        """Test login with invalid JSON - validation and error handling"""
        response = self.client.post('/api/auth/login',
                                  data='invalid json',
                                  content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_setup_test_users_endpoint(self):
        """Test setup test users endpoint"""
        response = self.client.post('/api/auth/setup-test-users')
        self.assertEqual(response.status_code, 201)

    def test_token_structure(self):
        """Test that JWT token contains expected claims"""
        # Update admin password
        with self.app.app_context():
            admin = Admin.query.filter_by(username='test_admin').first()
            admin.password = generate_password_hash('admin123')
            db.session.commit()

        response = self.client.post('/api/auth/login', json={
            'role': 'admin',
            'username': 'test_admin',
            'password': 'admin123'
        })

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('access_token', data)
        self.assertIn('role', data)
        self.assertIn('username', data)

        # Verify token is a string
        self.assertIsInstance(data['access_token'], str)
        self.assertGreater(len(data['access_token']), 0)


if __name__ == '__main__':
    unittest.main()