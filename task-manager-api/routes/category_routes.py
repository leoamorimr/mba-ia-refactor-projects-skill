from flask import Blueprint, jsonify, request

from controllers import category_controller
from middlewares.auth import login_required

category_bp = Blueprint('categories', __name__)


@category_bp.route('/categories', methods=['GET'])
def get_categories():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    categories = category_controller.list_categories(page=page, per_page=per_page)
    return jsonify(categories), 200


@category_bp.route('/categories', methods=['POST'])
@login_required
def create_category():
    data = request.get_json(silent=True)
    category, error, status_code = category_controller.create_category(data)
    if error:
        return jsonify({'error': error}), status_code
    return jsonify(category), status_code


@category_bp.route('/categories/<int:category_id>', methods=['PUT'])
@login_required
def update_category(category_id):
    data = request.get_json(silent=True)
    category, error, status_code = category_controller.update_category(category_id, data)
    if error:
        return jsonify({'error': error}), status_code
    return jsonify(category), status_code


@category_bp.route('/categories/<int:category_id>', methods=['DELETE'])
@login_required
def delete_category(category_id):
    result, error, status_code = category_controller.delete_category(category_id)
    if error:
        return jsonify({'error': error}), status_code
    return jsonify(result), status_code
