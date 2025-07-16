import os
import time
from flask import Flask
from reddit_manager.tasks.post_tasks import cleanup_temp_files
from reddit_manager.utils.db import init_db
from reddit_manager.services.group_service import GroupService
from reddit_manager.config.settings import Settings


def test_cleanup_temp_files_removes_old(tmp_path):
    instance = tmp_path / "inst"
    app = Flask("test", instance_path=str(instance))
    app.config["DATABASE_PATH"] = str(tmp_path / "db.db")
    with app.app_context():
        init_db(app)
        gm = GroupService(Settings())
        app.group_manager = gm
        temp_dir = instance / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        fpath = temp_dir / "old.txt"
        fpath.write_text("x")
        old = time.time() - 3600
        os.utime(fpath, (old, old))
        os.environ["TEMP_FILE_MAX_AGE_HOURS"] = "0"
        removed = cleanup_temp_files()
        assert removed == 1
        assert not fpath.exists()
