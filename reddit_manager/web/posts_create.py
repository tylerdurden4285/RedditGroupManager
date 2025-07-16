from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    current_app,
)
from ..tasks.post_tasks import process_post
from ..forms.post import PostForm, TextPostForm, LinkPostForm, ImagePostForm
from ..utils import quill_html_to_markdown
import logging
import traceback
import os
import datetime
from werkzeug.utils import secure_filename
import uuid
import shutil

posts_create_bp = Blueprint("posts_create", __name__, url_prefix="/posts")
logger = logging.getLogger(__name__)


def _parse_schedule_time(raw_value: str | None) -> datetime.datetime | None:
    """Parse schedule time allowing date-only values.

    If ``raw_value`` lacks a time portion, the ``DEFAULT_SCHED_TIME`` from
    configuration is appended.
    """
    if not raw_value:
        return None
    default_time = current_app.config.get("DEFAULT_SCHED_TIME", "00:00")
    value = raw_value.strip()

    if "T" not in value:
        if " " in value:
            value = value.replace(" ", "T")
        else:
            value = f"{value}T{default_time}"

    try:
        dt = datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M")
    except ValueError:
        return None
    return dt.replace(tzinfo=current_app.group_manager.timezone)

@posts_create_bp.route("/create")
def new_post():
    """Render the new post creation page."""
    form = PostForm()

    groups = current_app.group_manager.list_groups()

    form.group_id.choices = [(0, "Select a group...")] + [
        (g.id, g.name) for g in groups
    ]

    return render_template(
        "posts/create.html",
        form=form,
        groups=groups,
        page_title="Create Reddit Post",
    )


@posts_create_bp.route("/create", methods=["POST"])
def create_post():
    """Handle post creation form submission."""
    form = PostForm()

    groups = current_app.group_manager.list_groups()
    form.group_id.choices = [(0, "Select a group...")] + [
        (g.id, g.name) for g in groups
    ]

    if form.validate_on_submit():
        try:

            title = form.title.data.strip()
            campaign = form.campaign.data.strip()
            content_type = form.content_type.data

            content = ""
            if content_type == "text":
                content = form.text_content.data or ""
            elif content_type == "link":
                content = form.link_url.data or ""

            post_target = request.form.get("post_target")
            flair_id = form.flair_id.data or None

            post_results = []

            if post_target == "group":

                group_id = form.group_id.data

                if group_id == 0:
                    flash("Please select a group", "warning")
                    return render_template(
                        "posts/create.html", form=form, groups=groups
                    )

                group = current_app.group_manager.get_group(group_id)

                if not group or not group.subreddits:
                    flash(
                        "Selected group doesn't exist or has no subreddits", "warning"
                    )
                    return render_template(
                        "posts/create.html", form=form, groups=groups
                    )

                for subreddit in group.subreddits:
                    try:

                        sub_flair = subreddit.flair_id or flair_id

                        if content_type == "link":
                            post_id = current_app.reddit.post_link_to_subreddit(
                                subreddit.subreddit, title, content, sub_flair
                            )
                        else:
                            post_id = current_app.reddit.post_to_subreddit(
                                subreddit.subreddit, title, content, sub_flair
                            )

                        post_results.append(
                            {
                                "subreddit": subreddit.subreddit,
                                "status": "success",
                                "post_id": post_id,
                            }
                        )
                    except Exception as e:
                        logger.error(
                            f"Error posting to r/{subreddit.subreddit}: {str(e)}"
                        )
                        post_results.append(
                            {
                                "subreddit": subreddit.subreddit,
                                "status": "error",
                                "error": str(e),
                            }
                        )

                success_count = sum(1 for r in post_results if r["status"] == "success")

                if success_count == len(group.subreddits):
                    flash(
                        f"Successfully posted to {success_count}/{len(group.subreddits)}",
                        "success",
                    )
                elif success_count > 0:
                    flash(
                        f"Posted to {success_count} out of {len(group.subreddits)} subreddits with some errors",
                        "warning",
                    )
                else:
                    flash("Failed to post to any subreddits", "danger")
                    return render_template(
                        "posts/create.html", form=form, groups=groups
                    )

            else:

                subreddit = form.subreddit.data.strip()

                if not subreddit:
                    flash("Please enter a subreddit name", "warning")
                    return render_template(
                        "posts/create.html", form=form, groups=groups
                    )

                try:

                    if content_type == "link":
                        post_id = current_app.reddit.post_link_to_subreddit(
                            subreddit, title, content, flair_id
                        )
                    else:
                        post_id = current_app.reddit.post_to_subreddit(
                            subreddit, title, content, flair_id
                        )

                    post_results.append(
                        {
                            "subreddit": subreddit,
                            "status": "success",
                            "post_id": post_id,
                        }
                    )

                    flash(f"Successfully posted to r/{subreddit}", "success")

                except Exception as e:
                    logger.error(f"Error posting to r/{subreddit}: {str(e)}")
                    post_results.append(
                        {"subreddit": subreddit, "status": "error", "error": str(e)}
                    )

                    flash(f"Error posting to r/{subreddit}: {str(e)}", "danger")
                    return render_template(
                        "posts/create.html", form=form, groups=groups
                    )

            return redirect(url_for("posts_history.post_history"))

        except Exception as e:
            logger.error(f"Error creating post: {str(e)}\n{traceback.format_exc()}")
            flash(f"Error creating post: {str(e)}", "danger")

    return render_template("posts/create.html", form=form, groups=groups)


