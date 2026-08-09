"""Routing + request/response shaping only for the `/usuarios` and
`/login` domain.
"""
from flask import Blueprint, jsonify, request

from controllers import user_controller

user_bp = Blueprint("users", __name__)


@user_bp.route("/usuarios", methods=["GET"])
def listar_usuarios():
    limit = request.args.get("limit", type=int)
    offset = request.args.get("offset", 0, type=int)
    usuarios = user_controller.list_users(limit=limit, offset=offset)
    return jsonify({"dados": usuarios, "sucesso": True}), 200


@user_bp.route("/usuarios/<int:id>", methods=["GET"])
def buscar_usuario(id):
    usuario = user_controller.get_user(id)
    if usuario:
        return jsonify({"dados": usuario, "sucesso": True}), 200
    return jsonify({"erro": "Usuário não encontrado"}), 404


@user_bp.route("/usuarios", methods=["POST"])
def criar_usuario():
    dados = request.get_json(silent=True)
    if not dados:
        return jsonify({"erro": "Dados inválidos"}), 400

    nome = dados.get("nome", "")
    email = dados.get("email", "")
    senha = dados.get("senha", "")

    erro = user_controller.validate_new_user(nome, email, senha)
    if erro:
        return jsonify({"erro": erro}), 400

    novo_id = user_controller.create_user(nome, email, senha)
    return jsonify({"dados": {"id": novo_id}, "sucesso": True}), 201


@user_bp.route("/login", methods=["POST"])
def login():
    dados = request.get_json(silent=True) or {}
    email = dados.get("email", "")
    senha = dados.get("senha", "")

    if not email or not senha:
        return jsonify({"erro": "Email e senha são obrigatórios"}), 400

    usuario = user_controller.authenticate(email, senha)
    if usuario:
        return jsonify({"dados": usuario, "sucesso": True, "mensagem": "Login OK"}), 200
    return jsonify({"erro": "Email ou senha inválidos", "sucesso": False}), 401
