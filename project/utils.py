from datetime import date, timedelta
from collections import OrderedDict
from flask_login import current_user
from .models import db, Todo

def get_lawn_data(year=None):
    today = date.today()
    if year is None:
        year = today.year

    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)

    completed_todos = db.session.query(db.func.date(Todo.completed_at), db.func.count(Todo.id)).filter(
        Todo.user_id == current_user.id,
        Todo.completed_at.isnot(None),
        db.func.date(Todo.completed_at) >= start_date,
        db.func.date(Todo.completed_at) <= end_date
    ).group_by(db.func.date(Todo.completed_at)).all()

    completion_counts = {d: c for d, c in completed_todos}

    start_of_grid = start_date - timedelta(days=(start_date.weekday() + 1) % 7)
    end_of_grid = end_date + timedelta(days=5 - end_date.weekday())

    weeks = []
    current_week = []
    day_cursor = start_of_grid
    
    while day_cursor <= end_of_grid:
        count = completion_counts.get(day_cursor, 0)
        level = 4 if count >= 10 else 3 if count >= 5 else 2 if count >= 3 else 1 if count > 0 else 0
        
        current_week.append({
            "date": day_cursor,
            "count": count,
            "level": level,
        })

        if day_cursor.weekday() == 5:
            weeks.append(current_week)
            current_week = []
        
        day_cursor += timedelta(days=1)

    month_weeks = OrderedDict()
    for week in weeks:
        month_name = week[3]['date'].strftime('%b') if len(week) > 3 else week[0]['date'].strftime('%b')
        month_weeks.setdefault(month_name, 0)
        month_weeks[month_name] += 1
    
    return weeks, month_weeks, today
