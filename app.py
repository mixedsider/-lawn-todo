from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from datetime import datetime
import os
import click
from flask.cli import with_appcontext

# .env 파일 로드
load_dotenv()

# Flask 앱 생성 및 설정
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24))

# 데이터베이스 URI 설정
db_user = os.getenv('MYSQL_USER')
db_password = os.getenv('MYSQL_PASSWORD')
db_host = os.getenv('MYSQL_HOST', 'localhost')
db_name = os.getenv('MYSQL_DATABASE')
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+mysqlconnector://{db_user}:{db_password}@{db_host}/{db_name}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 확장 초기화
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = "로그인이 필요한 서비스입니다."
login_manager.login_message_category = "warning"

# --- 데이터베이스 모델 ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    todos = db.relationship('Todo', backref='author', lazy=True)

class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    important = db.Column(db.Boolean, default=False)
    due_date = db.Column(db.Date, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'completed': self.completed,
            'important': self.important,
            'due_date': self.due_date.strftime('%Y-%m-%d') if self.due_date else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'completed_at': self.completed_at.strftime('%Y-%m-%d %H:%M:%S') if self.completed_at else None
        }

# --- 사용자 로더 ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- CLI 명령어 ---
@click.command('init-db')
@with_appcontext
def init_db_command():
    """데이터베이스 테이블을 생성합니다."""
    db.create_all()
    click.echo('Initialized the database.')

app.cli.add_command(init_db_command)

# --- 라우트 ---
@app.route('/')
@login_required
def index():
    todos = Todo.query.filter_by(user_id=current_user.id).order_by(
        Todo.completed.asc(),
        Todo.important.desc(),
        Todo.due_date.is_(None),
        Todo.due_date.asc(),
        Todo.id.asc()
    ).all()
    return render_template('index.html', todos=todos, today=datetime.utcnow().date())

