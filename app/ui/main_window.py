"""Главное окно приложения с боковой навигацией и QStackedWidget."""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QPushButton, QLabel, QFrame, QFileDialog, QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut

from app.ui.pages.data_page import DataPage
from app.ui.pages.generation_page import GenerationPage
from app.ui.pages.timetable_page import TimetablePage
from app.ui.pages.settings_page import SettingsPage

PAGE_DATA = 0
PAGE_GENERATE = 1
PAGE_TIMETABLE = 2
PAGE_SETTINGS = 3


class MainWindow(QMainWindow):
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.setWindowTitle("School Scheduler")
        self.setMinimumSize(1100, 700)
        self._setup_ui()
        self._setup_shortcuts()
        self._navigate(PAGE_DATA)
        self._update_status_bar()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setFixedWidth(220)
        sidebar.setObjectName("sidebar")
        sidebar.setStyleSheet("""
            QFrame#sidebar {
                background-color: #2c3e50;
                border-right: 1px solid #1a252f;
            }
            QPushButton {
                color: #bdc3c7;
                border: none;
                text-align: left;
                padding: 14px 20px;
                font-size: 13px;
                border-radius: 0px;
            }
            QPushButton:hover {
                background-color: #34495e;
                color: white;
            }
            QPushButton[active="true"] {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                border-left: 3px solid #fff;
            }
            QLabel#sidebar-hint {
                color: #7f8c8d;
                font-size: 10px;
                padding: 8px 12px;
            }
            QLabel#sidebar-footer {
                color: #5d6d7e;
                font-size: 10px;
                padding: 8px 12px;
                border-top: 1px solid #1a252f;
            }
        """)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        logo = QLabel("  🗓  School Scheduler")
        logo.setStyleSheet(
            "color: white; font-size: 15px; font-weight: bold; "
            "padding: 20px 10px; background: #1a252f; letter-spacing: 0.5px;"
        )
        logo.setFixedHeight(60)
        sidebar_layout.addWidget(logo)

        year_label = QLabel("  2026/2027 учебный год")
        year_label.setStyleSheet(
            "color: #5d6d7e; font-size: 11px; padding: 8px 12px; "
            "font-style: italic;"
        )
        sidebar_layout.addWidget(year_label)

        sep0 = QFrame()
        sep0.setFrameShape(QFrame.HLine)
        sep0.setStyleSheet("color: #1a252f;")
        sidebar_layout.addWidget(sep0)

        nav_items = [
            (PAGE_DATA,      "▦  1. Данные",      "Учителя, классы, предметы, кабинеты"),
            (PAGE_GENERATE,  "⚙  2. Генерация",   "Настройка и запуск алгоритма"),
            (PAGE_TIMETABLE, "⊞  3. Расписание",  "Просмотр и редактирование"),
            (PAGE_SETTINGS,  "☷  4. Настройки",   "Санитарные нормы"),
        ]

        self._nav_buttons = {}
        for idx, label, tooltip in nav_items:
            btn = QPushButton(f"  {label}")
            btn.setToolTip(tooltip)
            btn.setProperty("active", False)
            btn.clicked.connect(lambda checked, i=idx: self._navigate(i))
            sidebar_layout.addWidget(btn)
            self._nav_buttons[idx] = btn

        sidebar_layout.addSpacing(10)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #1a252f;")
        sidebar_layout.addWidget(sep)

        sidebar_layout.addStretch()

        open_btn = QPushButton("  ⤓  Открыть БД...")
        open_btn.setToolTip("Открыть другой файл базы данных (.sqlite3)")
        open_btn.clicked.connect(self._open_db)
        sidebar_layout.addWidget(open_btn)

        hint = QLabel("  Ctrl+1..4 — переключение")
        hint.setObjectName("sidebar-hint")
        sidebar_layout.addWidget(hint)

        footer = QLabel("School Scheduler v0.1.0")
        footer.setObjectName("sidebar-footer")
        sidebar_layout.addWidget(footer)

        layout.addWidget(sidebar)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet("QStackedWidget { background-color: #f5f6fa; }")

        self.data_page = DataPage(self.engine)
        self.generation_page = GenerationPage(self.engine)
        self.timetable_page = TimetablePage(self.engine)
        self.settings_page = SettingsPage(self.engine)

        self.stack.addWidget(self.data_page)
        self.stack.addWidget(self.generation_page)
        self.stack.addWidget(self.timetable_page)
        self.stack.addWidget(self.settings_page)

        layout.addWidget(self.stack)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+1"), self, lambda: self._navigate(PAGE_DATA))
        QShortcut(QKeySequence("Ctrl+2"), self, lambda: self._navigate(PAGE_GENERATE))
        QShortcut(QKeySequence("Ctrl+3"), self, lambda: self._navigate(PAGE_TIMETABLE))
        QShortcut(QKeySequence("Ctrl+4"), self, lambda: self._navigate(PAGE_SETTINGS))
        QShortcut(QKeySequence("Ctrl+O"), self, self._open_db)
        QShortcut(QKeySequence("Ctrl+Z"), self, self._undo_timetable)

    def _undo_timetable(self):
        if self.stack.currentIndex() == PAGE_TIMETABLE:
            self.timetable_page._undo()

    def _update_status_bar(self):
        import pathlib
        from app.services.db_utils import find_db_path
        db_name = pathlib.Path(find_db_path(self.engine)).name
        self.statusBar().showMessage(f"БД: {db_name}", 0)
        self.statusBar().setStyleSheet(
            "QStatusBar { background: #ffffff; color: #7f8c8d; font-size: 11px; "
            "border-top: 1px solid #d5d8dc; }"
        )

    def _navigate(self, index):
        self.stack.setCurrentIndex(index)
        for i, btn in self._nav_buttons.items():
            btn.setProperty("active", i == index)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        if index == PAGE_TIMETABLE:
            self.timetable_page.refresh()
        elif index == PAGE_DATA:
            self.data_page.refresh()

    def _open_db(self):
        import pathlib
        path, _ = QFileDialog.getOpenFileName(
            self, "Открыть базу данных", "",
            "SQLite (*.sqlite3);;Все файлы (*)"
        )
        if not path:
            return
        from app.data.models import make_engine
        self.engine = make_engine(f"sqlite:///{pathlib.Path(path).as_posix()}")

        self.data_page.engine = self.engine
        self.generation_page.engine = self.engine
        self.timetable_page.engine = self.engine
        self.settings_page.engine = self.engine

        self._navigate(PAGE_DATA)
        self.data_page.refresh()
        self._update_status_bar()
