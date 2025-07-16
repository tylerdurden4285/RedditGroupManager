#!/usr/bin/env python3
import os
from alembic.config import Config
from alembic import command

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def main() -> None:
    db_path = os.getenv("DATABASE_PATH", os.path.join(BASE_DIR, "instance", "app.db"))
    
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    alembic_cfg = Config(os.path.join(BASE_DIR, "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    command.upgrade(alembic_cfg, "head")


if __name__ == "__main__":
    main()
