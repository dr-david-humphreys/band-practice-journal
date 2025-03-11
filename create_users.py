from app import app, db, User
from werkzeug.security import generate_password_hash

def create_test_users():
    with app.app_context():
        # Create band director
        director = User(
            username='director',
            password_hash=generate_password_hash('director123'),
            role='director'
        )
        db.session.add(director)
        
        # Create parent
        parent = User(
            username='parent',
            password_hash=generate_password_hash('parent123'),
            role='parent'
        )
        db.session.add(parent)
        
        # Create student
        student = User(
            username='student',
            password_hash=generate_password_hash('student123'),
            role='student',
            parent_id=2  # This will be the ID of the parent user
        )
        db.session.add(student)
        
        try:
            db.session.commit()
            print("Test users created successfully!")
            print("\nLogin credentials:")
            print("Director - Username: director, Password: director123")
            print("Parent - Username: parent, Password: parent123")
            print("Student - Username: student, Password: student123")
        except Exception as e:
            print("Error creating users:", e)
            db.session.rollback()

if __name__ == '__main__':
    create_test_users()
