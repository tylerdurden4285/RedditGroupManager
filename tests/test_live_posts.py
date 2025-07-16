import os
import io
from pathlib import Path
import pytest
from flask import url_for

pytestmark = pytest.mark.live


_required_env = [
    'REDDIT_CLIENT_ID',
    'REDDIT_CLIENT_SECRET',
    'REDDIT_USER_AGENT',
    'REDDIT_USERNAME',
    'REDDIT_PASSWORD',
]
if any(not os.getenv(v) or os.getenv(v) == 'dummy' for v in _required_env):
    pytest.skip('Real Reddit credentials not configured', allow_module_level=True)


def _get_live_group(group_manager):
    """Retrieve the 'live-test' group using available API."""
    if hasattr(group_manager, 'get_group_by_name'):
        return group_manager.get_group_by_name('live-test')
    for grp in group_manager.list_groups():
        if getattr(grp, 'name', '') == 'live-test':
            return grp
    return None


def test_text_post(app, group_manager):
    with app.app_context():
        group = _get_live_group(group_manager)
        if not group or not getattr(group, 'subreddits', []):
            pytest.skip('live-test group not configured')

        client = app.test_client()
        for sub in group.subreddits:
            data = {
                'title': 'test title',
                'text_content': 'test body content',
                'flair_id': '',
                'selected_subreddit': sub.subreddit,
                'comment_text': 'test comment',
                'campaign': 'camp'
            }
            resp = client.post('/posts/create/text', data=data)
            assert resp.status_code == 302
            with app.test_request_context():
                assert resp.headers['Location'].endswith(url_for('posts_history.post_history'))

        posts = group_manager.get_recent_posts()
        for sub in group.subreddits:
            assert any(
                p['subreddit'] == sub.subreddit and
                p['post_type'] == 'text' and
                p['title'] == 'test title' and
                p['comment'] == 'test comment'
                for p in posts
            )


def test_link_post(app, group_manager):
    with app.app_context():
        group = _get_live_group(group_manager)
        if not group or not getattr(group, 'subreddits', []):
            pytest.skip('live-test group not configured')

        link_path = Path(__file__).parent / 'data' / 'link.txt'
        link_url = link_path.read_text().strip()

        client = app.test_client()
        data = {
            'title': 'test title',
            'link_url': link_url,
            'group_id': str(group.id),
            'comment': 'test comment',
            'campaign': 'camp'
        }
        resp = client.post('/posts/create/link', data=data)
        assert resp.status_code == 302
        with app.test_request_context():
            assert resp.headers['Location'].endswith(url_for('posts_history.post_history'))

        posts = group_manager.get_recent_posts()
        for sub in group.subreddits:
            assert any(
                p['subreddit'] == sub.subreddit and
                p['post_type'] == 'link' and
                p['title'] == 'test title' and
                p['comment'] == 'test comment'
                for p in posts
            )


def test_image_post(app, group_manager):
    with app.app_context():
        group = _get_live_group(group_manager)
        if not group or not getattr(group, 'subreddits', []):
            pytest.skip('live-test group not configured')

        img_path = Path(__file__).parent / 'data' / 'test.jpg'
        client = app.test_client()
        with open(img_path, 'rb') as f:
            data = {
                'title': 'test title',
                'text_content': 'test comment',
                'flair_id': '',
                'group_id': str(group.id),
                'image_file': (io.BytesIO(f.read()), 'test.jpg'),
                'campaign': 'camp'
            }
            resp = client.post('/posts/create/image', data=data, content_type='multipart/form-data')
        assert resp.status_code == 302
        with app.test_request_context():
            assert resp.headers['Location'].endswith(url_for('posts_history.post_history'))

        posts = group_manager.get_recent_posts()
        for sub in group.subreddits:
            assert any(
                p['subreddit'] == sub.subreddit and
                p['post_type'] == 'image' and
                p['title'] == 'test title' and
                p['comment'] == 'test comment'
                for p in posts
            )
