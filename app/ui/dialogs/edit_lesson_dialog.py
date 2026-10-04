"""Диалог редактирования урока в расписании."""
import sqlite3
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QSpinBox, QFrame, QMessageBox,
)
from PySide6.QtCore import Qt

from app.config import MAX_LESSONS, DAY_NAMES_RU as _DAY_NAMES
from app.services.db_utils import find_db_path

DAY_NAMES = list(_DAY_NAMES)


class EditLessonDialog(QDialog):
    def __init__(self, engine, day, lesson, cell, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.day = day
        self.lesson = lesson
        self.cell = cell
        self._db_path = find_db_path(engine)

        self.setWindowTitle(f"Редактирование: {DAY_NAMES[day]}, ур. {lesson}")
        self.setMinimumWidth(420)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        info_frame = QFrame()
        info_frame.setStyleSheet(
            "QFrame { background: #eaf2f8; border: 1px solid #aed6f1; "
            "border-radius: 6px; padding: 10px; }"
        )
        info_layout = QVBoxLayout(info_frame)
        info_title = QLabel("Текущий урок")
        info_title.setStyleSheet("font-size: 11px; color: #7f8c8d; font-weight: bold;")
        info_layout.addWidget(info_title)
        info_text = QLabel(
            f"{self.cell.subject_name}\n"
            f"Учитель: {self.cell.teacher_name}\n"
            f"Кабинет: {self.cell.cabinet or '—'}\n"
            f"Класс: {self.cell.class_label or '—'}"
        )
        info_text.setStyleSheet("font-size: 13px; color: #2c3e50;")
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)
        layout.addWidget(info_frame)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #d5d8dc;")
        layout.addWidget(sep)

        move_label = QLabel("Переместить урок:")
        move_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(move_label)

        target_row = QHBoxLayout()
        target_row.setSpacing(10)

        day_label = QLabel("День:")
        day_label.setStyleSheet("font-size: 12px; color: #555;")
        target_row.addWidget(day_label)
        self.day_combo = QComboBox()
        self.day_combo.setFixedWidth(100)
        for d in range(1, 7):
            self.day_combo.addItem(DAY_NAMES[d], d)
        idx = self.day - 1
        if 0 <= idx < self.day_combo.count():
            self.day_combo.setCurrentIndex(idx)
        target_row.addWidget(self.day_combo)

        lesson_label = QLabel("Урок:")
        lesson_label.setStyleSheet("font-size: 12px; color: #555;")
        target_row.addWidget(lesson_label)
        self.lesson_spin = QSpinBox()
        self.lesson_spin.setRange(1, MAX_LESSONS)
        self.lesson_spin.setValue(self.lesson)
        self.lesson_spin.setFixedWidth(60)
        target_row.addWidget(self.lesson_spin)

        target_row.addStretch()
        layout.addLayout(target_row)

        layout.addStretch()

        btn_row = QHBoxLayout()
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setStyleSheet(
            "QPushButton { padding: 8px 20px; border: 1px solid #bdc3c7; "
            "border-radius: 6px; background: white; font-size: 13px; }"
            "QPushButton:hover { background: #f2f3f4; }"
        )
        cancel_btn.clicked.connect(self.reject)
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)

        move_btn = QPushButton("Переместить")
        move_btn.setStyleSheet(
            "QPushButton { padding: 8px 24px; background: #27ae60; color: white; "
            "border: none; border-radius: 6px; font-size: 13px; font-weight: bold; }"
            "QPushButton:hover { background: #2ecc71; }"
        )
        move_btn.clicked.connect(self._on_move)
        btn_row.addWidget(move_btn)

        layout.addLayout(btn_row)

    def _on_move(self):
        new_day = self.day_combo.currentData()
        new_lesson = self.lesson_spin.value()

        if new_day == self.day and new_lesson == self.lesson:
            QMessageBox.information(self, "Без изменений", "День и урок не изменились.")
            return

        conn = sqlite3.connect(self._db_path)
        try:
            src_entries = conn.execute(
                """SELECT te.id, te.subject_group_id, sg.teacher_id, te.cabinet_id
                   FROM timetable_entries te
                   JOIN subject_groups sg ON sg.id = te.subject_group_id
                   WHERE te.day_of_week=? AND te.lesson_number=?""",
                (self.day, self.lesson)
            ).fetchall()

            if not src_entries:
                QMessageBox.information(self, "Нет данных",
                    "В этом слоте нет записей для перемещения.")
                return

            _, sg_id, my_teacher, my_cabinet = src_entries[0]
            src_sg_ids = {sg for _, sg, _, _ in src_entries}

            existing = conn.execute(
                """SELECT te.subject_group_id, sg.teacher_id, te.cabinet_id
                   FROM timetable_entries te
                   JOIN subject_groups sg ON sg.id = te.subject_group_id
                   WHERE te.day_of_week=? AND te.lesson_number=?""",
                (new_day, new_lesson)
            ).fetchall()

            existing_sg_ids = {sg for sg, _, _ in existing}

            conflict = src_sg_ids & existing_sg_ids
            if conflict:
                QMessageBox.warning(
                    self, "Конфликт",
                    "Этот предмет уже есть в целевом слоте."
                )
                return

            for _, sg2, teacher2, cabinet2 in existing:
                if teacher2 == my_teacher:
                    QMessageBox.warning(
                        self, "Конфликт",
                        "В целевом слоте уже ведёт этот же учитель."
                    )
                    return
                if (my_cabinet is not None and my_cabinet != 0
                        and cabinet2 == my_cabinet):
                    QMessageBox.warning(
                        self, "Конфликт",
                        "В целевом слоте уже занят этот кабинет."
                    )
                    return

            for entry_id, *_ in src_entries:
                conn.execute(
                    "UPDATE timetable_entries SET day_of_week=?, lesson_number=? WHERE id=?",
                    (new_day, new_lesson, entry_id)
                )
            conn.commit()

            self.accept()

        except Exception as e:
            conn.rollback()
            QMessageBox.warning(self, "Ошибка", f"Не удалось переместить: {e}")
        finally:
            conn.close()