@app.route('/lawn')
@login_required
def lawn():
    from datetime import date, timedelta
    from collections import defaultdict

    today = date.today()
    end_date = today
    start_date = end_date - timedelta(days=365)

    # 사용자의 완료 기록 조회
    completed_todos = db.session.query(db.func.date(Todo.completed_at), db.func.count(Todo.id)).filter(
        Todo.user_id == current_user.id,
        Todo.completed_at.isnot(None),
        db.func.date(Todo.completed_at) >= start_date,
        db.func.date(Todo.completed_at) <= end_date
    ).group_by(db.func.date(Todo.completed_at)).all()

    completion_counts = {d: c for d, c in completed_todos}

    # 전체 날짜 그리드 생성
    # GitHub처럼 오늘이 마지막에 오도록 하고, 그리드의 시작은 일요일로 맞춤
    start_of_grid = start_date - timedelta(days=(start_date.weekday() + 1) % 7)
    
    weeks = []
    current_week = []
    current_month = -1
    
    day_cursor = start_of_grid
    while day_cursor <= end_date:
        # 월 표시 로직 개선
        month_label = ''
        if day_cursor.day == 1 or (len(weeks) == 0 and len(current_week) == 0):
             if day_cursor.month != current_month:
                month_label = day_cursor.strftime('%b')
                current_month = day_cursor.month

        count = completion_counts.get(day_cursor, 0)
        level = 4 if count >= 10 else 3 if count >= 5 else 2 if count >= 3 else 1 if count > 0 else 0
        
        current_week.append({
            "date": day_cursor,
            "count": count,
            "level": level,
            "month_label": month_label
        })

        if day_cursor.weekday() == 6: # 토요일 (Python: 0=월, 6=일 -> 수정필요. 0=월, 6=일)
            # Python weekday(): Monday is 0 and Sunday is 6.
            # GitHub는 일요일부터 시작하므로, 토요일(5)에 주를 마감하거나 일요일(6)에 마감해야 함.
            # GitHub 스타일은 일-토 이므로, 토요일(weekday==5)에 한 주를 마무리.
            # -> 아니, 7일씩 채우면 되므로 요일은 크게 중요하지 않음. 일요일(6)에 주를 마감.
            weeks.append(current_week)
            current_week = []
        
        day_cursor += timedelta(days=1)

    if current_week:
        weeks.append(current_week)

    return render_template('lawn.html', weeks=weeks, today=today)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('로그인 실패. 사용자 이름과 비밀번호를 확인하세요.', 'danger')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user_exists = User.query.filter_by(username=username).first()
        if user_exists:
            flash('이미 존재하는 사용자 이름입니다.', 'warning')
            return redirect(url_for('signup'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('회원가입 성공! 이제 로그인할 수 있습니다.', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/add', methods=['POST'])
@login_required
def add_todo():
    if not request.is_json:
        return jsonify({"error": "Invalid request"}), 400

    data = request.get_json()
    content = data.get('content')
    due_date_str = data.get('due_date')
    important = data.get('important', False)

    if not content:
        return jsonify({'error': '내용을 입력해주세요.'}), 400

    due_date = None
    if due_date_str:
        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            if due_date < datetime.utcnow().date():
                return jsonify({'error': '마감 날짜는 오늘 또는 그 이후여야 합니다.'}), 400
        except ValueError:
            return jsonify({'error': '날짜 형식이 올바르지 않습니다.'}), 400

    new_todo = Todo(
        content=content,
        user_id=current_user.id,
        due_date=due_date,
        important=important
    )
    db.session.add(new_todo)
    db.session.commit()
    return jsonify({'success': True, 'todo': new_todo.to_dict()}), 201

@app.route('/edit/<int:todo_id>', methods=['GET', 'POST'])
@login_required
def edit_todo(todo_id):
    todo = Todo.query.get_or_404(todo_id)
    if todo.author != current_user:
        flash('수정 권한이 없습니다.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        content = request.form.get('content')
        due_date_str = request.form.get('due_date')
        important = request.form.get('important') == 'on'

        if not content:
            flash('내용을 입력해주세요.', 'danger')
            return render_template('edit_todo.html', todo=todo)

        todo.content = content
        todo.important = important
        
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
                if due_date < datetime.utcnow().date():
                    flash('마감 날짜는 오늘 또는 그 이후여야 합니다.', 'danger')
                    return render_template('edit_todo.html', todo=todo)
                todo.due_date = due_date
            except ValueError:
                flash('날짜 형식이 올바르지 않습니다.', 'danger')
                return render_template('edit_todo.html', todo=todo)
        else:
            todo.due_date = None

        db.session.commit()
        flash('할 일이 성공적으로 수정되었습니다.', 'success')
        return redirect(url_for('index'))

    return render_template('edit_todo.html', todo=todo)

@app.route('/complete/<int:todo_id>', methods=['POST'])
@login_required
def complete_todo(todo_id):
    todo = Todo.query.get_or_404(todo_id)
    if todo.author != current_user:
        return jsonify({'success': False, 'error': '권한이 없습니다.'}), 403
    
    todo.completed = not todo.completed
    if todo.completed:
        todo.completed_at = datetime.utcnow()
    else:
        todo.completed_at = None
        
    db.session.commit()
    return jsonify({'success': True, 'completed': todo.completed})

@app.route('/delete/<int:todo_id>', methods=['POST'])
@login_required
def delete_todo(todo_id):
    todo = Todo.query.get_or_404(todo_id)
    if todo.author != current_user:
        return jsonify({'success': False, 'error': '권한이 없습니다.'}), 403
    db.session.delete(todo)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/important/<int:todo_id>', methods=['POST'])
@login_required
def important_todo(todo_id):
    todo = Todo.query.get_or_404(todo_id)
    if todo.author != current_user:
        return jsonify({'success': False, 'error': '권한이 없습니다.'}), 403
    todo.important = not todo.important
    db.session.commit()
    return jsonify({'success': True, 'important': todo.important})