@posts_create_bp.route("/create/text")
def new_text_post():
    """Render the simplified text post creation page."""
    form = TextPostForm()

    groups = current_app.group_manager.list_groups()

    tz_obj = current_app.group_manager.timezone
    timezone_name = getattr(tz_obj, "key", str(tz_obj))
    current_time = datetime.datetime.now(tz_obj).strftime("%Y-%m-%d %H:%M")

    groups_data = []
    for group in groups:

        try:
            group_id = int(group.id)
        except (TypeError, ValueError):
            group_id = 0

        group_dict = {
            "id": group_id,
            "name": group.name,
            "description": group.description,
            "subreddits": [],
        }

        if group.subreddits and isinstance(group.subreddits, list):
            for sub in group.subreddits:
                if hasattr(sub, "subreddit") and sub.subreddit:
                    try:
                        sub_id = int(sub.id) if sub.id is not None else 0
                    except (TypeError, ValueError):
                        sub_id = 0

                    group_dict["subreddits"].append(
                        {
                            "id": sub_id,
                            "subreddit": sub.subreddit,
                            "flair_id": getattr(sub, "flair_id", ""),
                            "flair_text": getattr(sub, "flair_text", ""),
                        }
                    )

        groups_data.append(group_dict)


    return render_template(
        "posts/create_text.html",
        form=form,
        groups=groups_data,
        page_title="Create Text Post",
        timezone_name=timezone_name,
        current_time=current_time,
    )


