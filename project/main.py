from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from .models import db, Todo
from datetime import datetime
from .utils import get_lawn_data

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required
def index():
    todos = Todo.query.filter_by(user_id=current_user.id).order_by(
        Todo.completed.asc(),
        Todo.due_date.is_(None),
        Todo.due_date.asc(),
        Todo.important.desc(),
        Todo.created_at.desc()
    ).all()
    
    from datetime import date
    current_year = date.today().year
    weeks, month_weeks, today = get_lawn_data(current_year)
    
    return render_template('index.html', todos=todos, today=today, weeks=weeks, month_weeks=month_weeks)

@main_bp.route('/lawn/')
@login_required
def lawn():
    from datetime import date
    current_year = date.today().year
    weeks, month_weeks, today = get_lawn_data(current_year)
    return render_template('lawn.html', weeks=weeks, today=today, month_weeks=month_weeks)

@main_bp.route('/add/', methods=['POST'])
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

@main_bp.route('/edit/<int:todo_id>/', methods=['GET', 'POST'])
@login_required
def edit_todo(todo_id):
    todo = Todo.query.get_or_404(todo_id)
    if todo.author != current_user:
        flash('수정 권한이 없습니다.', 'danger')
        return redirect(url_for('main.index'))

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
        return redirect(url_for('main.index'))

    return render_template('edit_todo.html', todo=todo)

@main_bp.route('/complete/<int:todo_id>/', methods=['POST'])
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

@main_bp.route('/delete/<int:todo_id>/', methods=['POST'])
@login_required
def delete_todo(todo_id):
    todo = Todo.query.get_or_404(todo_id)
    if todo.author != current_user:
        return jsonify({'success': False, 'error': '권한이 없습니다.'}), 403
    db.session.delete(todo)
    db.session.commit()
    return jsonify({'success': True})

@main_bp.route('/important/<int:todo_id>/', methods=['POST'])
@login_required
def important_todo(todo_id):
    todo = Todo.query.get_or_404(todo_id)
    if todo.author != current_user:
        return jsonify({'success': False, 'error': '권한이 없습니다.'}), 403
    todo.important = not todo.important
    db.session.commit()
    return jsonify({'success': True, 'important': todo.important})
