from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, json
from flask_wtf import FlaskForm
from wtforms import StringField, HiddenField, TextAreaField
from wtforms.validators import DataRequired
import logging
import traceback
from werkzeug.exceptions import NotFound


groups_bp = Blueprint('groups', __name__)
logger = logging.getLogger(__name__)


class GroupForm(FlaskForm):
    """Form for group creation and editing."""
    name = StringField('Group Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    subreddits = HiddenField('Subreddits')
    flairs = HiddenField('Flairs')


@groups_bp.route('/')
def list_groups():
    """Render the groups list page."""
    try:
        
        logger.info("Fetching groups for list page")
        groups = current_app.group_manager.list_groups()
        logger.info(f"Successfully loaded {len(groups)} groups")
        
        
        for group in groups:
            logger.info(f"Group: {group.name}, ID: {group.id}, Subreddits: {len(group.subreddits) if group.subreddits else 0}")
            if group.subreddits:
                for subreddit in group.subreddits:
                    logger.info(f"  Subreddit: {subreddit.subreddit}, Flair: {subreddit.flair_text}")
        
        return render_template('groups/list.html', 
                              groups=groups,
                              page_title="Reddit Groups")
    except Exception as e:
        logger.error(f"Error loading groups list: {str(e)}\n{traceback.format_exc()}")
        flash(f"Error loading groups: {str(e)}", "error")
        return render_template('groups/list.html', 
                              groups=[],
                              page_title="Reddit Groups",
                              error=str(e))


@groups_bp.route('/new')
def new_group():
    """Render the new group creation page."""
    form = GroupForm()
    return render_template('groups/edit.html', 
                         form=form,
                         group=None,
                         is_new=True,
                         page_title="Create New Group")


@groups_bp.route('/edit/<int:group_id>')
def edit_group(group_id):
    """Render the edit group page."""
    try:
        
        group = current_app.group_manager.get_group(group_id)
        
        if not group:
            logger.warning(f"Group not found: {group_id}")
            flash("Group not found", "error")
            return redirect(url_for('groups.list_groups'))
        
        
        form = GroupForm()
        form.name.data = group.name
        form.description.data = group.description
        
        
        subreddits_json = json.dumps([s.to_dict() for s in group.subreddits])
        form.subreddits.data = subreddits_json
        
        return render_template('groups/edit.html',
                              form=form,
                              group=group,
                              is_new=False,
                              page_title=f"Edit Group: {group.name}")
    
    except Exception as e:
        logger.error(f"Error loading group {group_id} for editing: {str(e)}\n{traceback.format_exc()}")
        flash(f"Error loading group: {str(e)}", "error")
        return redirect(url_for('groups.list_groups'))


@groups_bp.route('/create', methods=['POST'])
def create_group():
    """Handle group creation form submission."""
    form = GroupForm()
    
    if form.validate_on_submit():
        try:
            name = form.name.data.strip()
            description = form.description.data.strip() if form.description.data else ""

            
            subreddits = []
            if form.subreddits.data:
                try:
                    subreddits = json.loads(form.subreddits.data)
                except json.JSONDecodeError:
                    logger.warning("Invalid subreddits JSON")

            
            group_id = current_app.group_manager.create_group(
                name,
                description,
                subreddits,
            )

            logger.debug(f"create_group service returned: {group_id}")
            if group_id:
                logger.info(f"Group created: {name} (ID: {group_id}), redirecting to list")
                flash(f"Group '{name}' created successfully", "success")
                return redirect(url_for('groups.list_groups'))
            else:
                logger.error(f"Failed to create group: {name}")
                flash("Error creating group", "error")

        except ValueError as ve:
            logger.warning(str(ve))
            flash(str(ve), "error")
            return render_template(
                'groups/edit.html',
                form=form,
                group=None,
                is_new=True,
                page_title="Create New Group",
                subreddits_error=str(ve)
            )
        except Exception as e:
            logger.error(f"Error creating group: {str(e)}\n{traceback.format_exc()}")
            flash(f"Error creating group: {str(e)}", "error")
    
    
    logger.warning("Form validation failed during group creation")
    return render_template('groups/edit.html', 
                          form=form,
                          group=None,
                          is_new=True,
                          page_title="Create New Group")


@groups_bp.route('/update/<int:group_id>', methods=['POST'])
def update_group(group_id):
    """Handle group update form submission."""
    form = GroupForm()
    
    if form.validate_on_submit():
        try:
            
            existing_group = current_app.group_manager.get_group(group_id)

            if not existing_group:
                logger.warning(f"Group not found for update: {group_id}")
                flash("Group not found", "error")
                return redirect(url_for('groups.list_groups'))

            name = form.name.data.strip()
            description = form.description.data.strip() if form.description.data else ""

            
            subreddits = []
            if form.subreddits.data:
                try:
                    subreddits = json.loads(form.subreddits.data)
                except json.JSONDecodeError:
                    logger.warning("Invalid subreddits JSON")

            if not subreddits:
                raise ValueError("At least one subreddit is required")

            
            success = current_app.group_manager.update_group(
                group_id,
                name,
                description,
                subreddits,
            )

            logger.debug(f"update_group service returned: {success}")
            if success:
                logger.info(f"Group updated: {name} (ID: {group_id}), redirecting to list")
                flash(f"Group '{name}' updated successfully", "success")
                return redirect(url_for('groups.list_groups'))
            else:
                logger.error(f"Failed to update group: {group_id}")
                flash("Error updating group", "error")

        except ValueError as ve:
            logger.warning(str(ve))
            flash(str(ve), "error")
            return render_template(
                'groups/edit.html',
                form=form,
                group={"id": group_id},
                is_new=False,
                page_title="Edit Group",
                subreddits_error=str(ve)
            )
        except Exception as e:
            logger.error(f"Error updating group {group_id}: {str(e)}\n{traceback.format_exc()}")
            flash(f"Error updating group: {str(e)}", "error")
    
    
    logger.warning(f"Form validation failed during group update for ID: {group_id}")
    return render_template('groups/edit.html', 
                          form=form,
                          group={"id": group_id},
                          is_new=False,
                          page_title="Edit Group")


@groups_bp.route('/delete/<int:group_id>', methods=['DELETE', 'POST'])
def delete_group(group_id):
    """Delete a group via HTMX request or HTML form submission."""
    try:
        
        group = current_app.group_manager.get_group(group_id)
        
        if not group:
            if request.headers.get('HX-Request'):
                
                return "Group not found", 404
            else:
                
                flash("Group not found", "error")
                return redirect(url_for('groups.list_groups'))
        
        
        success = current_app.group_manager.delete_group(group_id)
        
        if success:
            logger.info(f"Group deleted: {group.name} (ID: {group_id})")

            if request.headers.get('HX-Request'):
                
                response = current_app.response_class("", status=200)
                response.headers["HX-Trigger"] = json.dumps({
                    "toast": {
                        "message": f"Group '{group.name}' deleted successfully",
                        "category": "success",
                    }
                })
                return response
            else:
                
                flash(f"Group '{group.name}' deleted successfully", "success")
                return redirect(url_for('groups.list_groups'))
        else:
            logger.error(f"Failed to delete group: {group_id}")
            
            if request.headers.get('HX-Request'):
                return "Error deleting group", 500
            else:
                flash("Error deleting group", "error")
                return redirect(url_for('groups.list_groups'))
    
    except Exception as e:
        logger.error(f"Error deleting group {group_id}: {str(e)}\n{traceback.format_exc()}")
        
        if request.headers.get('HX-Request'):
            return f"Error: {str(e)}", 500
        else:
            flash(f"Error deleting group: {str(e)}", "error")
            return redirect(url_for('groups.list_groups'))