@posts_create_bp.route("/create/text", methods=["POST"])
def create_text_post():
    """Handle text post creation form submission."""
    form = TextPostForm()

    groups = current_app.group_manager.list_groups()

    tz_obj = current_app.group_manager.timezone
    timezone_name = getattr(tz_obj, "key", str(tz_obj))
    current_time = datetime.datetime.now(tz_obj).strftime("%Y-%m-%d %H:%M")

    prepared_groups_data = []
    for group in groups:
        group_dict = {
            "id": group.id,
            "name": group.name,
            "description": group.description,
            "subreddits": [],
        }
        if group.subreddits:
            for sub in group.subreddits:
                group_dict["subreddits"].append(
                    {
                        "id": sub.id,
                        "subreddit": sub.subreddit,
                        "flair_id": sub.flair_id,
                        "flair_text": sub.flair_text,
                    }
                )
        prepared_groups_data.append(group_dict)

    if form.validate_on_submit():
        try:

            title = form.title.data.strip()
            campaign = form.campaign.data.strip()
            content_html = form.text_content.data or ""
            content = quill_html_to_markdown(content_html)
            flair_id = form.flair_id.data or None

            group_id = request.form.get("group_id")
            comment_html = request.form.get("comment_text")
            comment_text = (
                quill_html_to_markdown(comment_html) if comment_html else None
            )

            if not group_id or group_id == "0":
                flash("Please select a group", "warning")
                return render_template(
                    "posts/create_text.html",
                    form=form,
                    groups=prepared_groups_data,
                    timezone_name=timezone_name,
                    current_time=current_time,
                )

            selected_group = current_app.group_manager.get_group(int(group_id))
            if not selected_group or not selected_group.subreddits:
                flash("Selected group has no subreddits", "warning")
                return render_template(
                    "posts/create_text.html",
                    form=form,
                    groups=prepared_groups_data,
                    timezone_name=timezone_name,
                    current_time=current_time,
                )

            post_results = []
            obsolete_subreddits = []

            for subreddit_entry in selected_group.subreddits:
                subreddit = subreddit_entry.subreddit
                sub_flair = getattr(subreddit_entry, "flair_id", None) or flair_id
                try:
                    post_data = {
                        "subreddit": subreddit,
                        "title": title,
                        "content": (
                            content[:197] + "..." if len(content) > 200 else content
                        ),
                        "created_at": current_app.group_manager.get_current_timestamp(),
                        "post_type": "text",
                        "comment": (
                            comment_text.strip()
                            if comment_text and comment_text.strip()
                            else None
                        ),
                        "campaign": campaign,
                        "flair_id": sub_flair,
                        "flair_text": getattr(subreddit_entry, "flair_text", None),
                    }
                    scheduled_dt = (
                        form.schedule_time.data
                        or _parse_schedule_time(request.form.get("schedule_time"))
                    )

                    if scheduled_dt:
                        current_app.group_manager.create_scheduled_post(
                            post_data, scheduled_dt
                        )
                    else:
                        post_db_id = current_app.group_manager.create_processing_post(
                            post_data
                        )
                        current_app.queue.enqueue(process_post, post_db_id)
                except Exception as e:
                    logger.error(f"Error queueing post for r/{subreddit}: {str(e)}")

            if form.schedule_time.data or request.form.get("schedule_time"):
                flash("Posts scheduled", "success")
            else:
                flash("Posts queued for processing", "success")
            return redirect(url_for("posts_history.post_history"))

        except Exception as e:
            logger.error(f"Error creating post: {str(e)}\n{traceback.format_exc()}")
            flash(f"Error creating post: {str(e)}", "error")
            return render_template(
                "posts/create_text.html",
                form=form,
                groups=prepared_groups_data,
                timezone_name=timezone_name,
                current_time=current_time,
            )

    return render_template(
        "posts/create_text.html",
        form=form,
        groups=prepared_groups_data,
        timezone_name=timezone_name,
        current_time=current_time,
    )


@posts_create_bp.route("/create/link")
def new_link_post():
    """Render the Link post creation page."""
    form = LinkPostForm()

    groups = current_app.group_manager.list_groups()

    tz_obj = current_app.group_manager.timezone
    timezone_name = getattr(tz_obj, "key", str(tz_obj))
    current_time = datetime.datetime.now(tz_obj).strftime("%Y-%m-%d %H:%M")

    prepared_groups_data = []
    for group in groups:
        group_dict = {
            "id": group.id,
            "name": group.name,
            "description": group.description,
            "subreddits": [],
        }
        if group.subreddits:
            for sub in group.subreddits:
                group_dict["subreddits"].append(
                    {
                        "id": sub.id,
                        "subreddit": sub.subreddit,
                        "flair_id": sub.flair_id,
                        "flair_text": sub.flair_text,
                    }
                )
        prepared_groups_data.append(group_dict)

    return render_template(
        "posts/create_link.html",
        form=form,
        groups=prepared_groups_data,
        page_title="Create Link Post",
        timezone_name=timezone_name,
        current_time=current_time,
    )


