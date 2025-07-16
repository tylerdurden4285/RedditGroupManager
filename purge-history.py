#!/usr/bin/env python3
import click
from reddit_manager.config.settings import Settings
from reddit_manager.services.reddit_service import RedditService

@click.command(help="Delete all submissions and comments for the configured Reddit user.")
def main():
    """Purge the authenticated user's entire Reddit history."""
    service = RedditService(Settings())
    user = service.reddit.user.me()

    comments = list(user.comments.new(limit=None))
    submissions = list(user.submissions.new(limit=None))

    total = len(comments) + len(submissions)

    if total == 0:
        click.echo("No items to delete.")
        return

    if not click.confirm(
        "This will permanently delete all your Reddit submissions and comments. Continue?"
    ):
        click.echo("Aborted.")
        return

    def describe(item):
        text = getattr(item, "body", None) or getattr(item, "title", "")
        text = text.replace("\n", " ") if isinstance(text, str) else ""
        if len(text) > 40:
            text = text[:37] + "..."
        type_name = "Comment" if hasattr(item, "body") else "Post"
        return type_name, text

    emoji = {"checking": "🔎", "deleting": "🗑️", "purged": "✅"}

    index = 0
    removed_comments = 0
    removed_posts = 0

    for comment in comments:
        index += 1
        type_name, desc = describe(comment)
        click.echo(f"{emoji['checking']} Checking: {type_name} - \"{desc}\" - {index}/{total}")
        click.echo(f"{emoji['deleting']} Deleting: {type_name} - \"{desc}\" - {index}/{total}")
        comment.delete()
        removed_comments += 1
        click.echo(f"{emoji['purged']} Purged: {type_name} - \"{desc}\" - {index}/{total}")

    for submission in submissions:
        index += 1
        type_name, desc = describe(submission)
        click.echo(f"{emoji['checking']} Checking: {type_name} - \"{desc}\" - {index}/{total}")
        click.echo(f"{emoji['deleting']} Deleting: {type_name} - \"{desc}\" - {index}/{total}")
        submission.delete()
        removed_posts += 1
        click.echo(f"{emoji['purged']} Purged: {type_name} - \"{desc}\" - {index}/{total}")

    click.echo(
        f"== FINISHED == {removed_comments} Comments and {removed_posts} Posts Removed"
    )

if __name__ == "__main__":
    main()
