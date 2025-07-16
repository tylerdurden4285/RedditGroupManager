from flask import Blueprint, jsonify, request, current_app
from ..services.group_service import GroupServiceError
import logging
import traceback

from ..auth import require_api_key


groups_api = Blueprint('groups_api', __name__)
logger = logging.getLogger(__name__)


@groups_api.before_request
@require_api_key
def _require_api_key():
    """Enforce API key check for all group routes."""
    pass


@groups_api.route('/', methods=['GET'])
def get_groups():
    """Get all groups."""
    try:
        groups = current_app.group_manager.list_groups()
        return jsonify([group.to_dict() for group in groups]), 200
    except Exception as e:
        logger.error(f"Error getting groups: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


@groups_api.route('/', methods=['POST'])
def create_group():
    """Create a new group."""
    try:
        data = request.get_json()
        
        if not data or 'name' not in data:
            return jsonify({"error": "Group name is required"}), 400
        
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        subreddits = data.get('subreddits', [])

        if not name:
            return jsonify({"error": "Group name cannot be empty"}), 400

        
        try:
            group_id = current_app.group_manager.create_group(name, description, subreddits)
        except ValueError as ve:
            return jsonify({"error": str(ve)}), 400
        except GroupServiceError as ge:
            return jsonify({"error": str(ge)}), 409
        
        if group_id:
            return jsonify({"id": group_id, "name": name, "description": description}), 201
        else:
            return jsonify({"error": "Failed to create group"}), 500
    except Exception as e:
        logger.error(f"Error creating group: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


@groups_api.route('/<int:group_id>', methods=['GET'])
def get_group(group_id):
    """Get a specific group by ID."""
    try:
        group = current_app.group_manager.get_group(group_id)
        
        if group:
            return jsonify(group.to_dict()), 200
        else:
            return jsonify({"error": "Group not found"}), 404
    except Exception as e:
        logger.error(f"Error getting group {group_id}: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


@groups_api.route('/<int:group_id>', methods=['PUT'])
def update_group(group_id):
    """Update a group's details."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        
        existing_group = current_app.group_manager.get_group(group_id)
        if not existing_group:
            return jsonify({"error": "Group not found"}), 404
        
        name = data.get('name', existing_group.name).strip()
        description = data.get('description', existing_group.description).strip()

        
        subreddits = data.get('subreddits', None)

        if not name:
            return jsonify({"error": "Group name cannot be empty"}), 400

        if subreddits is not None and len(subreddits) == 0:
            return jsonify({"error": "At least one subreddit is required"}), 400

        
        try:
            success = current_app.group_manager.update_group(group_id, name, description, subreddits)
        except ValueError as ve:
            return jsonify({"error": str(ve)}), 400
        
        if success:
            return jsonify({"id": group_id, "name": name, "description": description}), 200
        else:
            return jsonify({"error": "Failed to update group"}), 500
    except Exception as e:
        logger.error(f"Error updating group {group_id}: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


@groups_api.route('/<int:group_id>', methods=['DELETE'])
def delete_group(group_id):
    """Delete a group."""
    try:
        
        group = current_app.group_manager.get_group(group_id)
        if not group:
            return jsonify({"error": "Group not found"}), 404
        
        
        success = current_app.group_manager.delete_group(group_id)
        
        if success:
            return jsonify({"message": "Group deleted successfully"}), 200
        else:
            return jsonify({"error": "Failed to delete group"}), 500
    except Exception as e:
        logger.error(f"Error deleting group {group_id}: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


@groups_api.route('/<int:group_id>/subreddits', methods=['GET'])
def get_group_subreddits(group_id):
    """Get all subreddits in a group."""
    try:
        
        group = current_app.group_manager.get_group(group_id)
        if not group:
            return jsonify({"error": "Group not found"}), 404
        
        
        subreddits = current_app.group_manager.get_group_subreddits(group_id)
        return jsonify([subreddit.to_dict() for subreddit in subreddits]), 200
    except Exception as e:
        logger.error(f"Error getting subreddits for group {group_id}: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


@groups_api.route('/<int:group_id>/subreddits', methods=['POST'])
def add_subreddit_to_group(group_id):
    """Add a subreddit to a group."""
    try:
        data = request.get_json()
        
        if not data or 'subreddit' not in data:
            return jsonify({"error": "Subreddit name is required"}), 400
        
        
        group = current_app.group_manager.get_group(group_id)
        if not group:
            return jsonify({"error": "Group not found"}), 404
        
        subreddit = data.get('subreddit', '').strip()
        flair_id = data.get('flair_id')
        
        if not subreddit:
            return jsonify({"error": "Subreddit name cannot be empty"}), 400
        
        
        try:
            subreddit_id = current_app.group_manager.add_subreddit_to_group(group_id, subreddit, flair_id)
        except GroupServiceError as e:
            
            return jsonify({"error": str(e)}), 409

        if subreddit_id:
            return jsonify({
                "id": subreddit_id,
                "group_id": group_id,
                "subreddit": subreddit,
                "flair_id": flair_id
            }), 201
        else:
            return jsonify({"error": "Failed to add subreddit to group"}), 500
    except Exception as e:
        logger.error(f"Error adding subreddit to group {group_id}: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


@groups_api.route('/<int:group_id>/subreddits/<string:subreddit>', methods=['DELETE'])
def remove_subreddit_from_group(group_id, subreddit):
    """Remove a subreddit from a group."""
    try:
        
        group = current_app.group_manager.get_group(group_id)
        if not group:
            return jsonify({"error": "Group not found"}), 404
        
        
        success = current_app.group_manager.remove_subreddit_from_group(group_id, subreddit)
        
        if success:
            return jsonify({"message": "Subreddit removed successfully"}), 200
        else:
            return jsonify({"error": "Failed to remove subreddit or subreddit not found in group"}), 404
    except Exception as e:
        logger.error(f"Error removing subreddit {subreddit} from group {group_id}: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500
