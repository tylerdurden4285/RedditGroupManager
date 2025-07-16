import datetime
from reddit_manager.web.posts_create import _parse_schedule_time


def test_parse_schedule_time_with_space(app):
    with app.app_context():
        tz = app.group_manager.timezone
        app.config["DEFAULT_SCHED_TIME"] = "08:00"
        dt = _parse_schedule_time("2025-07-15 20:55")
        assert dt == datetime.datetime(2025, 7, 15, 20, 55, tzinfo=tz)


def test_parse_schedule_time_date_only(app):
    with app.app_context():
        tz = app.group_manager.timezone
        app.config["DEFAULT_SCHED_TIME"] = "08:00"
        dt = _parse_schedule_time("2025-07-15")
        assert dt == datetime.datetime(2025, 7, 15, 8, 0, tzinfo=tz)
