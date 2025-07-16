from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, HiddenField
from wtforms.validators import DataRequired, Length


class GroupForm(FlaskForm):
    """Form for creating and editing groups."""
    name = StringField('Group Name', validators=[
        DataRequired(message="Group name is required"),
        Length(min=1, max=100, message="Group name must be between 1 and 100 characters")
    ])
    description = TextAreaField('Description', validators=[
        Length(max=500, message="Description cannot exceed 500 characters")
    ])
    subreddits = HiddenField('Subreddits')
    
    
    errors = HiddenField('Errors')
