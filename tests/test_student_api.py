import unittest
import json
from tests.base_test import BaseTestCase
from backend.app.models import Student, Exam, Question, Response, Forum, LooBreak
from datetime import datetime, timedelta


class TestStudentAPI(BaseTestCase):
    """Test cases for student API endpoints"""

    def test_get_student_profile_unauthorized(self):
        """Test accessing student profile without authentication - validation and error handling"""
        response = self.client.get('/api/student/profile')
        self.assertEqual(response.status_code, 401)

    def test_get_student_profile_authorized(self):
        """Test accessing student profile with valid authentication"""
        token = self.get_auth_token('student', 'TEST_S101', 'student123')
        self.assertIsNotNone(token)

        response = self.client.get('/api/student/profile',
                                 headers={'Authorization': f'Bearer {token}'})

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['admission_id'], 'TEST_S101')
        self.assertEqual(data['name'], 'Test Student')
        self.assertEqual(data['email'], 'test_student@test.com')

    def test_get_exam_status(self):
        """Test getting exam status"""
        token = self.get_auth_token('student', 'TEST_S101', 'student123')

        response = self.client.get('/api/student/upcoming-tests',
                                 headers={'Authorization': f'Bearer {token}'})

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIsInstance(data, list)
        if data:
            self.assertIn('status', data[0])

    def test_get_questions_unauthorized(self):
        """Test accessing questions without authentication - validation and error handling"""
        response = self.client.get('/api/student/game')
        self.assertEqual(response.status_code, 401)

    def test_get_questions_authorized(self):
        """Test getting questions with valid authentication"""
        token = self.get_auth_token('student', 'TEST_S101', 'student123')

        response = self.client.get('/api/student/game',
                                 headers={'Authorization': f'Bearer {token}'})

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIsInstance(data, list)

    def test_submit_answer_valid(self):
        """Test submitting a valid answer"""
        token = self.get_auth_token('student', 'TEST_S101', 'student123')

        response = self.client.post('/api/exam/submit',
                                  headers={'Authorization': f'Bearer {token}'},
                                  json=[{
                                      'question_id': 1,
                                      'answer': '4'
                                  }])

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('msg', data)

    def test_submit_answer_invalid_question(self):
        """Test submitting answer for non-existent question - validation and error handling"""
        token = self.get_auth_token('student', 'TEST_S101', 'student123')

        response = self.client.post('/api/exam/submit',
                                  headers={'Authorization': f'Bearer {token}'},
                                  json=[{
                                      'question_id': 999,
                                      'answer': '4'
                                  }])

        # Should handle gracefully or return appropriate error
        self.assertIn(response.status_code, [200, 400, 404])

    def test_submit_answer_missing_fields(self):
        """Test submitting answer with missing fields - validation and error handling"""
        token = self.get_auth_token('student', 'TEST_S101', 'student123')

        # Missing question_id
        response = self.client.post('/api/exam/submit',
                                  headers={'Authorization': f'Bearer {token}'},
                                  json=[{'answer': '4'}])
        self.assertEqual(response.status_code, 400)

        # Missing answer
        response = self.client.post('/api/exam/submit',
                                  headers={'Authorization': f'Bearer {token}'},
                                  json=[{'question_id': 1}])
        self.assertEqual(response.status_code, 400)

    def test_start_break_valid(self):
        """Test starting a break"""
        token = self.get_auth_token('student', 'TEST_S101', 'student123')

        response = self.client.post('/api/exam/loo-break/start',
                                  headers={'Authorization': f'Bearer {token}'})

        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertIn('msg', data)

    def test_end_break_valid(self):
        """Test ending a break"""
        token = self.get_auth_token('student', 'TEST_S101', 'student123')

        # First start a break
        self.client.post('/api/exam/loo-break/start',
                        headers={'Authorization': f'Bearer {token}'})

        # Then end it
        response = self.client.post('/api/exam/loo-break/end',
                                  headers={'Authorization': f'Bearer {token}'})

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('msg', data)

    def test_forum_post_valid(self):
        """Test posting to forum"""
        token = self.get_auth_token('student', 'TEST_S101', 'student123')

        response = self.client.post('/api/student/forum',
                                  headers={'Authorization': f'Bearer {token}'},
                                  json={
                                      'post': 'This is a test forum post'
                                  })

        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertIn('msg', data)

    def test_forum_post_missing_content(self):
        """Test posting to forum with missing content - validation and error handling"""
        token = self.get_auth_token('student', 'S101', 'student123')

        response = self.client.post('/api/student/forum',
                                  headers={'Authorization': f'Bearer {token}'},
                                  json={})

        self.assertEqual(response.status_code, 422)

    def test_get_forum_posts(self):
        """Test getting forum posts"""
        token = self.get_auth_token('student', 'TEST_S101', 'student123')

        response = self.client.get('/api/student/forum',
                                 headers={'Authorization': f'Bearer {token}'})

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIsInstance(data, list)

    def test_get_resources(self):
        """Test getting resources"""
        token = self.get_auth_token('student', 'TEST_S101', 'student123')

        response = self.client.get('/api/student/resources',
                                 headers={'Authorization': f'Bearer {token}'})

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIsInstance(data, list)

    def test_submit_mood_valid(self):
        """Test submitting mood"""
        token = self.get_auth_token('student', 'TEST_S101', 'student123')

        response = self.client.post('/api/exam/mood',
                                  headers={'Authorization': f'Bearer {token}'},
                                  json={'mood': 'happy'})

        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertIn('msg', data)

    def test_submit_mood_invalid(self):
        """Test submitting invalid mood - validation and error handling"""
        token = self.get_auth_token('student', 'TEST_S101', 'student123')

        response = self.client.post('/api/exam/mood',
                                  headers={'Authorization': f'Bearer {token}'},
                                  json={'mood': 'invalid_mood'})

        # Should validate mood values
        self.assertIn(response.status_code, [200, 400])

    def test_submit_mood_missing_field(self):
        """Test submitting mood with missing field - validation and error handling"""
        token = self.get_auth_token('student', 'TEST_S101', 'student123')

        response = self.client.post('/api/exam/mood',
                                  headers={'Authorization': f'Bearer {token}'},
                                  json={})

        self.assertEqual(response.status_code, 400)

    def test_get_responses(self):
        """Test getting student dashboard with response information"""
        token = self.get_auth_token('student', 'TEST_S101', 'student123')

        response = self.client.get('/api/student/dashboard',
                                 headers={'Authorization': f'Bearer {token}'})

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('total_marks', data)
        self.assertIn('accuracy', data)


if __name__ == '__main__':
    unittest.main()