"""Точка входа приложения School Scheduler."""
import os
import sys
import shutil
import sqlite3
import pathlib
import platform

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QFontDatabase

from app.data.models import make_engine
from app.ui.main_window import MainWindow

_APP_DIR = pathlib.Path(__file__).resolve().parent
_SCHEMA_PATH = _APP_DIR.parent / "db" / "schema.sql"
_DEFAULT_DB = _APP_DIR.parent / "school.sqlite3"


def _is_writable(directory: pathlib.Path) -> bool:
    try:
        directory.mkdir(parents=True, exist_ok=True)
        probe = directory / ".school_write_probe"
        probe.write_bytes(b"ok")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def resolve_db_path() -> str:
    """Вернуть путь к файлу БД.

    В dev-окружении БД лежит рядом с пакетом. В AppImage каталог пакета
    доступен только на чтение, поэтому используем XDG-каталог данных
    пользователя (с копией schema.sql для инициализации).
    """
    if _is_writable(_APP_DIR.parent):
        return str(_DEFAULT_DB)
    data_dir = pathlib.Path(
        os.environ.get("XDG_DATA_HOME", pathlib.Path.home() / ".local" / "share")
    ) / "school-scheduler"
    data_dir.mkdir(parents=True, exist_ok=True)
    schema_copy = data_dir / "schema.sql"
    if not schema_copy.exists():
        shutil.copy2(_SCHEMA_PATH, schema_copy)
    return str(data_dir / "school.sqlite3")


def init_db():
    from app.services.seed_sample_school import seed as seed_school

    db_path = resolve_db_path()
    schema_path = _SCHEMA_PATH if (_is_writable(_APP_DIR.parent)) else (
        pathlib.Path(db_path).parent / "schema.sql"
    )
    exists = pathlib.Path(db_path).exists()
    conn = sqlite3.connect(db_path)
    if not exists:
        with open(schema_path, encoding="utf-8") as f:
            conn.executescript(f.read())
        seed_school(conn)
    _migrate(conn)
    conn.close()
    return db_path


def _migrate(conn):
    cols = {row[1] for row in conn.execute("PRAGMA table_info(class_subjects)").fetchall()}
    if "profile_id" not in cols:
        conn.execute("ALTER TABLE class_subjects ADD COLUMN profile_id INTEGER")
        conn.commit()


def _get_system_font():
    system = platform.system()
    if system == "Windows":
        return "Segoe UI"
    elif system == "Darwin":
        return "SF Pro Display"
    else:
        families = QFontDatabase.families()
        for candidate in ["Noto Sans", "DejaVu Sans", "Liberation Sans", "Ubuntu", "sans-serif"]:
            if candidate in families:
                return candidate
        return "sans-serif"


def main():
    db_path = init_db()
    engine = make_engine(f"sqlite:///{pathlib.Path(db_path).as_posix()}")

    app = QApplication(sys.argv)
    app.setApplicationName("School Scheduler")
    app.setStyle("Fusion")

    from app.styles import SGLOBAL_STYLE

    font = QFont(_get_system_font(), 10)
    app.setFont(font)
    app.setStyleSheet(SGLOBAL_STYLE)

    window = MainWindow(engine)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
