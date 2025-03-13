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
    
    # Instruments in score order with weights for more realistic distribution
    instruments = {
        'Flute': 8,      # More common
        'Clarinet': 8,   # More common
        'Saxophone': 6,  # Common
        'Trumpet': 6,    # Common
        'Trombone': 4,   # Less common
        'Horn': 3,       # Less common
        'Oboe': 2,       # Rare
        'Bassoon': 2,    # Rare
        'Euphonium': 3,  # Less common
        'Tuba': 2,       # Rare
        'Percussion': 5  # Moderately common
    }
    
    # Realistic first names
    first_names = [
        'Emma', 'Liam', 'Olivia', 'Noah', 'Ava', 'James', 'Sophia', 'William',
        'Isabella', 'Mason', 'Mia', 'Ethan', 'Charlotte', 'Alexander', 'Amelia',
        'Henry', 'Harper', 'Sebastian', 'Evelyn', 'Jack', 'Abigail', 'Owen',
        'Emily', 'Daniel', 'Elizabeth', 'Jackson', 'Sofia', 'Samuel', 'Madison',
        'David', 'Avery', 'Joseph', 'Ella', 'Carter', 'Scarlett', 'Julian',
        'Victoria', 'Luke', 'Riley', 'Grayson'
    ]
    
    # Realistic last names
    last_names = [
        'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller',
        'Davis', 'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez',
        'Wilson', 'Anderson', 'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin',
        'Lee', 'Perez', 'Thompson', 'White', 'Harris', 'Sanchez', 'Clark',
        'Ramirez', 'Lewis', 'Robinson', 'Walker', 'Young', 'Allen', 'King',
        'Wright', 'Scott', 'Torres', 'Nguyen', 'Hill', 'Flores'
    ]
    
    # Practice ranges with weights
    practice_ranges = [
        (100, 120, 3),  # High achievers (15%)
        (80, 99, 7),    # Above average (35%)
        (50, 79, 6),    # Average (30%)
        (20, 49, 3),    # Below average (15%)
        (0, 19, 1)      # Minimal practice (5%)
    ]
    
    # Create test students
    students = []
    used_names = set()  # Track used name combinations
    
    # Create Emily Davis as the first student
    emily = User(
        username="edavis",
        email="edavis@school.edu",
        password_hash=generate_password_hash("student123"),
        role="student",
        instrument="Flute",
        parent_email="parent.edavis@email.com",
        first_name="Emily",
        last_name="Davis"
    )
    db.session.add(emily)
    db.session.flush()  # Get student ID
    students.append(emily)
    used_names.add(("Emily", "Davis"))
    
    while len(students) < 40:
        # Generate random name
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        
        # Skip if this name combination is already used
        name_key = (first_name, last_name)
        if name_key in used_names:
            continue
        
        used_names.add(name_key)
        
        # Create username from first initial and last name, plus a number if needed
        base_username = f"{first_name[0].lower()}{last_name.lower()}"
        username = base_username
        counter = 1
        while any(s.username == username for s in students):
            username = f"{base_username}{counter}"
            counter += 1
        
        # Select instrument based on weights
        instrument = random.choices(list(instruments.keys()), 
                                  weights=list(instruments.values()))[0]
        
        # Create student
        student = User(
            username=username,
            email=f"{username}@school.edu",
            password_hash=generate_password_hash("student123"),
            role="student",
            instrument=instrument,
            parent_email=f"parent.{username}@email.com",
            first_name=first_name,
            last_name=last_name
        )
        db.session.add(student)
        db.session.flush()  # Get student ID
        students.append(student)
    
    # Generate practice data from January 2025 to current date
    start_date = date(2025, 1, 3)  # First Friday of January 2025
    today = datetime.now().date()
    
    current_date = start_date
    while current_date <= today:
        # Skip if not a Friday (week start)
        if current_date.weekday() != 4:  # 4 is Friday
            current_date += timedelta(days=1)
            continue
            
        # Generate practice data for each student for this week
        for student in students:
            # Generate practice data
            practice_range = random.choices(practice_ranges, 
                                          weights=[r[2] for r in practice_ranges])[0]
            days_practiced = random.randint(3, 7)  # Between 3 and 7 days
            practice_days = random.sample(['friday', 'saturday', 'sunday', 'monday', 'tuesday', 'wednesday', 'thursday'], days_practiced)
            
            # Create minutes dictionary with some variation
            minutes = {}
            for day in ['friday', 'saturday', 'sunday', 'monday', 'tuesday', 'wednesday', 'thursday']:
                if day in practice_days:
                    # Add some random variation to practice times
                    base_minutes = random.randint(practice_range[0], practice_range[1])
                    variation = random.randint(-10, 10)
                    minutes[day] = max(0, base_minutes + variation)
                else:
                    minutes[day] = 0
            
            # Create comments dictionary with more varied comments
            comments = {}
            practice_activities = [
                'scales', 'etudes', 'band music', 'sight reading', 'solos',
                'duets', 'ensemble pieces', 'technical exercises', 'tone exercises',
                'rhythm practice'
            ]
            for day, mins in minutes.items():
                if mins > 0:
                    activities = random.sample(practice_activities, random.randint(1, 3))
                    comments[day] = f"Practiced {', '.join(activities)} for {mins} minutes"
            
            # Create practice record with varied submission status
            record = PracticeRecord(
                student_id=student.id,
                week_start=current_date,
                minutes=json.dumps(minutes),
                daily_comments=json.dumps(comments),
                comments=f"Weekly practice report for {student.first_name} {student.last_name}",
                is_submitted=True,
                submitted_at=current_date + timedelta(days=6),  # Submit on Thursday
                parent_signature_status='approved' if random.random() < 0.8 else 'pending',  # 80% approved
                signature_requested=True,
                signature_timestamp=current_date + timedelta(days=6) if random.random() < 0.8 else None
            )
            db.session.add(record)
        
        current_date += timedelta(days=1)
    
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
