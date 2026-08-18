from flask import Blueprint, g, jsonify, request

from controllers import user_controller
from middlewares.auth import login_required

user_bp = Blueprint('users', __name__)


@user_bp.route('/users', methods=['GET'])
@login_required
def get_users():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    users = user_controller.list_users(page=page, per_page=per_page)
    return jsonify(users), 200


@user_bp.route('/users/<int:user_id>', methods=['GET'])
@login_required
def get_user(user_id):
    user, error, status_code = user_controller.get_user(user_id)
    if error:
        return jsonify({'error': error}), status_code
    return jsonify(user), status_code


@user_bp.route('/users', methods=['POST'])
@login_required
def create_user():
    data = request.get_json(silent=True)
    user, error, status_code = user_controller.create_user(data, caller=g.current_user)
    if error:
        return jsonify({'error': error}), status_code
    return jsonify(user), status_code


@user_bp.route('/users/<int:user_id>', methods=['PUT'])
@login_required
def update_user(user_id):
    data = request.get_json(silent=True)
    user, error, status_code = user_controller.update_user(user_id, data, caller=g.current_user)
    if error:
        return jsonify({'error': error}), status_code
    return jsonify(user), status_code


@user_bp.route('/users/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    result, error, status_code = user_controller.delete_user(user_id, caller=g.current_user)
    if error:
        return jsonify({'error': error}), status_code
    return jsonify(result), status_code


@user_bp.route('/users/<int:user_id>/tasks', methods=['GET'])
@login_required
def get_user_tasks(user_id):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    tasks, error, status_code = user_controller.get_user_tasks(user_id, page=page, per_page=per_page)
    if error:
        return jsonify({'error': error}), status_code
    return jsonify(tasks), status_code


@user_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True)
    result, error, status_code = user_controller.login(data)
    if error:
        return jsonify({'error': error}), status_code
    return jsonify(result), status_code
