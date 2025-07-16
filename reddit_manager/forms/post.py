from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import (
    StringField,
    TextAreaField,
    SelectField,
    HiddenField,
    RadioField,
    DateTimeLocalField,
)
from wtforms.validators import DataRequired, Length, URL, Optional


class PostForm(FlaskForm):
    """Form for creating Reddit posts."""

    campaign = StringField("Campaign", validators=[DataRequired()])
    title = StringField(
        "Post Title",
        validators=[
            DataRequired(message="Post title is required"),
            Length(
                min=1, max=300, message="Title must be between 1 and 300 characters"
            ),
        ],
    )

    content_type = RadioField(
        "Content Type",
        choices=[("text", "Text Post"), ("link", "Link Post")],
        default="text",
    )

    text_content = TextAreaField(
        "Post Content",
        validators=[
            Optional(),
            Length(max=40000, message="Post content cannot exceed 40,000 characters"),
        ],
    )

    link_url = StringField(
        "Link URL", validators=[Optional(), URL(message="Please enter a valid URL")]
    )

    group_id = SelectField("Post to Group", validators=[Optional()], coerce=int)

    subreddit = StringField("Subreddit", validators=[Optional()])

    flair_id = HiddenField("Flair ID")

    schedule_time = DateTimeLocalField(
        "Schedule Time", format="%Y-%m-%dT%H:%M", validators=[Optional()]
    )

    errors = HiddenField("Errors")


class TextPostForm(FlaskForm):
    """Simplified form for creating text posts."""

    campaign = StringField("Campaign", validators=[DataRequired()])
    title = StringField(
        "Post Title",
        validators=[
            DataRequired(message="Post title is required"),
            Length(
                min=1, max=300, message="Title must be between 1 and 300 characters"
            ),
        ],
    )

    text_content = TextAreaField(
        "Post Content",
        validators=[
            Optional(),
            Length(max=40000, message="Post content cannot exceed 40,000 characters"),
        ],
    )

    flair_id = HiddenField("Flair ID")

    schedule_time = DateTimeLocalField(
        "Schedule Time", format="%Y-%m-%dT%H:%M", validators=[Optional()]
    )


class LinkPostForm(FlaskForm):
    """Form for creating Link posts."""

    campaign = StringField("Campaign", validators=[DataRequired()])
    title = StringField(
        "Post Title",
        validators=[
            DataRequired(message="Post title is required"),
            Length(
                min=1, max=300, message="Title must be between 1 and 300 characters"
            ),
        ],
    )

    link_url = StringField(
        "Link URL",
        validators=[
            DataRequired(message="URL is required"),
            URL(message="Please enter a valid URL"),
        ],
    )

    flair_id = HiddenField("Flair ID")

    schedule_time = DateTimeLocalField(
        "Schedule Time", format="%Y-%m-%dT%H:%M", validators=[Optional()]
    )


class ImagePostForm(FlaskForm):
    """Form for creating image posts."""

    campaign = StringField("Campaign", validators=[DataRequired()])
    title = StringField(
        "Post Title",
        validators=[
            DataRequired(message="Post title is required"),
            Length(
                min=1, max=300, message="Title must be between 1 and 300 characters"
            ),
        ],
    )

    image_file = FileField(
        "Image File",
        validators=[
            FileRequired(message="Please select an image file"),
            FileAllowed(
                ["jpg", "jpeg", "png", "gif"],
                message="Only JPG, PNG, and GIF files are allowed",
            ),
        ],
    )

    text_content = TextAreaField(
        "Caption (Optional)",
        validators=[
            Optional(),
            Length(max=1000, message="Caption cannot exceed 1,000 characters"),
        ],
    )

    flair_id = HiddenField("Flair ID")

    schedule_time = DateTimeLocalField(
        "Schedule Time", format="%Y-%m-%dT%H:%M", validators=[Optional()]
    )
