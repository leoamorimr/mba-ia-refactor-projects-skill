"""Task business logic: validation, aggregation, and orchestration.

Routes only parse the request and shape the HTTP response; every rule
about what makes a task valid, overdue, etc. lives here (or on the model
for simple per-instance checks).
"""
import logging

from sqlalchemy.orm import joinedload

from database import db
from models.category import Category
from models.task import Task
from models.user import User
from utils.helpers import (
    DEFAULT_PRIORITY,
    DEFAULT_STATUS,
    calculate_percentage,
    process_task_data,
    utc_now,
)

logger = logging.getLogger(__name__)

DEFAULT_PAGE = 1
DEFAULT_PER_PAGE = 20


def list_tasks(page=DEFAULT_PAGE, per_page=DEFAULT_PER_PAGE):
    page = max(page, 1)
    per_page = max(min(per_page, 100), 1)

    tasks = (
        Task.query.options(joinedload(Task.user), joinedload(Task.category))
        .order_by(Task.id)
        .limit(per_page)
        .offset((page - 1) * per_page)
        .all()
    )

    result = []
    for task in tasks:
        task_data = task.to_dict()
        task_data['overdue'] = task.is_overdue()
        task_data['user_name'] = task.user.name if task.user else None
        task_data['category_name'] = task.category.name if task.category else None
        result.append(task_data)

    return result


def get_task(task_id):
    task = Task.query.get(task_id)
    if not task:
        return None, 'Task não encontrada', 404

    data = task.to_dict()
    data['overdue'] = task.is_overdue()
    return data, None, 200


def create_task(data):
    if not data:
        return None, 'Dados inválidos', 400

    title = data.get('title')
    if not title:
        return None, 'Título é obrigatório', 400

    fields, error = process_task_data(data)
    if error:
        return None, error, 400

    user_id = data.get('user_id')
    if user_id and not User.query.get(user_id):
        return None, 'Usuário não encontrado', 404

    category_id = data.get('category_id')
    if category_id and not Category.query.get(category_id):
        return None, 'Categoria não encontrada', 404

    task = Task(
        title=fields['title'],
        description=fields.get('description', data.get('description', '')),
        status=fields.get('status', DEFAULT_STATUS),
        priority=fields.get('priority', DEFAULT_PRIORITY),
        user_id=user_id,
        category_id=category_id,
        due_date=fields.get('due_date'),
        tags=fields.get('tags'),
    )

    db.session.add(task)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    logger.info('Task created: id=%s title=%s', task.id, task.title)
    return task.to_dict(), None, 201


def update_task(task_id, data):
    task = Task.query.get(task_id)
    if not task:
        return None, 'Task não encontrada', 404

    if not data:
        return None, 'Dados inválidos', 400

    fields, error = process_task_data(data)
    if error:
        return None, error, 400

    if 'user_id' in data:
        user_id = data['user_id']
        if user_id and not User.query.get(user_id):
            return None, 'Usuário não encontrado', 404
        task.user_id = user_id

    if 'category_id' in data:
        category_id = data['category_id']
        if category_id and not Category.query.get(category_id):
            return None, 'Categoria não encontrada', 404
        task.category_id = category_id

    for field in ('title', 'description', 'status', 'priority', 'due_date', 'tags'):
        if field in fields:
            setattr(task, field, fields[field])

    task.updated_at = utc_now()

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    logger.info('Task updated: id=%s', task.id)
    return task.to_dict(), None, 200


def delete_task(task_id):
    task = Task.query.get(task_id)
    if not task:
        return None, 'Task não encontrada', 404

    db.session.delete(task)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    logger.info('Task deleted: id=%s', task_id)
    return {'message': 'Task deletada com sucesso'}, None, 200


def search_tasks(query, status, priority, user_id):
    tasks_query = Task.query

    if query:
        tasks_query = tasks_query.filter(
            db.or_(Task.title.like(f'%{query}%'), Task.description.like(f'%{query}%'))
        )

    if status:
        tasks_query = tasks_query.filter(Task.status == status)

    if priority:
        try:
            priority_value = int(priority)
        except ValueError:
            return None, 'Prioridade deve ser um número', 400
        tasks_query = tasks_query.filter(Task.priority == priority_value)

    if user_id:
        try:
            user_id_value = int(user_id)
        except ValueError:
            return None, 'user_id deve ser um número', 400
        tasks_query = tasks_query.filter(Task.user_id == user_id_value)

    tasks = tasks_query.all()
    return [task.to_dict() for task in tasks], None, 200


def task_stats():
    total = Task.query.count()
    pending = Task.query.filter_by(status='pending').count()
    in_progress = Task.query.filter_by(status='in_progress').count()
    done = Task.query.filter_by(status='done').count()
    cancelled = Task.query.filter_by(status='cancelled').count()

    overdue_count = Task.query.filter(
        Task.due_date.isnot(None),
        Task.due_date < utc_now(),
        Task.status.notin_(['done', 'cancelled']),
    ).count()

    return {
        'total': total,
        'pending': pending,
        'in_progress': in_progress,
        'done': done,
        'cancelled': cancelled,
        'overdue': overdue_count,
        'completion_rate': calculate_percentage(done, total),
    }
