from backend.app import create_app, db
from backend.app.models import Admin, Exam, Student, Teacher, Question, Resource, TestPaper, TestPaperQuestion
from werkzeug.security import generate_password_hash
import os

app = create_app()

with app.app_context():
    db.create_all()

    demo_non_math_questions = [
        'Which statement best describes photosynthesis?',
        'A body continues moving with uniform velocity unless acted on by an external force. This is:',
        'The acceleration due to gravity on Earth is approximately:'
    ]
    for prompt in demo_non_math_questions:
        Question.query.filter_by(question=prompt).delete()
    Resource.query.filter(Resource.title.in_([
        'Newton Laws Summary Notes',
        'Photosynthesis Quick Guide'
    ])).delete(synchronize_session=False)
    
    # Create default Admin if not exists
    if not Admin.query.filter_by(username='admin').first():
        admin = Admin(
            username='admin',
            password=generate_password_hash('admin123', method='pbkdf2:sha256')
        )
        db.session.add(admin)
        print("Admin user created.")

    # Create default Exam entry if not exists
    if not Exam.query.first():
        exam = Exam(status='stopped')
        db.session.add(exam)
        print("Default exam entry created.")

    # Create a test student if not exists
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

    # Create a test teacher if not exists
    if not Teacher.query.filter_by(employee_id='T201').first():
        teacher = Teacher(
            employee_id='T201',
            name='Test Teacher',
            email='teacher@test.com',
            password=generate_password_hash('password123', method='pbkdf2:sha256'),
            subject='Mathematics'
        )
        db.session.add(teacher)
    else:
        teacher = Teacher.query.filter_by(employee_id='T201').first()
        if teacher and not teacher.subject:
            teacher.subject = 'Mathematics'

    starter_questions = [
        {
            'question': 'Solve for x: 3x - 7 = 14',
            'type': 'MCQ',
            'options': ['x = 5', 'x = 7', 'x = 9', 'x = 21'],
            'correct_answer': 'x = 7',
            'difficulty_level': 1,
            'topic': 'Mathematics',
            'subtopic': 'Linear Equations',
            'explanation': 'Add 7 on both sides and then divide the result by 3.'
        },
        {
            'question': 'What is the square root of 144?',
            'type': 'NAT',
            'options': None,
            'correct_answer': '12',
            'difficulty_level': 1,
            'topic': 'Mathematics',
            'subtopic': 'Number Systems',
            'explanation': '12 multiplied by 12 equals 144.'
        },
        {
            'question': 'Factorise: x^2 + 5x + 6',
            'type': 'MCQ',
            'options': ['(x + 1)(x + 6)', '(x + 2)(x + 3)', '(x - 2)(x - 3)', '(x + 4)(x + 2)'],
            'correct_answer': '(x + 2)(x + 3)',
            'difficulty_level': 2,
            'topic': 'Mathematics',
            'subtopic': 'Quadratic Expressions',
            'explanation': 'Find two numbers whose product is 6 and sum is 5.'
        },
        {
            'question': 'Select the prime number.',
            'type': 'MCQ',
            'options': ['15', '21', '27', '31'],
            'correct_answer': '31',
            'difficulty_level': 1,
            'topic': 'Mathematics',
            'subtopic': 'Number Systems',
            'explanation': '31 has exactly two factors: 1 and itself.'
        },
        {
            'question': 'If 2x + 3 = 11, then x = ?',
            'type': 'MCQ',
            'options': ['2', '3', '4', '5'],
            'correct_answer': '4',
            'difficulty_level': 1,
            'topic': 'Mathematics',
            'subtopic': 'Linear Equations',
            'explanation': 'Subtract 3 from both sides and divide by 2.'
        },
        {
            'question': 'Evaluate: 3/4 + 1/2',
            'type': 'NAT',
            'options': None,
            'correct_answer': '1.25',
            'difficulty_level': 2,
            'topic': 'Mathematics',
            'subtopic': 'Fractions',
            'explanation': 'Convert to a common denominator or decimals, then add.'
        }
    ]
    for starter_question in starter_questions:
        if not Question.query.filter_by(question=starter_question['question']).first():
            db.session.add(Question(**starter_question))

    starter_resources = [
        {
            'title': 'Linear Equations Revision Sheet',
            'file_url': 'https://example.com/resources/linear-equations',
            'topic': 'Mathematics',
            'uploaded_by': 'T201'
        },
        {
            'title': 'Quadratic Expressions Drill Pack',
            'file_url': 'https://example.com/resources/quadratic-expressions',
            'topic': 'Mathematics',
            'uploaded_by': 'T201'
        }
    ]
    for starter_resource in starter_resources:
        if not Resource.query.filter_by(title=starter_resource['title']).first():
            db.session.add(Resource(**starter_resource))

    if Question.query.count() == 0:
        for starter_question in starter_questions:
            db.session.add(Question(**starter_question))

    if Resource.query.count() == 0:
        for starter_resource in starter_resources:
            db.session.add(Resource(**starter_resource))

    student = Student.query.filter_by(admission_id='S101').first()
    if student and not student.assigned_teacher_id:
        student.assigned_teacher_id = 'T201'
        
    db.session.commit()

    if TestPaper.query.count() == 0:
        test = TestPaper(
            title='Foundation Diagnostic Test',
            topic='Mathematics',
            description='Starter mathematics diagnostic for new learners.',
            created_by='T201'
        )
        db.session.add(test)
        db.session.flush()
        for index, question in enumerate(Question.query.filter_by(topic='Mathematics').order_by(Question.id.asc()).limit(5).all()):
            db.session.add(TestPaperQuestion(test_id=test.id, question_id=question.id, sort_order=index))
        if exam := Exam.query.first():
            exam.test_id = test.id
        db.session.commit()
    else:
        starter_test = TestPaper.query.order_by(TestPaper.id.asc()).first()
        if starter_test:
            starter_test.topic = 'Mathematics'
            starter_test.description = 'Starter mathematics diagnostic for new learners.'
            TestPaperQuestion.query.filter_by(test_id=starter_test.id).delete()
            for index, question in enumerate(Question.query.filter_by(topic='Mathematics').order_by(Question.id.asc()).limit(5).all()):
                db.session.add(TestPaperQuestion(test_id=starter_test.id, question_id=question.id, sort_order=index))
            db.session.commit()

    print("Database initialized.")
