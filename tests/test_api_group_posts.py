import os
from reddit_manager import create_app
from reddit_manager.services.group_service import GroupService
from reddit_manager.services.reddit_service import RedditService
from reddit_manager.utils.db import init_db
from reddit_manager.config.settings import Settings


def test_create_post_in_group_uses_subreddit_attributes(monkeypatch):
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    db_path = "/tmp/api.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    os.environ["DATABASE_PATH"] = db_path
    flask_app = create_app("testing")
    import api_main
    flask_app.config.update(TESTING=True, DATABASE_PATH=os.environ["DATABASE_PATH"])
    with flask_app.app_context():
        init_db(flask_app)
        gm = GroupService(Settings())
        gid = gm.create_group('MyGroup', '', [
            {'subreddit': 'python', 'flair_id': 'flair1'},
            {'subreddit': 'learnpython'}
        ])

        monkeypatch.setattr(api_main, 'group_service', gm)

        class DummyRedditService:
            def post_to_subreddit(self, subreddit_name, title, body, flair_id=None):
                return f'id-{subreddit_name}'

            def post_link_to_subreddit(self, subreddit_name, title, url, flair_id=None):
                return f'id-{subreddit_name}'

        monkeypatch.setattr(api_main, 'reddit_service', DummyRedditService())

        result = api_main.create_post_in_group(gid, {'title': 'T', 'body': 'B'}, auth_key='testkey')
        subreddits = [r['subreddit'] for r in result['results']]
        assert set(subreddits) == {'python', 'learnpython'}
        url_map = {r['subreddit']: r['post_url'] for r in result['results']}
        assert url_map['python'] == 'https://www.reddit.com/r/python/comments/id-python'


def test_create_post_with_env_auth_key(monkeypatch, tmp_path):
    monkeypatch.setenv('AUTH_KEY', 'envsecret')
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///:memory:')
    db_path = tmp_path / 'api.db'
    monkeypatch.setenv('DATABASE_PATH', str(db_path))
    flask_app = create_app('testing')
    import api_main
    flask_app.config.update(TESTING=True, DATABASE_PATH=str(db_path))
    with flask_app.app_context():
        init_db(flask_app)
        gm = GroupService(Settings())
        gid = gm.create_group('EnvGroup', '', [{'subreddit': 'python'}])

        monkeypatch.setattr(api_main, 'group_service', gm)

        class DummyRedditService:
            def post_to_subreddit(self, subreddit_name, title, body, flair_id=None):
                return f'id-{subreddit_name}'

            def post_link_to_subreddit(self, subreddit_name, title, url, flair_id=None):
                return f'id-{subreddit_name}'

        monkeypatch.setattr(api_main, 'reddit_service', DummyRedditService())

        result = api_main.create_post_in_group(gid, {'title': 'T', 'body': 'B'}, auth_key='envsecret')
        assert result['results'][0]['success']

