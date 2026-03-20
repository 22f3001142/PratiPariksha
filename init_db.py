from backend.app import create_app, db
from backend.app.models import Admin, Exam, Student, Teacher
from werkzeug.security import generate_password_hash
import os

app = create_app()

with app.app_context():
    db.create_all()
    
    # Create default Admin if not exists
    if not Admin.query.filter_by(username='admin').first():
        admin = Admin(
            username='admin',
            password=generate_password_hash('admin123')
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
            password=generate_password_hash('password123'),
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
            password=generate_password_hash('password123')
        )
        db.session.add(teacher)
        
    db.session.commit()
    print("Database initialized.")
