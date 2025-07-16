from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    current_app,
    send_from_directory,
)
import os
import datetime
import os
from ..tasks import post_tasks

posts_history_bp = Blueprint("posts_history", __name__, url_prefix="/posts")


@posts_history_bp.route("/", methods=["GET"])
def post_history():
    """Unified post history page showing all post types with filtering options."""
    post_type = request.args.get("post_type")
    current_filter = post_type
    status = None
    if post_type == "scheduled":
        status = "scheduled"
        post_type = None
    search_query = request.args.get("search")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=50, type=int)
    if per_page not in {20, 50, 100}:
        per_page = 50
    if page < 1:
        page = 1

    total_posts = current_app.group_manager.count_posts(
        post_type=post_type if post_type else None,
        search_query=search_query if search_query else None,
        start_date=start_date if start_date else None,
        end_date=end_date if end_date else None,
        status=status if status else None,
    )

    offset = (page - 1) * per_page

    posts = current_app.group_manager.get_recent_posts(
        limit=per_page,
        post_type=post_type if post_type else None,
        search_query=search_query if search_query else None,
        start_date=start_date if start_date else None,
        end_date=end_date if end_date else None,
        offset=offset,
        status=status if status else None,
    )

    posts.sort(key=lambda p: p.get("created_at", ""), reverse=True)

    for post in posts:
        if "created_at" in post:
            try:
                dt = datetime.datetime.fromisoformat(post["created_at"])
            except ValueError:
                dt = datetime.datetime.fromisoformat(post["created_at"].split(".")[0])
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone.utc)
            dt = dt.astimezone(current_app.group_manager.timezone)
            post["created_date"] = dt.strftime("%Y-%m-%d")
            post["created_time"] = dt.strftime("%H:%M")
        if "reddit_url" not in post:
            post["reddit_url"] = post.get("post_url")
        if post.get("scheduled_for"):
            try:
                sdt = datetime.datetime.fromisoformat(post["scheduled_for"])
                if sdt.tzinfo is None:
                    sdt = sdt.replace(tzinfo=datetime.timezone.utc)
                sdt = sdt.astimezone(current_app.group_manager.timezone)
                post["scheduled_date"] = sdt.strftime("%Y-%m-%d")
                post["scheduled_time"] = sdt.strftime("%H:%M")
            except Exception:
                post["scheduled_date"] = post["scheduled_for"]
                post["scheduled_time"] = ""
        if post.get("image_path"):
            post["local_image_url"] = url_for(
                "posts_history.preview_temp_file",
                filename=os.path.basename(post["image_path"]),
            )

    total_pages = (total_posts + per_page - 1) // per_page if per_page else 1

    return render_template(
        "posts/history.html",
        posts=posts,
        current_filter=current_filter,
        search_query=search_query,
        start_date=start_date,
        end_date=end_date,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        max_retries=post_tasks.retry_strategy.max,
        page_title="Post History",
    )


@posts_history_bp.route("/delete-history", methods=["POST"])
def delete_post_history():
    """Delete all post history records."""
    try:
        deleted = current_app.group_manager.delete_all_posts()
        flash(f"Deleted {deleted} post(s) from history", "success")
    except Exception as e:
        current_app.logger.error(f"Error deleting post history: {str(e)}")
        flash("Failed to delete post history", "error")
    return redirect(url_for("posts_history.post_history"))


@posts_history_bp.route("/preview/<path:filename>")
def preview_temp_file(filename: str):
    """Serve a temporary uploaded file from the instance temp directory."""
    temp_dir = os.path.join(current_app.instance_path, "temp")
    return send_from_directory(temp_dir, filename)
