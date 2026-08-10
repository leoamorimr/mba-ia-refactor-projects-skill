from flask import Blueprint, jsonify, request

from controllers import task_controller
from middlewares.auth import login_required

task_bp = Blueprint('tasks', __name__)


@task_bp.route('/tasks', methods=['GET'])
def get_tasks():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    tasks = task_controller.list_tasks(page=page, per_page=per_page)
    return jsonify(tasks), 200


@task_bp.route('/tasks/search', methods=['GET'])
def search_tasks():
    query = request.args.get('q', '')
    status = request.args.get('status', '')
    priority = request.args.get('priority', '')
    user_id = request.args.get('user_id', '')

    tasks, error, status_code = task_controller.search_tasks(query, status, priority, user_id)
    if error:
        return jsonify({'error': error}), status_code
    return jsonify(tasks), status_code


@task_bp.route('/tasks/stats', methods=['GET'])
def task_stats():
    stats = task_controller.task_stats()
    return jsonify(stats), 200


@task_bp.route('/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    task, error, status_code = task_controller.get_task(task_id)
    if error:
        return jsonify({'error': error}), status_code
    return jsonify(task), status_code


@task_bp.route('/tasks', methods=['POST'])
@login_required
def create_task():
    data = request.get_json(silent=True)
    task, error, status_code = task_controller.create_task(data)
    if error:
        return jsonify({'error': error}), status_code
    return jsonify(task), status_code


@task_bp.route('/tasks/<int:task_id>', methods=['PUT'])
@login_required
def update_task(task_id):
    data = request.get_json(silent=True)
    task, error, status_code = task_controller.update_task(task_id, data)
    if error:
        return jsonify({'error': error}), status_code
    return jsonify(task), status_code


@task_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
@login_required
def delete_task(task_id):
    result, error, status_code = task_controller.delete_task(task_id)
    if error:
        return jsonify({'error': error}), status_code
    return jsonify(result), status_code
