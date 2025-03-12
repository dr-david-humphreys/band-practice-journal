from datetime import datetime, date, timedelta
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
import secrets
import os
import string

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'  # Change this in production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///practice.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Email configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Update with your SMTP server
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')  # Set this in environment variables
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')  # Set this in environment variables
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME')

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
mail = Mail(app)

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'student', 'director'
    instrument = db.Column(db.String(50), nullable=True)
    parent_email = db.Column(db.String(120), nullable=True)
    streak_count = db.Column(db.Integer, default=0)
    last_practice = db.Column(db.Date, nullable=True)
    practice_records = db.relationship('PracticeRecord', backref='student', lazy=True)

class PracticeRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    week_start = db.Column(db.Date, nullable=False)
    minutes = db.Column(db.String(200), nullable=False)  # Stored as JSON string
    comments = db.Column(db.Text, nullable=True)
    daily_comments = db.Column(db.Text, nullable=True)
    parent_signature_status = db.Column(db.String(20), default='pending')  # 'pending', 'approved', 'denied'
    signature_token = db.Column(db.String(100), nullable=True)  # Token for email verification
    signature_requested = db.Column(db.Boolean, default=False)
    signature_timestamp = db.Column(db.DateTime, nullable=True)
    is_submitted = db.Column(db.Boolean, default=False)  # Track if week is submitted
    submitted_at = db.Column(db.DateTime, nullable=True)  # When the week was submitted
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def generate_temp_password():
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for i in range(12))

def send_signature_request(practice_record, student):
    # Generate a unique token for this signature request
    token = secrets.token_urlsafe(32)
    practice_record.signature_token = token
    practice_record.signature_requested = True
    db.session.commit()

    # Create approve and deny URLs
    approve_url = url_for('verify_signature', token=token, action='approve', _external=True)
    deny_url = url_for('verify_signature', token=token, action='deny', _external=True)

    # Calculate total minutes and practice days
    minutes_dict = json.loads(practice_record.minutes)
    total_minutes = sum(int(v) for v in minutes_dict.values())
    practice_days = sum(1 for v in minutes_dict.values() if int(v) > 0)

    # Send email to parent
    msg = Message(
        'Band Practice Verification Request',
        recipients=[student.parent_email]
    )
    msg.html = render_template(
        'email/signature_request.html',
        student_name=student.username,
        total_minutes=total_minutes,
        practice_days=practice_days,
        week_start=practice_record.week_start.strftime('%B %d, %Y'),
        approve_url=approve_url,
        deny_url=deny_url
    )
    mail.send(msg)

# Add template filters
@app.template_filter('from_json')
def from_json_filter(value):
    if not value:
        return {}
    try:
        return json.loads(value) if isinstance(value, str) else value
    except json.JSONDecodeError:
        return {}

@app.template_filter('sum_minutes')
def sum_minutes_filter(minutes_dict):
    try:
        if isinstance(minutes_dict, str):
            minutes_dict = json.loads(minutes_dict)
        return sum(int(mins) for mins in minutes_dict.values())
    except (json.JSONDecodeError, AttributeError):
        return 0

@app.template_filter('count_practice_days')
def count_practice_days_filter(minutes_dict):
    try:
        if isinstance(minutes_dict, str):
            minutes_dict = json.loads(minutes_dict)
        return sum(1 for mins in minutes_dict.values() if int(mins) > 0)
    except (json.JSONDecodeError, AttributeError):
        return 0

@app.template_filter('get_day_minutes')
def get_day_minutes(minutes_dict, day, default=0):
    try:
        if isinstance(minutes_dict, str):
            minutes_dict = json.loads(minutes_dict)
        return int(minutes_dict.get(day, default))
    except (json.JSONDecodeError, AttributeError, ValueError):
        return default

@app.template_filter('get_day_comment')
def get_day_comment(comments_dict, day, default=''):
    try:
        if isinstance(comments_dict, str):
            comments_dict = json.loads(comments_dict)
        return comments_dict.get(day, default)
    except (json.JSONDecodeError, AttributeError):
        return default

@app.template_filter('calculate_grade')
def calculate_grade_filter(record):
    if not record:
        return '-'
    points = calculate_points(record)
    if record.parent_signature_status == 'approved':
        return f"{points}/105 pts"
    else:
        return f'{points-20}/105 (+20 with parent signature)'

@app.template_filter('calculate_points')
def calculate_points_filter(record):
    return calculate_points(record)

