from flask import Blueprint, jsonify, current_app
import logging

from ..auth import require_api_key

admin_api = Blueprint('admin_api', __name__)
logger = logging.getLogger(__name__)


@admin_api.before_request
@require_api_key
def _require_api_key():
    """Enforce API key check for all admin routes."""
    pass


@admin_api.route('/reload', methods=['POST'])
def reload_services():
    """Reload service configuration from environment variables."""
    try:
        if hasattr(current_app, 'reddit'):
            current_app.reddit.reload_from_env()
        if hasattr(current_app, 'group_manager'):
            current_app.group_manager.reload_from_env()
        return jsonify({'message': 'Configuration reloaded'}), 200
    except Exception as e:
        logger.error(f'Error reloading configuration: {e}')
        return jsonify({'error': str(e)}), 500
