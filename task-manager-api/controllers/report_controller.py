"""Reporting business logic: cross-entity aggregation.

All aggregation here uses grouped/aggregate queries (COUNT/GROUP BY)
instead of loading every row and counting in a Python loop, to avoid the
N+1 patterns the old inline report handlers had.
"""
from datetime import timedelta

from sqlalchemy import func

from database import db
from models.category import Category
from models.task import Task
from models.user import User
from utils.helpers import VALID_STATUSES, calculate_percentage, format_date, utc_now


def summary_report():
    now = utc_now()

    total_tasks = Task.query.count()
    total_users = User.query.count()
    total_categories = Category.query.count()

    status_counts = dict(
        db.session.query(Task.status, func.count(Task.id)).group_by(Task.status).all()
    )
    tasks_by_status = {status: status_counts.get(status, 0) for status in VALID_STATUSES}

    priority_counts = dict(
        db.session.query(Task.priority, func.count(Task.id)).group_by(Task.priority).all()
    )
    tasks_by_priority = {
        'critical': priority_counts.get(1, 0),
        'high': priority_counts.get(2, 0),
        'medium': priority_counts.get(3, 0),
        'low': priority_counts.get(4, 0),
        'minimal': priority_counts.get(5, 0),
    }

    overdue_tasks = Task.query.filter(
        Task.due_date.isnot(None),
        Task.due_date < now,
        Task.status.notin_(['done', 'cancelled']),
    ).all()
    overdue_list = [
        {
            'id': task.id,
            'title': task.title,
            'due_date': format_date(task.due_date),
            'days_overdue': (now - task.due_date).days,
        }
        for task in overdue_tasks
    ]

    seven_days_ago = now - timedelta(days=7)
    recent_tasks = Task.query.filter(Task.created_at >= seven_days_ago).count()
    recent_done = Task.query.filter(
        Task.status == 'done',
        Task.updated_at >= seven_days_ago,
    ).count()

    total_by_user = dict(
        db.session.query(Task.user_id, func.count(Task.id)).group_by(Task.user_id).all()
    )
    completed_by_user = dict(
        db.session.query(Task.user_id, func.count(Task.id))
        .filter(Task.status == 'done')
        .group_by(Task.user_id)
        .all()
    )

    users = User.query.order_by(User.id).all()
    user_stats = []
    for user in users:
        total = total_by_user.get(user.id, 0)
        completed = completed_by_user.get(user.id, 0)
        user_stats.append({
            'user_id': user.id,
            'user_name': user.name,
            'total_tasks': total,
            'completed_tasks': completed,
            'completion_rate': calculate_percentage(completed, total),
        })

    return {
        'generated_at': format_date(now),
        'overview': {
            'total_tasks': total_tasks,
            'total_users': total_users,
            'total_categories': total_categories,
        },
        'tasks_by_status': tasks_by_status,
        'tasks_by_priority': tasks_by_priority,
        'overdue': {
            'count': len(overdue_list),
            'tasks': overdue_list,
        },
        'recent_activity': {
            'tasks_created_last_7_days': recent_tasks,
            'tasks_completed_last_7_days': recent_done,
        },
        'user_productivity': user_stats,
    }


def user_report(user_id):
    user = User.query.get(user_id)
    if not user:
        return None, 'Usuário não encontrado', 404

    tasks = Task.query.filter_by(user_id=user_id).all()

    total = len(tasks)
    done = sum(1 for task in tasks if task.status == 'done')
    pending = sum(1 for task in tasks if task.status == 'pending')
    in_progress = sum(1 for task in tasks if task.status == 'in_progress')
    cancelled = sum(1 for task in tasks if task.status == 'cancelled')
    high_priority = sum(1 for task in tasks if task.priority <= 2)
    overdue = sum(1 for task in tasks if task.is_overdue())

    report = {
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
        },
        'statistics': {
            'total_tasks': total,
            'done': done,
            'pending': pending,
            'in_progress': in_progress,
            'cancelled': cancelled,
            'overdue': overdue,
            'high_priority': high_priority,
            'completion_rate': calculate_percentage(done, total),
        },
    }

    return report, None, 200
