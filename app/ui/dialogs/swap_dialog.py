"""Диалог выбора ячейки для обмена между классами."""
import sqlite3
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView,
    QMessageBox, QComboBox, QWidget, QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from app.config import MAX_LESSONS, DAY_NAMES_RU as _DAY_NAMES

DAY_NAMES = list(_DAY_NAMES)
DAY_IDS = {"Пн": 1, "Вт": 2, "Ср": 3, "Чт": 4, "Пт": 5, "Сб": 6}


class SwapDialog(QDialog):
    def __init__(self, engine, src_day, src_lesson, src_cell_text,
                 src_teacher, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.src_day = src_day
        self.src_lesson = src_lesson
        self.selected_target = None

        import pathlib
        db_path = str(self.engine.url)
        if db_path.startswith("sqlite:///"):
            db_path = str(pathlib.Path(db_path[len("sqlite:///"):]))
        self._db_path = db_path

        self.setWindowTitle("Обмен уроков между классами")
        self.setMinimumSize(750, 520)
        self._setup_ui(src_cell_text, src_teacher)
        self._load_entries()

    def _setup_ui(self, src_cell_text, src_teacher):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        src_frame = QFrame()
        src_frame.setStyleSheet(
            "QFrame { background: #fef9e7; border: 1px solid #f0e68c; border-radius: 8px; padding: 10px; }"
        )
        src_layout = QVBoxLayout(src_frame)
        src_title = QLabel("Исходный урок")
        src_title.setStyleSheet("font-size: 12px; color: #7f8c8d; font-weight: bold;")
        src_layout.addWidget(src_title)
        src_info = QLabel(
            f"{DAY_NAMES[self.src_day]}, урок {self.src_lesson}  —  "
            f"{src_cell_text}  ({src_teacher})"
        )
        src_info.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50;")
        src_layout.addWidget(src_info)
        layout.addWidget(src_frame)

        hint = QLabel(
            "Выберите день и урок для обмена, затем нажмите на строку:"
        )
        hint.setStyleSheet("font-size: 12px; color: #7f8c8d;")
        layout.addWidget(hint)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(10)

        lbl_day = QLabel("День:")
        lbl_day.setStyleSheet("font-size: 12px; color: #555; font-weight: bold;")
        filter_row.addWidget(lbl_day)
        self.day_combo = QComboBox()
        self.day_combo.setFixedWidth(100)
        self.day_combo.setStyleSheet(
            "QComboBox { padding: 6px 10px; font-size: 12px; border: 1px solid #bdc3c7; border-radius: 4px; }"
        )
        for d_id in range(1, 7):
            self.day_combo.addItem(DAY_NAMES[d_id], d_id)
        idx = self.src_day - 1
        if 0 <= idx < self.day_combo.count():
            self.day_combo.setCurrentIndex(idx)
        self.day_combo.currentIndexChanged.connect(self._load_entries)
        filter_row.addWidget(self.day_combo)

        lbl_lesson = QLabel("Урок:")
        lbl_lesson.setStyleSheet("font-size: 12px; color: #555; font-weight: bold;")
        filter_row.addWidget(lbl_lesson)
        self.lesson_combo = QComboBox()
        self.lesson_combo.setFixedWidth(80)
        self.lesson_combo.setStyleSheet(
            "QComboBox { padding: 6px 10px; font-size: 12px; border: 1px solid #bdc3c7; border-radius: 4px; }"
        )
        for l in range(1, MAX_LESSONS + 1):
            self.lesson_combo.addItem(str(l), l)
        lidx = self.src_lesson - 1
        if 0 <= lidx < self.lesson_combo.count():
            self.lesson_combo.setCurrentIndex(lidx)
        self.lesson_combo.currentIndexChanged.connect(self._load_entries)
        filter_row.addWidget(self.lesson_combo)

        filter_row.addStretch()
        layout.addLayout(filter_row)

        self.table = QTableWidget()
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setShowGrid(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setDefaultSectionSize(48)
        self.table.setStyleSheet(
            "QTableWidget { background: white; gridline-color: #e5e8e8; }"
            "QTableWidget::item:selected { background-color: #eaf2f8; color: #2c3e50; }"
            "QHeaderView::section { background: #f8f9fa; color: #2c3e50; "
            "border: none; border-bottom: 2px solid #2c3e50; padding: 6px; "
            "font-weight: bold; font-size: 12px; }"
        )
        self.table.cellDoubleClicked.connect(self._on_accept)
        layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setStyleSheet(
            "QPushButton { padding: 8px 20px; border: 1px solid #bdc3c7; "
            "border-radius: 6px; background: white; font-size: 13px; }"
            "QPushButton:hover { background: #f2f3f4; }"
        )
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        self.swap_btn = QPushButton("Поменять местами")
        self.swap_btn.setStyleSheet(
            "QPushButton { padding: 8px 24px; background: #e67e22; color: white; "
            "border: none; border-radius: 6px; font-size: 13px; font-weight: bold; }"
            "QPushButton:hover { background: #d35400; }"
            "QPushButton:disabled { background: #bdc3c7; }"
        )
        self.swap_btn.setEnabled(False)
        self.swap_btn.clicked.connect(self._on_accept)
        btn_row.addWidget(self.swap_btn)

        layout.addLayout(btn_row)
        self.table.itemSelectionChanged.connect(self._on_selection)

    def _load_entries(self):
        target_day = self.day_combo.currentData()
        target_lesson = self.lesson_combo.currentData()
        if not target_day or not target_lesson:
            return

        conn = sqlite3.connect(self._db_path)
        try:
            rows = conn.execute("""
                SELECT te.day_of_week, te.lesson_number,
                       s.name, t.full_name,
                       c2.number, sg.group_number, cs.is_split,
                       c.grade, c.letter, c.id,
                       te.id, te.subject_group_id
                FROM timetable_entries te
                JOIN subject_groups sg ON sg.id = te.subject_group_id
                JOIN class_subjects cs ON cs.id = sg.class_subject_id
                JOIN classes c ON c.id = cs.class_id
                JOIN subjects s ON s.id = cs.subject_id
                JOIN teachers t ON t.id = sg.teacher_id
                LEFT JOIN cabinets c2 ON c2.id = te.cabinet_id
                WHERE te.day_of_week = ? AND te.lesson_number = ?
                ORDER BY c.grade, c.letter
            """, (target_day, target_lesson)).fetchall()
        finally:
            conn.close()

        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["Класс", "Предмет", "Учитель", "Кабинет", "Подгруппа"]
        )
        self.table.setRowCount(len(rows))
        self._row_data = []

        for i, r in enumerate(rows):
            class_label = f"{r[7]}{r[8]}"
            group_text = f"гр.{r[5]}" if r[6] else "—"
            self._row_data.append({
                "class_label": class_label,
                "class_grade": r[7],
                "class_letter": r[8],
                "class_id": r[9],
                "subject_name": r[2],
                "teacher_name": r[3],
                "cabinet": r[4] or "",
                "group_number": r[5],
                "is_split": r[6],
                "entry_id": r[10],
                "subject_group_id": r[11],
                "target_day": target_day,
                "target_lesson": target_lesson,
            })

            values = [class_label, r[2], r[3], r[4] or "", group_text]
            for j, val in enumerate(values):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(i, j, item)

        self.table.resizeColumnsToContents()

    def _on_selection(self):
        rows = self.table.selectionModel().selectedRows()
        self.swap_btn.setEnabled(len(rows) > 0)

    def _on_accept(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        idx = rows[0].row()
        if idx < len(self._row_data):
            self.selected_target = self._row_data[idx]
            self.accept()