@posts_create_bp.route("/create/link", methods=["POST"])
def create_link_post():
    """Handle Link post creation form submission."""
    form = LinkPostForm()

    groups = current_app.group_manager.list_groups()

    tz_obj = current_app.group_manager.timezone
    timezone_name = getattr(tz_obj, "key", str(tz_obj))
    current_time = datetime.datetime.now(tz_obj).strftime("%Y-%m-%d %H:%M")

    prepared_groups_data = []
    for group in groups:
        group_dict = {
            "id": group.id,
            "name": group.name,
            "description": group.description,
            "subreddits": [],
        }
        if group.subreddits:
            for sub in group.subreddits:
                group_dict["subreddits"].append(
                    {
                        "id": sub.id,
                        "subreddit": sub.subreddit,
                        "flair_id": sub.flair_id,
                        "flair_text": sub.flair_text,
                    }
                )
        prepared_groups_data.append(group_dict)

    if form.validate_on_submit():
        try:

            title = request.form.get("title")
            campaign = form.campaign.data.strip()
            link_url = request.form.get("link_url")
            group_id = request.form.get("group_id")
            flair_id = form.flair_id.data or None
            comment_html = request.form.get("comment")
            comment = quill_html_to_markdown(comment_html) if comment_html else None

            if not group_id or group_id == "0":
                flash("Please select a group", "warning")
                return render_template(
                    "posts/create_link.html",
                    form=form,
                    groups=prepared_groups_data,
                    timezone_name=timezone_name,
                    current_time=current_time,
                )

            selected_group = None
            for group in groups:
                if str(group.id) == str(group_id):
                    selected_group = group
                    break

            if not selected_group:
                flash("Selected group not found", "error")
                return render_template(
                    "posts/create_link.html",
                    form=form,
                    groups=prepared_groups_data,
                    timezone_name=timezone_name,
                    current_time=current_time,
                )

            if not selected_group.subreddits:
                flash("Selected group has no subreddits", "warning")
                return render_template(
                    "posts/create_link.html",
                    form=form,
                    groups=prepared_groups_data,
                    timezone_name=timezone_name,
                    current_time=current_time,
                )

            for subreddit_entry in selected_group.subreddits:
                subreddit = subreddit_entry.subreddit
                sub_flair = getattr(subreddit_entry, "flair_id", None) or flair_id
                try:
                    post_data = {
                        "subreddit": subreddit,
                        "title": title,
                        "content": link_url,
                        "created_at": current_app.group_manager.get_current_timestamp(),
                        "post_type": "link",
                        "comment": (
                            comment.strip() if comment and comment.strip() else None
                        ),
                        "campaign": campaign,
                        "flair_id": sub_flair,
                        "flair_text": getattr(subreddit_entry, "flair_text", None),
                    }
                    scheduled_dt = (
                        form.schedule_time.data
                        or _parse_schedule_time(request.form.get("schedule_time"))
                    )
                    if scheduled_dt:
                        current_app.group_manager.create_scheduled_post(
                            post_data, scheduled_dt
                        )
                    else:
                        post_db_id = current_app.group_manager.create_processing_post(
                            post_data
                        )
                        current_app.queue.enqueue(process_post, post_db_id)
                except Exception as e:
                    logger.error(f"Error queueing post for r/{subreddit}: {str(e)}")

            if form.schedule_time.data or request.form.get("schedule_time"):
                flash("Posts scheduled", "success")
            else:
                flash("Posts queued for processing", "success")
            return redirect(url_for("posts_history.post_history"))

        except Exception as e:
            logger.error(
                f"Error creating Link post: {str(e)}\n{traceback.format_exc()}"
            )
            flash(f"Error creating post: {str(e)}", "error")
            return render_template(
                "posts/create_link.html",
                form=form,
                groups=prepared_groups_data,
                timezone_name=timezone_name,
                current_time=current_time,
            )

    return render_template(
        "posts/create_link.html",
        form=form,
        groups=prepared_groups_data,
        timezone_name=timezone_name,
        current_time=current_time,
    )


@posts_create_bp.route("/create/image")
def new_image_post():
    """Render the image post creation page."""
    form = ImagePostForm()

    groups = current_app.group_manager.list_groups()

    tz_obj = current_app.group_manager.timezone
    timezone_name = getattr(tz_obj, "key", str(tz_obj))
    current_time = datetime.datetime.now(tz_obj).strftime("%Y-%m-%d %H:%M")

    prepared_groups_data = []
    for group in groups:
        group_dict = {
            "id": group.id,
            "name": group.name,
            "description": group.description,
            "subreddits": [],
        }
        if group.subreddits:
            for sub in group.subreddits:
                group_dict["subreddits"].append(
                    {
                        "id": sub.id,
                        "subreddit": sub.subreddit,
                        "flair_id": sub.flair_id,
                        "flair_text": sub.flair_text,
                    }
                )
        prepared_groups_data.append(group_dict)

    return render_template(
        "posts/create_image.html",
        form=form,
        groups=prepared_groups_data,
        page_title="Create Image Post",
        timezone_name=timezone_name,
        current_time=current_time,
    )


