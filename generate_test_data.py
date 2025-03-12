from app import app, db, User, PracticeRecord, generate_password_hash
from datetime import datetime, date, timedelta
import random
import json

def generate_test_data():
    # Create director account
    director = User(
        username="director",
        email="director@school.edu",
        password_hash=generate_password_hash("director123"),
        role="director"
    )
    db.session.add(director)
    
    # Instruments in score order
    instruments = [
        'Flute', 'Oboe', 'Clarinet', 'Bassoon', 'Saxophone',
        'Trumpet', 'Horn', 'Trombone', 'Euphonium', 'Tuba'
    ]
    
    practice_ranges = [
        (100, 120),  # High achievers
        (80, 99),    # Above average
        (50, 79),    # Average
        (20, 49),    # Below average
        (0, 19)      # Minimal practice
    ]
    
    # Calculate week dates
    today = datetime.now().date()
    days_since_friday = (today.weekday() - 4) % 7
    week_start = today - timedelta(days=days_since_friday)
    
    # Create test students
    for i in range(35):
        # Create student
        username = f"student{i+1}"
        student = User(
            username=username,
            email=f"{username}@school.edu",
            password_hash="pbkdf2:sha256:260000$rqKqh3HUKcYKm1c1$d9e3a6e3fff11c4bbdbbfb77c9198d48e0f847a9c6fe6bfa3d4c16d3951c621f",  # student123
            role="student",
            instrument=random.choice(instruments),
            parent_email=f"parent{i+1}@email.com"
        )
        db.session.add(student)
        db.session.flush()  # Get student ID
        
        # Generate practice data
        practice_range = random.choice(practice_ranges)
        days_practiced = random.randint(3, 7)  # Between 3 and 7 days
        practice_days = random.sample(['friday', 'saturday', 'sunday', 'monday', 'tuesday', 'wednesday', 'thursday'], days_practiced)
        
        # Create minutes dictionary
        minutes = {}
        for day in ['friday', 'saturday', 'sunday', 'monday', 'tuesday', 'wednesday', 'thursday']:
            if day in practice_days:
                minutes[day] = random.randint(practice_range[0], practice_range[1])
            else:
                minutes[day] = 0
        
        # Create comments dictionary
        comments = {}
        for day, mins in minutes.items():
            if mins > 0:
                comments[day] = f"Practiced {random.choice(['scales', 'etudes', 'band music', 'sight reading'])} for {mins} minutes"
        
        # Create practice record
        record = PracticeRecord(
            student_id=student.id,
            week_start=week_start,
            minutes=json.dumps(minutes),
            daily_comments=json.dumps(comments),
            comments=f"Weekly practice report for {username}",
            is_submitted=True,
            submitted_at=datetime.now(),
            parent_signature_status='approved' if i < 30 else 'pending',
            signature_requested=True,
            signature_timestamp=datetime.now() if i < 30 else None
        )
        db.session.add(record)
    
    # Commit all changes
    db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        # Drop all tables and recreate them
        db.drop_all()
        db.create_all()
        
        # Generate new test data
        generate_test_data()
        print("Test data generated successfully!")
