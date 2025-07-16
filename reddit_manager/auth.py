import os
from functools import wraps
from flask import request, jsonify, current_app


def require_api_key(view):
    """Ensure that incoming requests contain a valid Authorization header."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        api_key = request.headers.get("Authorization")
        if not api_key:
            return jsonify({"error": "Forbidden"}), 403

        env_key = os.getenv("AUTH_KEY")
        if env_key and api_key == env_key:
            return view(*args, **kwargs)

        user_service = getattr(current_app, "user_service", None)
        if user_service and user_service.get_user_by_api_key(api_key):
            return view(*args, **kwargs)

        return jsonify({"error": "Forbidden"}), 403

    return wrapper