@posts_create_bp.route("/create/image", methods=["POST"])
def create_image_post():
    """Handle image post creation form submission."""
    form = ImagePostForm()

    groups = current_app.group_manager.list_groups()

    tz_obj = current_app.group_manager.timezone
    timezone_name = getattr(tz_obj, "key", str(tz_obj))
    current_time = datetime.datetime.now(tz_obj).strftime("%Y-%m-%d %H:%M")

    prepared_groups_data = []
    for group in groups:
        group_dict = {
            "id": group.id,
            "name": group.name,
            "description": group.description,
            "subreddits": [],
        }
        if group.subreddits:
            for sub in group.subreddits:
                group_dict["subreddits"].append(
                    {
                        "id": sub.id,
                        "subreddit": sub.subreddit,
                        "flair_id": sub.flair_id,
                        "flair_text": sub.flair_text,
                    }
                )
        prepared_groups_data.append(group_dict)

    if form.validate_on_submit():
        try:

            title = form.title.data.strip()
            campaign = form.campaign.data.strip()
            caption_html = form.text_content.data or ""
            caption = quill_html_to_markdown(caption_html)
            flair_id = form.flair_id.data or None

            group_id = request.form.get("group_id")

            if not group_id or group_id == "0":
                flash("Please select a group", "warning")
                return render_template(
                    "posts/create_image.html",
                    form=form,
                    groups=prepared_groups_data,
                    timezone_name=timezone_name,
                    current_time=current_time,
                )

            selected_group = current_app.group_manager.get_group(int(group_id))
            if not selected_group or not selected_group.subreddits:
                flash("Selected group has no subreddits", "warning")
                return render_template(
                    "posts/create_image.html",
                    form=form,
                    groups=prepared_groups_data,
                    timezone_name=timezone_name,
                    current_time=current_time,
                )

            image_file = form.image_file.data
            if not image_file:
                flash("Please select an image to upload", "warning")
                return render_template(
                    "posts/create_image.html",
                    form=form,
                    groups=prepared_groups_data,
                    timezone_name=timezone_name,
                    current_time=current_time,
                )

            temp_dir = os.path.join(current_app.instance_path, "temp")
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)

            filename = secure_filename(image_file.filename)
            temp_path = os.path.join(temp_dir, filename)
            image_file.save(temp_path)

            for subreddit_entry in selected_group.subreddits:
                selected_subreddit = subreddit_entry.subreddit
                sub_flair = getattr(subreddit_entry, "flair_id", None) or flair_id
                try:
                    unique_path = os.path.join(temp_dir, f"{uuid.uuid4()}_{filename}")
                    shutil.copy(temp_path, unique_path)
                    post_data = {
                        "subreddit": selected_subreddit,
                        "title": title,
                        "content": unique_path,
                        "image_path": unique_path,
                        "created_at": current_app.group_manager.get_current_timestamp(),
                        "post_type": "image",
                        "comment": (
                            caption.strip() if caption and caption.strip() else None
                        ),
                        "campaign": campaign,
                        "flair_id": sub_flair,
                        "flair_text": getattr(subreddit_entry, "flair_text", None),
                    }
                    scheduled_dt = (
                        form.schedule_time.data
                        or _parse_schedule_time(request.form.get("schedule_time"))
                    )
                    if scheduled_dt:
                        current_app.group_manager.create_scheduled_post(
                            post_data, scheduled_dt
                        )
                    else:
                        post_db_id = current_app.group_manager.create_processing_post(
                            post_data
                        )
                        current_app.queue.enqueue(process_post, post_db_id)
                except Exception as e:
                    logger.error(
                        f"Error queueing image post for r/{selected_subreddit}: {str(e)}"
                    )

            try:
                os.remove(temp_path)
            except Exception:
                logger.warning(f"Failed to remove temp image {temp_path}")

            if form.schedule_time.data or request.form.get("schedule_time"):
                flash("Posts scheduled", "success")
            else:
                flash("Posts queued for processing", "success")
            return redirect(url_for("posts_history.post_history"))

        except Exception as e:

            logger.error(f"Error in image post creation: {str(e)}")
            flash(f"An error occurred: {str(e)}", "error")
            return render_template(
                "posts/create_image.html",
                form=form,
                groups=prepared_groups_data,
                timezone_name=timezone_name,
                current_time=current_time,
            )

    return render_template(
        "posts/create_image.html",
        form=form,
        groups=prepared_groups_data,
        timezone_name=timezone_name,
        current_time=current_time,
    )
