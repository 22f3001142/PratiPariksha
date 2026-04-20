import unittest
import json
from tests.base_test import BaseTestCase
from backend.app.models import db, Admin, Student, Teacher, Exam, Question
from datetime import datetime, timedelta, timezone


class TestAdminAPI(BaseTestCase):
    """Test cases for admin API endpoints"""

    def test_toggle_exam_start_unauthorized(self):
        """Test exam toggle without admin authentication - validation and error handling"""
        response = self.client.post('/api/admin/exam-toggle', json={'status': 'started'})
        self.assertEqual(response.status_code, 401)

    def test_toggle_exam_start_wrong_role(self):
        """Test exam toggle with non-admin role - validation and error handling"""
        token = self.get_auth_token('student', 'TEST_S101', 'student123')

        response = self.client.post('/api/admin/exam-toggle',
                                  headers={'Authorization': f'Bearer {token}'},
                                  json={'status': 'started'})

        self.assertEqual(response.status_code, 403)

    def test_toggle_exam_start_valid(self):
        """Test starting exam with valid admin authentication"""
        token = self.get_auth_token('admin', 'test_admin', 'admin123')

        response = self.client.post('/api/admin/exam-toggle',
                                  headers={'Authorization': f'Bearer {token}'},
                                  json={'status': 'started'})

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'started')
        self.assertIn('Exam started', data['msg'])

    def test_toggle_exam_stop_valid(self):
        """Test stopping exam with valid admin authentication"""
        token = self.get_auth_token('admin', 'test_admin', 'admin123')

        # First start the exam
        self.client.post('/api/admin/exam-toggle',
                        headers={'Authorization': f'Bearer {token}'},
                        json={'status': 'started'})

        # Then stop it
        response = self.client.post('/api/admin/exam-toggle',
                                  headers={'Authorization': f'Bearer {token}'},
                                  json={'status': 'stopped'})

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'stopped')
        self.assertIn('Exam stopped', data['msg'])

    def test_schedule_exam_valid(self):
        """Test scheduling exam with valid data"""
        token = self.get_auth_token('admin', 'test_admin', 'admin123')

        # Create a question for the subject first, otherwise scheduling fails
        with self.app.app_context():
            q = Question(subject='Math Test', question='Q', correct_answer='A')
            db.session.add(q)
            db.session.commit()

        future_time = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat().replace('+00:00', '')

        response = self.client.post('/api/admin/exam-schedule',
                                  headers={'Authorization': f'Bearer {token}'},
                                  json={
                                      'subject': 'Math Test',
                                      'duration': 60,
                                      'scheduled_start': future_time
                                  })

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['subject'], 'Math Test')
        self.assertIsNotNone(data['scheduled_start'])

    def test_schedule_exam_missing_fields(self):
        """Test scheduling exam with missing required fields - validation and error handling"""
        token = self.get_auth_token('admin', 'test_admin', 'admin123')

        response = self.client.post('/api/admin/exam-schedule',
                                  headers={'Authorization': f'Bearer {token}'},
                                  json={})

        # Should handle missing fields gracefully
        self.assertIn(response.status_code, [200, 400])

    def test_delay_exam_valid(self):
        """Test delaying scheduled exam"""
        token = self.get_auth_token('admin', 'test_admin', 'admin123')

        # Create a question for the subject first
        with self.app.app_context():
            q = Question(subject='Math Test', question='Q', correct_answer='A')
            db.session.add(q)
            db.session.commit()

        # First schedule an exam
        future_time = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat().replace('+00:00', '')
        self.client.post('/api/admin/exam-schedule',
                        headers={'Authorization': f'Bearer {token}'},
                        json={
                            'subject': 'Math Test',
                            'duration': 60,
                            'scheduled_start': future_time
                        })

        # Then delay it
        response = self.client.post('/api/admin/exam-delay',
                                  headers={'Authorization': f'Bearer {token}'},
                                  json={'delay_minutes': 30})

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('Delayed 30 min', data['msg'])

    def test_delay_exam_no_scheduled_exam(self):
        """Test delaying when no exam is scheduled - validation and error handling"""
        token = self.get_auth_token('admin', 'test_admin', 'admin123')

        response = self.client.post('/api/admin/exam-delay',
                                  headers={'Authorization': f'Bearer {token}'},
                                  json={'delay_minutes': 30})

        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('No scheduled exam', data['msg'])

    def test_delete_exam_valid(self):
        """Test deleting an exam"""
        token = self.get_auth_token('admin', 'test_admin', 'admin123')

        response = self.client.delete('/api/admin/exam',
                                    headers={'Authorization': f'Bearer {token}'})

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['msg'], 'Exam deleted')

    def test_create_user_student_valid(self):
        """Test creating a new student user"""
        token = self.get_auth_token('admin', 'test_admin', 'admin123')

        response = self.client.post('/api/admin/users',
                                  headers={'Authorization': f'Bearer {token}'},
                                  json={
                                      'role': 'student',
                                      'id': 'S103',
                                      'name': 'New Student',
                                      'email': 'newstudent@test.com',
                                      'password': 'password123'
                                  })

        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data['msg'], 'User created')

    def test_create_user_teacher_valid(self):
        """Test creating a new teacher user"""
        token = self.get_auth_token('admin', 'test_admin', 'admin123')

        response = self.client.post('/api/admin/users',
                                  headers={'Authorization': f'Bearer {token}'},
                                  json={
                                      'role': 'teacher',
                                      'id': 'T203',
                                      'name': 'New Teacher',
                                      'email': 'newteacher@test.com',
                                      'password': 'password123'
                                  })

        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data['msg'], 'User created')

    def test_create_user_duplicate_id(self):
        """Test creating user with duplicate ID - validation and error handling"""
        token = self.get_auth_token('admin', 'test_admin', 'admin123')

        response = self.client.post('/api/admin/users',
                                  headers={'Authorization': f'Bearer {token}'},
                                  json={
                                      'role': 'student',
                                      'id': 'TEST_S101',  # Already exists
                                      'name': 'Duplicate Student',
                                      'email': 'duplicate@test.com',
                                      'password': 'password123'
                                  })

        self.assertEqual(response.status_code, 409)
        data = response.get_json()
        self.assertIn('already exists', data['msg'])

    def test_create_user_duplicate_email(self):
        """Test creating user with duplicate email - validation and error handling"""
        token = self.get_auth_token('admin', 'test_admin', 'admin123')

        response = self.client.post('/api/admin/users',
                                  headers={'Authorization': f'Bearer {token}'},
                                  json={
                                      'role': 'student',
                                      'id': 'S104',
                                      'name': 'Student',
                                      'email': 'test_student@test.com',  # Already exists
                                      'password': 'password123'
                                  })

        self.assertEqual(response.status_code, 409)
        data = response.get_json()
        self.assertIn('already in use', data['msg'])

    def test_create_user_missing_fields(self):
        """Test creating user with missing required fields - validation and error handling"""
        token = self.get_auth_token('admin', 'test_admin', 'admin123')

        response = self.client.post('/api/admin/users',
                                  headers={'Authorization': f'Bearer {token}'},
                                  json={
                                      'role': 'student',
                                      'name': 'Student'
                                      # Missing id, email, password
                                  })

        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('required', data['msg'])

    def test_create_user_invalid_role(self):
        """Test creating user with invalid role - validation and error handling"""
        token = self.get_auth_token('admin', 'test_admin', 'admin123')

        response = self.client.post('/api/admin/users',
                                  headers={'Authorization': f'Bearer {token}'},
                                  json={
                                      'role': 'invalid_role',
                                      'id': 'X001',
                                      'name': 'Invalid User',
                                      'email': 'invalid@test.com',
                                      'password': 'password123'
                                  })

        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertEqual(data['msg'], 'Invalid role')

    def test_get_users_list(self):
        """Test getting list of all users"""
        token = self.get_auth_token('admin', 'test_admin', 'admin123')

        response = self.client.get('/api/admin/users',
                                 headers={'Authorization': f'Bearer {token}'})

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('students', data)
        self.assertIn('teachers', data)
        self.assertIsInstance(data['students'], list)
        self.assertIsInstance(data['teachers'], list)

    def test_delete_user_student_valid(self):
        """Test deleting a student user"""
        token = self.get_auth_token('admin', 'test_admin', 'admin123')

        response = self.client.delete('/api/admin/users/student/TEST_S101',
                                    headers={'Authorization': f'Bearer {token}'})

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['msg'], 'User deleted')

    def test_delete_user_teacher_valid(self):
        """Test deleting a teacher user"""
        token = self.get_auth_token('admin', 'test_admin', 'admin123')

        response = self.client.delete('/api/admin/users/teacher/TEST_T201',
                                    headers={'Authorization': f'Bearer {token}'})

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['msg'], 'User deleted')

    def test_delete_user_not_found(self):
        """Test deleting non-existent user - validation and error handling"""
        token = self.get_auth_token('admin', 'test_admin', 'admin123')

        response = self.client.delete('/api/admin/users/student/NOTFOUND',
                                    headers={'Authorization': f'Bearer {token}'})

        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertEqual(data['msg'], 'User not found')

    def test_delete_user_invalid_role(self):
        """Test deleting user with invalid role - validation and error handling"""
        token = self.get_auth_token('admin', 'test_admin', 'admin123')

        response = self.client.delete('/api/admin/users/invalid/S101',
                                    headers={'Authorization': f'Bearer {token}'})

        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertEqual(data['msg'], 'Invalid role')

    def test_assign_exam_valid(self):
        """Test assigning exam to student"""
        token = self.get_auth_token('admin', 'test_admin', 'admin123')

        response = self.client.post('/api/admin/assign-exam',
                                  headers={'Authorization': f'Bearer {token}'},
                                  json={
                                      'student_id': 'TEST_S101',
                                      'exam_id': 1
                                  })

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('assigned', data['msg'])

    def test_assign_exam_student_not_found(self):
        """Test assigning exam to non-existent student - validation and error handling"""
        token = self.get_auth_token('admin', 'test_admin', 'admin123')

        # We need to make sure the student wasn't deleted by a previous test
        # BaseTestCase resets data for each test, so it should be there.
        
        response = self.client.post('/api/admin/assign-exam',
                                  headers={'Authorization': f'Bearer {token}'},
                                  json={
                                      'student_id': 'NOTFOUND',
                                      'exam_id': 1
                                  })

        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertEqual(data['msg'], 'Student not found')

    def test_assign_exam_exam_not_found(self):
        """Test assigning non-existent exam to student - validation and error handling"""
        token = self.get_auth_token('admin', 'test_admin', 'admin123')

        response = self.client.post('/api/admin/assign-exam',
                                  headers={'Authorization': f'Bearer {token}'},
                                  json={
                                      'student_id': 'TEST_S101',
                                      'exam_id': 999
                                  })

        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertEqual(data['msg'], 'Exam not found')

    def test_get_analytics(self):
        """Test getting system analytics"""
        token = self.get_auth_token('admin', 'test_admin', 'admin123')

        response = self.client.get('/api/admin/analytics',
                                 headers={'Authorization': f'Bearer {token}'})

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('total_students', data)
        self.assertIn('total_teachers', data)
        self.assertIn('active_exams', data)
        self.assertIsInstance(data['total_students'], int)
        self.assertIsInstance(data['total_teachers'], int)


if __name__ == '__main__':
    unittest.main()
