from flask import Blueprint, redirect, url_for, flash, request, current_app, json
import os
import datetime
from ..tasks.post_tasks import process_post, undo_post_task

posts_actions_bp = Blueprint("posts_actions", __name__, url_prefix="/posts")

@posts_actions_bp.route("/clear-stuck", methods=["POST"])
def clear_stuck_posts():
    """Mark stuck or expired posts as failed."""
    count = current_app.group_manager.fail_processing_posts()
    flash(f"{count} posts marked as failed", "info")
    return redirect(url_for("posts_history.post_history"))

@posts_actions_bp.route("/mark-overdue", methods=["POST"])
def mark_overdue_scheduled_posts():
    """Mark any overdue scheduled posts as overdue."""
    count = current_app.group_manager.mark_overdue_scheduled_posts()
    flash(f"{count} scheduled posts marked overdue", "info")
    return redirect(url_for("posts_history.post_history"))

@posts_actions_bp.route("/clear-overdue", methods=["POST"])
def clear_overdue_scheduled_posts():
    """Mark overdue posts as failed."""
    count = current_app.group_manager.fail_overdue_posts()
    flash(f"{count} overdue posts marked as failed", "info")
    return redirect(url_for("posts_history.post_history"))

@posts_actions_bp.route("/delete-failed", methods=["POST"])
def delete_failed_posts():
    """Delete all posts that are marked as failed."""
    count = current_app.group_manager.delete_failed_posts()
    flash(f"{count} failed posts deleted", "info")
    return redirect(url_for("posts_history.post_history"))

@posts_actions_bp.route("/delete-all", methods=["POST"])
def delete_all_posts():
    """Delete all local post history."""
    count = current_app.group_manager.delete_all_posts()
    flash(f"{count} posts deleted", "info")
    return redirect(url_for("posts_history.post_history"))

@posts_actions_bp.route("/delete-selected", methods=["POST"])
def delete_selected_posts():
    """Delete selected posts by ID."""
    ids_raw = request.form.get("post_ids", "")
    if isinstance(ids_raw, list):
        id_list = [int(i) for i in ids_raw if str(i).isdigit()]
    else:
        id_list = [int(i) for i in ids_raw.split(",") if i.strip().isdigit()]
    deleted = 0
    if id_list:
        deleted = current_app.group_manager.delete_posts(id_list)
        flash(f"Deleted {deleted} post(s)", "info")
    else:
        flash("No posts selected", "warning")
    return redirect(url_for("posts_history.post_history"))

@posts_actions_bp.route("/edit-scheduled", methods=["POST"])
def edit_scheduled_posts():
    """Update the scheduled time for selected posts."""
    ids_raw = request.form.get("post_ids", "")
    if isinstance(ids_raw, list):
        id_list = [int(i) for i in ids_raw if str(i).isdigit()]
    else:
        id_list = [int(i) for i in ids_raw.split(",") if i.strip().isdigit()]

    time_str = request.form.get("schedule_time")
    if not time_str or not id_list:
        flash("No posts selected", "warning")
        return redirect(url_for("posts_history.post_history"))

    try:
        run_at = datetime.datetime.fromisoformat(time_str)
    except ValueError:
        flash("Invalid schedule time", "error")
        return redirect(url_for("posts_history.post_history"))

    count = 0
    for pid in id_list:
        if current_app.group_manager.update_scheduled_post(pid, run_at):
            count += 1

    flash(f"Updated {count} post(s)", "info")
    return redirect(url_for("posts_history.post_history"))

@posts_actions_bp.route("/undo-selected", methods=["POST"])
def undo_selected_posts():
    """Undo multiple posts by ID."""
    ids_raw = request.form.get("post_ids", "")
    if isinstance(ids_raw, list):
        id_list = [int(i) for i in ids_raw if str(i).isdigit()]
    else:
        id_list = [int(i) for i in ids_raw.split(",") if i.strip().isdigit()]
    if id_list:
        for pid in id_list:
            current_app.queue.enqueue(undo_post_task, pid)
        flash(f"Queued {len(id_list)} post(s) for undo", "info")
    else:
        flash("No posts selected", "warning")
    return redirect(url_for("posts_history.post_history"))

@posts_actions_bp.route("/repost-selected", methods=["POST"])
def repost_selected_posts():
    """Repost multiple posts by ID."""
    ids_raw = request.form.get("post_ids", "")
    if isinstance(ids_raw, list):
        id_list = [int(i) for i in ids_raw if str(i).isdigit()]
    else:
        id_list = [int(i) for i in ids_raw.split(",") if i.strip().isdigit()]
    count = 0
    if id_list:
        for pid in id_list:
            if current_app.group_manager.repost_post(pid):
                current_app.queue.enqueue(process_post, pid)
                count += 1
        flash(f"Queued {count} post(s) for repost", "info")
    else:
        flash("No posts selected", "warning")
    return redirect(url_for("posts_history.post_history"))

@posts_actions_bp.route("/statuses")
def post_statuses():
    """Return status and retry count for recent posts."""
    posts = current_app.group_manager.get_recent_posts(limit=50)
    post_map = {p["id"]: p for p in posts}

    ids_raw = request.args.get("ids")
    if ids_raw:
        try:
            id_list = [int(i) for i in ids_raw.split(",") if i.strip().isdigit()]
        except ValueError:
            id_list = []
        for pid in id_list:
            if pid not in post_map:
                post = current_app.group_manager.get_post(pid)
                if post:
                    post_map[pid] = post

    statuses = [
        {
            "id": p["id"],
            "status": p.get("status"),
            "retry_count": p.get("retry_count", 0),
            "reddit_url": p.get("reddit_url"),
            "content": p.get("content"),
            "error_message": p.get("error_message"),
            "preview_url": (
                url_for(
                    "posts_history.preview_temp_file",
                    filename=os.path.basename(p.get("image_path", "")),
                )
                if p.get("post_type") == "image"
                and p.get("image_path")
                and os.path.isfile(
                    os.path.join(
                        current_app.instance_path,
                        "temp",
                        os.path.basename(p.get("image_path")),
                    )
                )
                else None
            ),
        }
        for p in post_map.values()
    ]

    return current_app.response_class(
        response=json.dumps(statuses),
        status=200,
        mimetype="application/json",
    )

@posts_actions_bp.route("/<int:post_id>/requeue", methods=["POST"])
@posts_actions_bp.route("/<int:post_id>/repost", methods=["POST"])
def repost_post(post_id):
    """Repost a failed post using the existing record."""
    if current_app.group_manager.repost_post(post_id):
        current_app.queue.enqueue(process_post, post_id)
        flash("Post reposted", "success")
    else:
        flash("Post not found", "error")
    return redirect(url_for("posts_history.post_history"))

@posts_actions_bp.route("/<int:post_id>/undo", methods=["POST"])
def undo_post(post_id):
    """Delete a posted submission from Reddit and mark it as undone."""
    if current_app.group_manager.get_post(post_id):
        current_app.queue.enqueue(undo_post_task, post_id)
        flash("Undo queued", "info")
    else:
        flash("Post not found", "error")
    return redirect(url_for("posts_history.post_history"))
