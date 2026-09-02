# routes/ai.py
"""Endpoint do assistente de IA usado no formulário de criação de tarefa."""

from flask import Blueprint, jsonify, request
from flask_login import login_required

from services.ai_service import AIServiceError, parse_task_description
from utils import validate_csrf_token

ai_bp = Blueprint("ai", __name__)


@ai_bp.route("/interpretar-tarefa", methods=["POST"])
@login_required
def parse_task():
    # Este endpoint é chamado via fetch (JSON), não por um <form> comum —
    # por isso o token CSRF vem no corpo JSON em vez de um campo oculto.
    payload = request.get_json(silent=True) or {}

    if not validate_csrf_token(payload.get("csrf_token")):
        return jsonify(success=False, message="Sessão expirada. Recarregue a página."), 400

    free_text = (payload.get("text") or "").strip()
    if not free_text:
        return jsonify(success=False, message="Descreva a tarefa antes de usar o assistente."), 400

    try:
        result = parse_task_description(free_text)
    except AIServiceError as exc:
        # Erro esperado (sem chave configurada, API fora do ar etc.): devolve
        # 200 com success=False para o frontend mostrar a mensagem e cair no
        # preenchimento manual, sem tratar como um bug da aplicação.
        return jsonify(success=False, message=str(exc))

    return jsonify(success=True, data=result)
