"""Category business logic: validation and orchestration."""
import logging

from sqlalchemy import func

from database import db
from models.category import Category
from models.task import Task
from utils.helpers import DEFAULT_COLOR, is_valid_color

logger = logging.getLogger(__name__)

DEFAULT_PAGE = 1
DEFAULT_PER_PAGE = 20


def list_categories(page=DEFAULT_PAGE, per_page=DEFAULT_PER_PAGE):
    page = max(page, 1)
    per_page = max(min(per_page, 100), 1)

    categories = (
        Category.query.order_by(Category.id)
        .limit(per_page)
        .offset((page - 1) * per_page)
        .all()
    )

    category_ids = [category.id for category in categories]
    task_counts = dict(
        db.session.query(Task.category_id, func.count(Task.id))
        .filter(Task.category_id.in_(category_ids))
        .group_by(Task.category_id)
        .all()
    )

    result = []
    for category in categories:
        category_data = category.to_dict()
        category_data['task_count'] = task_counts.get(category.id, 0)
        result.append(category_data)

    return result


def create_category(data):
    if not data:
        return None, 'Dados inválidos', 400

    name = data.get('name')
    if not name:
        return None, 'Nome é obrigatório', 400

    color = data.get('color', DEFAULT_COLOR)
    if not is_valid_color(color):
        return None, 'Cor inválida. Use o formato #RRGGBB', 400

    category = Category(name=name, description=data.get('description', ''), color=color)

    db.session.add(category)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    logger.info('Category created: id=%s name=%s', category.id, category.name)
    return category.to_dict(), None, 201


def update_category(category_id, data):
    category = Category.query.get(category_id)
    if not category:
        return None, 'Categoria não encontrada', 404

    if not data:
        return None, 'Dados inválidos', 400

    if 'name' in data:
        if not data['name']:
            return None, 'Nome é obrigatório', 400
        category.name = data['name']

    if 'description' in data:
        category.description = data['description']

    if 'color' in data:
        if not is_valid_color(data['color']):
            return None, 'Cor inválida. Use o formato #RRGGBB', 400
        category.color = data['color']

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return category.to_dict(), None, 200


def delete_category(category_id):
    category = Category.query.get(category_id)
    if not category:
        return None, 'Categoria não encontrada', 404

    # Clear the FK on dependent tasks instead of leaving them pointing at a
    # deleted category (dangling category_id).
    Task.query.filter_by(category_id=category_id).update({'category_id': None})

    db.session.delete(category)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    logger.info('Category deleted: id=%s', category_id)
    return {'message': 'Categoria deletada'}, None, 200
