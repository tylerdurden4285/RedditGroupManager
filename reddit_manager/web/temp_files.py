from flask import Blueprint, current_app, send_from_directory
import os


temp_files_bp = Blueprint('temp_files_bp', __name__, url_prefix='/temp')


@temp_files_bp.route('/<path:filename>')
def serve(filename: str):
    """Serve temporary files from the instance temp directory."""
    temp_dir = os.path.join(current_app.instance_path, 'temp')
    return send_from_directory(temp_dir, filename)
