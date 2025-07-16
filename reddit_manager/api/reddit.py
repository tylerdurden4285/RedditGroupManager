from flask import Blueprint, jsonify, request, current_app
import logging
import os
import traceback
import prawcore
from functools import wraps


reddit_api = Blueprint('reddit_api', __name__)
logger = logging.getLogger(__name__)


def require_api_key(func):
    """Flask decorator to validate the Authorization header."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        api_key = request.headers.get("Authorization")
        if not api_key:
            return jsonify({"detail": "Could not validate credentials"}), 403

        env_key = os.getenv("AUTH_KEY")
        if env_key and api_key == env_key:
            return func(*args, **kwargs)

        user_service = getattr(current_app, "user_service", None)
        user = user_service.get_user_by_api_key(api_key) if user_service else None
        if not user:
            return jsonify({"detail": "Could not validate credentials"}), 403

        return func(*args, **kwargs)

    return wrapper


@reddit_api.before_request
def _require_api_key():
    """Enforce API key check for all reddit routes except flair lookups."""
    exempt_endpoints = {
        'reddit_api.get_reddit_flairs',
        'reddit_api.get_reddit_flairs_html',
    }
    if request.endpoint in exempt_endpoints:
        return None

    return require_api_key(lambda: None)()

@reddit_api.route('/flairs/<string:subreddit>', methods=['GET'])
def get_reddit_flairs(subreddit):
    """Get available flairs for a subreddit."""
    try:
        if not subreddit:
            return jsonify({"error": "Subreddit name is required", "flairs": []}), 400
        
        
        logger.info(f"Fetching flairs for r/{subreddit}")
        
        try:
            
            flairs = current_app.reddit.get_flairs(subreddit)
            
            
            if flairs:
                return jsonify({"flairs": flairs}), 200
            else:
                
                return jsonify({"message": "No flairs needed", "flairs": []}), 200
                
        except prawcore.exceptions.Redirect as e:
            
            logger.warning(f"Subreddit r/{subreddit} doesn't exist: {str(e)}")
            return jsonify({"error": "Subreddit doesn't exist. Try again", "flairs": []}), 200
            
        except prawcore.exceptions.Forbidden as e:
            
            logger.warning(f"Forbidden access to r/{subreddit}: {str(e)}")
            return jsonify({"error": "Cannot access this subreddit. It may be private.", "flairs": []}), 200
            
        except prawcore.exceptions.NotFound as e:
            
            logger.warning(f"Subreddit r/{subreddit} not found: {str(e)}")
            return jsonify({"error": "Subreddit doesn't exist. Try again", "flairs": []}), 200
            
        except Exception as e:
            error_str = str(e)
            logger.error(f"Error fetching flairs for r/{subreddit}: {error_str}")
            
            
            if 'Redirect' in error_str and '/subreddits/search' in error_str:
                return jsonify({"error": "Subreddit doesn't exist. Try again", "flairs": []}), 200
            elif '403' in error_str or 'Forbidden' in error_str:
                return jsonify({"error": "Cannot access this subreddit. It may be private.", "flairs": []}), 200
            else:
                return jsonify({"error": error_str, "flairs": []}), 200
    except Exception as e:
        logger.error(f"Error getting flairs for r/{subreddit}: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"error": "An unexpected error occurred. Please try again.", "flairs": []}), 200


@reddit_api.route('/flairs-html/<string:subreddit>', methods=['GET'])
def get_reddit_flairs_html(subreddit):
    """Get available flairs for a subreddit as HTML options for HTMX."""
    try:
        if not subreddit or subreddit == '{this.value}':
            return '<option value="">-- Enter a valid subreddit name --</option>'
        
        flairs = current_app.reddit.get_flairs(subreddit)
        
        if not flairs:
            return '<option value="">No flairs available for this subreddit</option>'
        
        html = '<option value="">-- Select a flair --</option>'
        for flair in flairs:
            html += f'<option value="{flair["id"]}" data-flair-text="{flair["text"]}">{flair["text"]}</option>'
        
        return html
    except Exception as e:
        logger.error(f"Error getting flairs HTML for r/{subreddit}: {str(e)}\n{traceback.format_exc()}")
        return '<option value="">Error loading flairs</option>'


@reddit_api.route('/post', methods=['POST'])
def create_post():
    """Create a new post to a subreddit."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        subreddit = data.get('subreddit', '').strip()
        title = data.get('title', '').strip()
        content_type = data.get('content_type', 'text')
        content = data.get('content', '').strip()
        flair_id = data.get('flair_id')
        
        if not subreddit:
            return jsonify({"error": "Subreddit name is required"}), 400
        
        if not title:
            return jsonify({"error": "Post title is required"}), 400
        
        
        if content_type == 'link':
            if not content:
                return jsonify({"error": "Link URL is required"}), 400
            
            post_id = current_app.reddit.post_link_to_subreddit(subreddit, title, content, flair_id)
        else:
            post_id = current_app.reddit.post_to_subreddit(subreddit, title, content, flair_id)
        
        return jsonify({
            "post_id": post_id,
            "subreddit": subreddit,
            "title": title,
            "content_type": content_type,
            "flair_id": flair_id
        }), 201
    except Exception as e:
        logger.error(f"Error creating post: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


@reddit_api.route('/comment', methods=['POST'])
def comment_on_post():
    """Comment on a Reddit post."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        post_id = data.get('post_id', '').strip()
        comment_text = data.get('comment_text', '').strip()
        
        if not post_id:
            return jsonify({"error": "Post ID is required"}), 400
        
        if not comment_text:
            return jsonify({"error": "Comment text is required"}), 400
        
        comment_id, permalink = current_app.reddit.comment_on_post(post_id, comment_text)
        
        return jsonify({
            "comment_id": comment_id,
            "permalink": permalink,
            "post_id": post_id
        }), 201
    except Exception as e:
        logger.error(f"Error commenting on post: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


