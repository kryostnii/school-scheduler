"""Утилиты для работы с БД — унифицированный доступ к пути файлу SQLite."""
from __future__ import annotations

import pathlib
from sqlalchemy.engine import Engine


def find_db_path(engine: Engine) -> str:
    """Извлечь путь к файлу SQLite из URL SQLAlchemy engine."""
    url_str = str(engine.url)
    if url_str.startswith("sqlite:///"):
        return str(pathlib.Path(url_str[len("sqlite:///"):]))
    return "school.sqlite3"
