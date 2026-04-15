from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Admin(db.Model):
    __tablename__ = 'admin'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

class Student(db.Model):
    __tablename__ = 'students'
    admission_id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    points = db.Column(db.Integer, default=0)
    level = db.Column(db.Integer, default=1)
    badges = db.Column(db.Text, default='') # Comma separated list of badges
    current_avatar = db.Column(db.String(100), default='🤖') # Default emoji avatar
    inventory = db.Column(db.Text, default='🤖') # Comma separated list of owned avatars
    assigned_teacher_id = db.Column(db.String(50), db.ForeignKey('teachers.employee_id'), nullable=True)

class Teacher(db.Model):
    __tablename__ = 'teachers'
    employee_id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(100), default='Mathematics')

class Question(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(10), nullable=False) # MCQ, MSQ, NAT
    options = db.Column(db.JSON, nullable=True) # JSON for MCQ/MSQ
    correct_answer = db.Column(db.Text, nullable=False)
    difficulty_level = db.Column(db.Integer, default=1)
    topic = db.Column(db.String(100), default='General')
    subtopic = db.Column(db.String(100), default='General')
    explanation = db.Column(db.Text, default='')

class Exam(db.Model):
    __tablename__ = 'exams'
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime, nullable=True)
    end_time = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='stopped') # started, stopped
    test_id = db.Column(db.Integer, db.ForeignKey('test_papers.id'), nullable=True)

class Response(db.Model):
    __tablename__ = 'responses'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(50), db.ForeignKey('students.admission_id'))
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'))
    answer = db.Column(db.Text, nullable=False)

class LooBreak(db.Model):
    __tablename__ = 'loo_break'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(50), db.ForeignKey('students.admission_id'))
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)

class Forum(db.Model):
    __tablename__ = 'forum'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(50), db.ForeignKey('students.admission_id'))
    post = db.Column(db.Text, nullable=False)
    reply = db.Column(db.Text, nullable=True)
    poll = db.Column(db.String(255), nullable=True)
    vote = db.Column(db.Integer, default=0)

class Resource(db.Model):
    __tablename__ = 'resources'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    file_url = db.Column(db.String(255), nullable=False)
    uploaded_by = db.Column(db.String(50), db.ForeignKey('teachers.employee_id'))
    topic = db.Column(db.String(100), default='General')

class TestPaper(db.Model):
    __tablename__ = 'test_papers'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    topic = db.Column(db.String(100), default='General')
    description = db.Column(db.Text, default='')
    created_by = db.Column(db.String(50), db.ForeignKey('teachers.employee_id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    questions = db.relationship(
        'TestPaperQuestion',
        backref='test_paper',
        cascade='all, delete-orphan',
        lazy=True
    )

class TestPaperQuestion(db.Model):
    __tablename__ = 'test_paper_questions'
    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey('test_papers.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    sort_order = db.Column(db.Integer, default=0)

class Mood(db.Model):
    __tablename__ = 'moods'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(50), db.ForeignKey('students.admission_id'))
    mood = db.Column(db.String(20), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