def calculate_points(record):
    if not record:
        return 0
    
    try:
        minutes_dict = json.loads(record.minutes) if isinstance(record.minutes, str) else record.minutes
        total_minutes = sum(int(mins) for mins in minutes_dict.values())
        practice_days = sum(1 for mins in minutes_dict.values() if int(mins) > 0)
        
        # Calculate base points based on total minutes
        if total_minutes >= 100:
            base_points = 80
        elif total_minutes >= 90:
            base_points = 75
        elif total_minutes >= 80:
            base_points = 70
        elif total_minutes >= 70:
            base_points = 65
        elif total_minutes >= 60:
            base_points = 60
        elif total_minutes >= 50:
            base_points = 55
        elif total_minutes >= 40:
            base_points = 50
        elif total_minutes >= 30:
            base_points = 45
        elif total_minutes >= 20:
            base_points = 40
        else:
            base_points = 35
        
        # Add bonus points for 5+ practice days
        bonus_points = 5 if practice_days >= 5 else 0
        
        # Add points for parent signature
        signature_points = 20 if record.parent_signature_status == 'approved' else 0
        
        return base_points + bonus_points + signature_points
    except (json.JSONDecodeError, AttributeError, ValueError):
        return 0

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'student':
            return redirect(url_for('student_dashboard'))
        elif current_user.role == 'director':
            return redirect(url_for('director_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        instrument = request.form.get('instrument')
        parent_email = request.form.get('parent_email')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('register'))
            
        user = User(
            username=username,
            password_hash=generate_password_hash(password),
            role=role,
            instrument=instrument if role == 'student' else None,
            parent_email=parent_email if role == 'student' else None
        )
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/api/practice/daily', methods=['POST'])
@login_required
def save_daily_practice():
    if current_user.role != 'student':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    day = data.get('day')
    minutes = data.get('minutes', 0)
    comment = data.get('comment', '')
    
    # Get or create practice record for current week
    today = datetime.now().date()
    days_since_friday = (today.weekday() - 4) % 7  # Friday is weekday 4
    week_start = today - timedelta(days=days_since_friday)
    
    record = PracticeRecord.query.filter_by(
        student_id=current_user.id,
        week_start=week_start
    ).first()
    
    if not record:
        record = PracticeRecord(
            student_id=current_user.id,
            week_start=week_start,
            minutes=json.dumps({day: minutes}),
            daily_comments=json.dumps({day: comment}),
            parent_signature_status='pending',
            signature_requested=False,
            created_at=datetime.utcnow()
        )
        db.session.add(record)
    else:
        # Update existing record
        minutes_dict = json.loads(record.minutes) if record.minutes else {}
        comments_dict = json.loads(record.daily_comments) if record.daily_comments else {}
        
        minutes_dict[day] = minutes
        comments_dict[day] = comment
        
        record.minutes = json.dumps(minutes_dict)
        record.daily_comments = json.dumps(comments_dict)
        record.updated_at = datetime.utcnow()
    
    # Update streak if minutes > 0
    if int(minutes) > 0:
        if current_user.last_practice:
            days_diff = (today - current_user.last_practice).days
            if days_diff == 1:  # Consecutive days
                current_user.streak_count += 1
            elif days_diff > 1:  # Streak broken
                current_user.streak_count = 1
        else:
            current_user.streak_count = 1
        current_user.last_practice = today
    
    try:
        db.session.commit()
        return jsonify({
            'message': 'Daily practice saved',
            'streak': current_user.streak_count,
            'parent_email': current_user.parent_email
        })
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error saving daily practice: {str(e)}')
        return jsonify({'error': 'Failed to save practice'}), 500

@app.route('/api/practice/submit', methods=['POST'])
@login_required
def submit_weekly_practice():
    if current_user.role != 'student':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    weekly_comments = data.get('weeklyComments', '')
    
    # Get current week's record
    today = datetime.now().date()
    days_since_friday = (today.weekday() - 4) % 7  # Friday is weekday 4
    week_start = today - timedelta(days=days_since_friday)
    
    record = PracticeRecord.query.filter_by(
        student_id=current_user.id,
        week_start=week_start
    ).first()
    
    if not record:
        return jsonify({'error': 'No practice recorded this week'}), 400
    
    record.comments = weekly_comments
    record.is_submitted = True
    record.submitted_at = datetime.utcnow()
    
    try:
        db.session.commit()
        return jsonify({
            'message': 'Weekly practice submitted',
            'parent_email': current_user.parent_email
        })
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error submitting practice: {str(e)}')
        return jsonify({'error': 'Failed to submit practice'}), 500

@app.route('/api/practice/history')
@login_required
def get_practice_history():
    if current_user.role != 'student':
        return jsonify({'error': 'Unauthorized'}), 403

    records = PracticeRecord.query.filter_by(
        student_id=current_user.id
    ).order_by(PracticeRecord.week_start.desc()).all()

    return jsonify([{
        'id': record.id,
        'week_start': record.week_start.isoformat(),
        'minutes': record.minutes,
        'comments': record.comments,
        'daily_comments': record.daily_comments,
        'parent_signature_status': record.parent_signature_status,
        'signature_requested': record.signature_requested,
        'total_points': calculate_points(record)
    } for record in records])

@app.route('/api/weeks')
@login_required
def get_weeks():
    if current_user.role != 'director':
        return jsonify({'error': 'Unauthorized'}), 403

    weeks = db.session.query(PracticeRecord.week_start).distinct().order_by(
        PracticeRecord.week_start.desc()
    ).all()
    return jsonify([week[0].isoformat() for week in weeks])

@app.route('/api/records/<week_start>')
@login_required
def get_week_records(week_start):
    if current_user.role != 'director':
        return jsonify({'error': 'Unauthorized'}), 403

    week_date = datetime.strptime(week_start, '%Y-%m-%d').date()
    records = PracticeRecord.query.join(User).filter(
        PracticeRecord.week_start == week_date
    ).all()

    return jsonify([{
        'student_name': record.student.username,
        'instrument': record.student.instrument,
        'minutes': record.minutes,
        'comments': record.comments,
        'daily_comments': record.daily_comments,
        'parent_signature_status': record.parent_signature_status,
        'total_points': calculate_points(record)
    } for record in records])

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        return redirect(url_for('index'))
    
    # Get current week's practice record
    today = datetime.now().date()
    days_since_friday = (today.weekday() - 4) % 7  # Friday is weekday 4
    week_start = today - timedelta(days=days_since_friday)
    
    current_week_record = PracticeRecord.query.filter_by(
        student_id=current_user.id,
        week_start=week_start
    ).first()
    
    # Get practice history
    practice_records = PracticeRecord.query.filter_by(
        student_id=current_user.id
    ).order_by(PracticeRecord.week_start.desc()).all()
    
    return render_template('student_dashboard.html', 
                         today=today,
                         current_week_record=current_week_record,
                         practice_records=practice_records)

@app.route('/director/dashboard')
@login_required
def director_dashboard():
    if current_user.role != 'director':
        flash('Access denied. Director privileges required.', 'danger')
        return redirect(url_for('index'))
    
    # Define instruments in score order
    instruments = [
        'Flute', 'Oboe', 'Clarinet', 'Bassoon', 'Saxophone',
        'Trumpet', 'Horn', 'Trombone', 'Euphonium', 'Tuba'
    ]
    
    # Get all practice records
    records = PracticeRecord.query.all()
    return render_template('director_dashboard.html', records=records, instruments=instruments)

@app.route('/request_signature/<int:record_id>')
@login_required
def request_signature(record_id):
    practice_record = PracticeRecord.query.get_or_404(record_id)
    
    # Ensure the student owns this record
    if practice_record.student_id != current_user.id:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('student_dashboard'))
    
    # Check if parent email is set
    if not current_user.parent_email:
        flash('Please update your parent\'s email address first', 'warning')
        return redirect(url_for('student_dashboard'))
    
    try:
        send_signature_request(practice_record, current_user)
        flash('Signature request sent to your parent!', 'success')
    except Exception as e:
        flash('Error sending signature request. Please try again.', 'danger')
        app.logger.error(f'Error sending signature request: {str(e)}')
    
    return redirect(url_for('student_dashboard'))

@app.route('/verify_signature/<token>')
def verify_signature(token):
    practice_record = PracticeRecord.query.filter_by(signature_token=token).first_or_404()
    action = request.args.get('action')
    
    if action not in ['approve', 'deny']:
        flash('Invalid action', 'danger')
        return render_template('signature_error.html')
    
    if not practice_record.signature_requested:
        flash('This signature request is no longer valid', 'danger')
        return render_template('signature_error.html')
    
    practice_record.parent_signature_status = 'approved' if action == 'approve' else 'denied'
    practice_record.signature_timestamp = datetime.utcnow()
    practice_record.signature_requested = False
    db.session.commit()
    
    return render_template('signature_success.html', action=action)

@app.route('/update_parent_email', methods=['POST'])
@login_required
def update_parent_email():
    if current_user.role != 'student':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    parent_email = data.get('parent_email')
    
    if not parent_email:
        return jsonify({'error': 'Parent email is required'}), 400
    
    current_user.parent_email = parent_email
    db.session.commit()
    
    return jsonify({'message': 'Parent email updated successfully'})

if __name__ == '__main__':
    app.run(debug=True)
