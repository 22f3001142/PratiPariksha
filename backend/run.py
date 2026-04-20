from app import create_app
from app.models import db, Admin, Exam, Student, Teacher
from werkzeug.security import generate_password_hash
from sqlalchemy.exc import IntegrityError
import os

app = create_app()

# initialize database and default records on startup
with app.app_context():
    print("Creating database tables...")
    db.create_all()
    print(f"Database file should be at: {app.config['SQLALCHEMY_DATABASE_URI']}")

    # default admin
    if not Admin.query.filter_by(username='admin').first():
        admin = Admin(
            username='admin',
            password=generate_password_hash('admin123', method='pbkdf2:sha256')
        )
        db.session.add(admin)
        try:
            db.session.commit()
            print("Admin user created.")
        except IntegrityError:
            db.session.rollback()

    if not Exam.query.first():
        exam = Exam(status='stopped')
        db.session.add(exam)
        try:
            db.session.commit()
            print("Default exam entry created.")
        except IntegrityError:
            db.session.rollback()

if __name__ == '__main__':
    port = int(os.getenv('PORT', '8391'))
    app.run(debug=True, port=port)
