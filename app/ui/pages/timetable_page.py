"""Страница просмотра и редактирования расписания."""
import sqlite3
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QFrame, QMessageBox, QButtonGroup, QStackedWidget,
)
from PySide6.QtCore import Qt

from sqlalchemy import select

from app.data.models import (
    AcademicYear, SchoolClass, Teacher, Cabinet, Subject,
    ClassSubject, make_session,
)
from app.config import DAY_NAMES_RU as DAY_NAMES
from app.services.db_utils import find_db_path
from app.ui.widgets.timetable_grid import TimetableGrid
from app.ui.widgets.assignment_matrix import AssignmentMatrix
from app.ui.dialogs.swap_dialog import SwapDialog

STYLE_BTN_ACTIVE = """
    QPushButton {{
        background-color: {color};
        color: white;
        border: none;
        border-radius: 6px;
        padding: 8px 14px;
        font-size: 12px;
        font-weight: bold;
        min-width: 50px;
    }}
"""
STYLE_BTN_INACTIVE = """
    QPushButton {
        background-color: #ecf0f1;
        color: #2c3e50;
        border: 1px solid #bdc3c7;
        border-radius: 6px;
        padding: 8px 14px;
        font-size: 12px;
        min-width: 50px;
    }
    QPushButton:hover {
        background-color: #d5dbdb;
        border-color: #95a5a6;
    }
"""
STYLE_TOGGLE_ON = """
    QPushButton {
        background-color: #e67e22;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 8px 16px;
        font-size: 12px;
        font-weight: bold;
    }
"""
STYLE_TOGGLE_OFF = """
    QPushButton {
        background-color: #3498db;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 8px 16px;
        font-size: 12px;
    }
    QPushButton:hover { background-color: #2980b9; }
"""
STYLE_CATEGORY_ACTIVE = """
    QPushButton {
        background-color: #2c3e50;
        color: white;
        border: none;
        border-radius: 0px;
        padding: 10px 20px;
        font-size: 13px;
        font-weight: bold;
    }
"""
STYLE_CATEGORY_INACTIVE = """
    QPushButton {
        background-color: #ecf0f1;
        color: #2c3e50;
        border: none;
        border-radius: 0px;
        padding: 10px 20px;
        font-size: 13px;
    }
    QPushButton:hover { background-color: #d5dbdb; }
"""


class TimetablePage(QWidget):
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self._edit_mode = False
        self._undo_stack = []
        self._current_filter = None
        self._subject_names = {}
        self._clipboard = None
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        toolbar = self._build_toolbar()
        main_layout.addWidget(toolbar)

        self._stack = QStackedWidget()

        self.empty_widget = self._build_empty_state()
        self._stack.addWidget(self.empty_widget)

        self.content_widget = QWidget()
        self._build_content(self.content_widget)
        self._stack.addWidget(self.content_widget)

        main_layout.addWidget(self._stack, stretch=1)

        self.grid.cell_clicked.connect(self._on_cell_clicked)
        self.grid.cell_dropped.connect(self._on_cell_dropped)
        self.grid.cell_copy.connect(self._on_cell_copy)
        self.grid.cell_delete.connect(self._on_cell_delete)
        self.grid.cell_edit.connect(self._on_cell_edit)
        self._set_category("classes")
        self._switch_view("timetable")

    def _build_empty_state(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignCenter)

        icon = QLabel("⏱")
        icon.setStyleSheet(
            "font-size: 56px; color: #d5d8dc;"
        )
        icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon)

        title = QLabel("Расписание ещё не создано")
        title.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #2c3e50; padding-top: 12px;"
        )
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        hint = QLabel(
            "Сначала создайте учебные планы на вкладке «Данные»,\n"
            "затем запустите генерацию на вкладке «Генерация»."
        )
        hint.setStyleSheet("font-size: 13px; color: #95a5a6; padding-top: 8px;")
        hint.setAlignment(Qt.AlignCenter)
        hint.setWordWrap(True)
        layout.addWidget(hint)

        go_btn = QPushButton("\u2190 Перейти к данным")
        go_btn.setStyleSheet(
            "QPushButton { padding: 10px 20px; background: #3498db; color: white; "
            "border: none; border-radius: 6px; font-size: 13px; font-weight: bold; "
            "margin-top: 16px; }"
            "QPushButton:hover { background: #2980b9; }"
        )
        go_btn.setFixedWidth(200)
        go_btn.setCursor(Qt.PointingHandCursor)
        go_btn.clicked.connect(lambda: self._navigate_to_data())
        layout.addWidget(go_btn, alignment=Qt.AlignCenter)

        layout.addStretch()
        return w

    def _navigate_to_data(self):
        window = self.window()
        if hasattr(window, '_navigate'):
            window._navigate(0)

    def _build_content(self, parent):
        body = QHBoxLayout(parent)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(16, 12, 16, 12)
        center_layout.setSpacing(8)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        self.filter_combo = QComboBox()
        self.filter_combo.setMinimumWidth(260)
        self.filter_combo.setStyleSheet("""
            QComboBox {
                padding: 8px 12px; font-size: 13px;
                border: 1px solid #bdc3c7; border-radius: 6px; background: white;
            }
            QComboBox::drop-down { border: none; width: 24px; }
        """)
        self.filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        top_row.addWidget(self.filter_combo)

        self.edit_btn = QPushButton("Режим редактирования")
        self.edit_btn.setStyleSheet(STYLE_TOGGLE_OFF)
        self.edit_btn.setCheckable(True)
        self.edit_btn.setToolTip(
            "Включите, чтобы менять расписание:\n"
            "  Перетащите урок на другой слот для обмена,\n"
            "  или выделите и нажмите «Поменять местами»"
        )
        self.edit_btn.toggled.connect(self._toggle_edit_mode)
        top_row.addWidget(self.edit_btn)

        self.undo_btn = QPushButton("\u21a9 Отменить")
        self.undo_btn.setStyleSheet(STYLE_BTN_INACTIVE)
        self.undo_btn.setEnabled(False)
        self.undo_btn.clicked.connect(self._undo)
        top_row.addWidget(self.undo_btn)

        refresh_btn = QPushButton("\U0001f504")
        refresh_btn.setFixedSize(36, 36)
        refresh_btn.setStyleSheet("""
            QPushButton { border: 1px solid #bdc3c7; border-radius: 6px; background: white; font-size: 16px; }
            QPushButton:hover { background: #eaf2f8; }
        """)
        refresh_btn.clicked.connect(self.refresh)
        top_row.addWidget(refresh_btn)
        top_row.addStretch()

        center_layout.addLayout(top_row)

        self.edit_hint = QLabel("")
        self.edit_hint.setStyleSheet(
            "color: #e67e22; font-size: 12px; font-style: italic; padding: 2px 0;"
        )
        self.edit_hint.setVisible(False)
        center_layout.addWidget(self.edit_hint)

        self.swap_hint = QLabel("")
        self.swap_hint.setStyleSheet(
            "color: #2980b9; font-size: 12px; font-style: italic; padding: 2px 0;"
        )
        self.swap_hint.setVisible(False)
        center_layout.addWidget(self.swap_hint)

        self._view_stack = QStackedWidget()

        timetable_container = QWidget()
        tc_layout = QVBoxLayout(timetable_container)
        tc_layout.setContentsMargins(0, 0, 0, 0)
        tc_layout.setSpacing(0)

        self.grid = TimetableGrid()
        tc_layout.addWidget(self.grid)

        self.legend_bar = self._build_legend()
        tc_layout.addWidget(self.legend_bar)

        self._view_stack.addWidget(timetable_container)

        self.assignment_matrix = AssignmentMatrix(self.engine)
        self.assignment_matrix.assignment_changed.connect(self._on_assignment_changed)
        self._view_stack.addWidget(self.assignment_matrix)

        self._view_stack.setCurrentIndex(0)
        center_layout.addWidget(self._view_stack, stretch=1)

        body.addWidget(center)

        self.info_panel = self._build_info_panel()
        self.info_panel.setFixedWidth(240)
        body.addWidget(self.info_panel)

    def _switch_view(self, view_key):
        for key, btn in self._view_buttons.items():
            if key == view_key:
                btn.setStyleSheet(self._view_style_active)
            else:
                btn.setStyleSheet(self._view_style_inactive)

        if view_key == "timetable":
            self._view_stack.setCurrentIndex(0)
            self.filter_combo.setVisible(True)
            self.edit_btn.setVisible(True)
            self.undo_btn.setVisible(True)
            self.edit_hint.setVisible(False)
            self.swap_hint.setVisible(False)
            self.info_panel.setVisible(True)
        else:
            self._view_stack.setCurrentIndex(1)
            self.filter_combo.setVisible(False)
            self.edit_btn.setVisible(False)
            self.undo_btn.setVisible(False)
            self.edit_hint.setVisible(False)
            self.swap_hint.setVisible(False)
            self.info_panel.setVisible(False)
            self.assignment_matrix.refresh()

    def _on_assignment_changed(self):
        self._rebuild_filter()

    def _build_toolbar(self):
        toolbar = QFrame()
        toolbar.setFixedHeight(50)
        toolbar.setStyleSheet("background-color: #2c3e50; border: none;")
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(16, 0, 16, 0)

        title = QLabel("Расписание")
        title.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        layout.addSpacing(20)

        self.view_toggle_group = QButtonGroup(self)
        self.view_toggle_group.setExclusive(True)
        self._view_buttons = {}

        STYLE_VIEW_ACTIVE = """
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: bold;
            }
        """
        STYLE_VIEW_INACTIVE = """
            QPushButton {
                background-color: transparent;
                color: #bdc3c7;
                border: 1px solid #7f8c8d;
                border-radius: 4px;
                padding: 6px 14px;
                font-size: 12px;
            }
            QPushButton:hover { color: white; border-color: white; }
        """

        for key, label in [("timetable", "Расписание"), ("assignments", "Назначения")]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setStyleSheet(STYLE_VIEW_INACTIVE)
            btn.clicked.connect(lambda checked, k=key: self._switch_view(k))
            self.view_toggle_group.addButton(btn)
            self._view_buttons[key] = btn
            layout.addWidget(btn)

        self._view_style_active = STYLE_VIEW_ACTIVE
        self._view_style_inactive = STYLE_VIEW_INACTIVE

        layout.addStretch()

        self.cat_btns = QButtonGroup(self)
        self.cat_btns.setExclusive(True)
        self._cat_buttons = {}

        for key, label in [("classes", "Классы"), ("teachers", "Учителя"), ("cabinets", "Кабинеты")]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setStyleSheet(STYLE_CATEGORY_INACTIVE)
            btn.clicked.connect(lambda checked, k=key: self._set_category(k))
            self.cat_btns.addButton(btn)
            self._cat_buttons[key] = btn
            layout.addWidget(btn)

        layout.addSpacing(20)

        shift_label = QLabel("Смена:")
        shift_label.setStyleSheet("color: #bdc3c7; font-size: 12px;")
        layout.addWidget(shift_label)
        self.shift_combo = QComboBox()
        self.shift_combo.setFixedWidth(120)
        self.shift_combo.setStyleSheet("""
            QComboBox { padding: 5px 8px; font-size: 12px; border: none; border-radius: 4px; background: #34495e; color: white; }
            QComboBox::drop-down { border: none; width: 20px; }
            QComboBox QAbstractItemView { background: #2c3e50; color: white; selection-background-color: #3498db; }
        """)
        self.shift_combo.addItem("Все", None)
        self.shift_combo.addItem("I смена", 1)
        self.shift_combo.addItem("II смена", 2)
        self.shift_combo.currentIndexChanged.connect(self._on_filter_changed)
        layout.addWidget(self.shift_combo)

        return toolbar

    def _build_info_panel(self):
        panel = QFrame()
        panel.setStyleSheet("background-color: #f8f9fa; border-left: 1px solid #d5d8dc;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(8)

        header = QLabel("Информация")
        header.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(header)

        self.info_title = QLabel("Выберите ячейку")
        self.info_title.setStyleSheet("font-size: 13px; color: #7f8c8d;")
        self.info_title.setWordWrap(True)
        layout.addWidget(self.info_title)

        self.info_subject = QLabel("")
        self.info_subject.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50;")
        self.info_subject.setWordWrap(True)
        layout.addWidget(self.info_subject)

        self.info_teacher = QLabel("")
        self.info_teacher.setStyleSheet("font-size: 12px; color: #555;")
        self.info_teacher.setWordWrap(True)
        layout.addWidget(self.info_teacher)

        self.info_cabinet = QLabel("")
        self.info_cabinet.setStyleSheet("font-size: 12px; color: #555;")
        layout.addWidget(self.info_cabinet)

        self.info_group = QLabel("")
        self.info_group.setStyleSheet("font-size: 12px; color: #555;")
        layout.addWidget(self.info_group)

        self.info_conflict = QLabel("")
        self.info_conflict.setStyleSheet("font-size: 13px; font-weight: bold; color: #e74c3c;")
        self.info_conflict.setWordWrap(True)
        layout.addWidget(self.info_conflict)

        self.swap_btn = QPushButton("Поменять местами с другим классом...")
        self.swap_btn.setStyleSheet(
            "QPushButton { padding: 8px 12px; background: #2980b9; color: white; "
            "border: none; border-radius: 6px; font-size: 12px; font-weight: bold; }"
            "QPushButton:hover { background: #2471a3; }"
            "QPushButton:disabled { background: #bdc3c7; }"
        )
        self.swap_btn.setEnabled(False)
        self.swap_btn.setToolTip(
            "Обмен урока с другим классом через диалог выбора.\n"
            "Работает из любого режима просмотра."
        )
        self.swap_btn.clicked.connect(self._open_swap_dialog)
        layout.addWidget(self.swap_btn)

        layout.addSpacing(16)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #d5d8dc;")
        layout.addWidget(sep)

        legend_title = QLabel("Цвета предметов")
        legend_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #7f8c8d;")
        layout.addWidget(legend_title)

        self.legend_container = QVBoxLayout()
        self.legend_container.setSpacing(4)
        layout.addLayout(self.legend_container)

        layout.addStretch()
        return panel

    def _build_legend(self):
        frame = QFrame()
        frame.setStyleSheet("background: #f8f9fa; border: 1px solid #e5e8e8; border-radius: 4px; padding: 4px;")
        self.legendFlowLayout = QHBoxLayout(frame)
        self.legendFlowLayout.setContentsMargins(8, 4, 8, 4)
        self.legendFlowLayout.setSpacing(12)
        lbl = QLabel("Предметы:")
        lbl.setStyleSheet("font-size: 11px; color: #7f8c8d; font-weight: bold;")
        self.legendFlowLayout.addWidget(lbl)
        self.legendFlowLayout.addStretch()
        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("font-size: 11px; color: #7f8c8d; font-weight: bold;")
        self.legendFlowLayout.addWidget(self.stats_label)
        return frame

    def _set_category(self, cat):
        for key, btn in self._cat_buttons.items():
            if key == cat:
                btn.setStyleSheet(STYLE_CATEGORY_ACTIVE)
            else:
                btn.setStyleSheet(STYLE_CATEGORY_INACTIVE)
        self._current_cat = cat
        self._rebuild_filter()

    def _rebuild_filter(self):
        self.filter_combo.blockSignals(True)
        prev = self.filter_combo.currentData()
        self.filter_combo.clear()

        shift_id = self.shift_combo.currentData()

        with make_session(self.engine) as session:
            year = session.execute(
                select(AcademicYear).where(AcademicYear.is_active == 1)
            ).scalar_one_or_none()
            if not year:
                self.filter_combo.blockSignals(False)
                self._show_empty()
                return

            if self._current_cat == "classes":
                q = select(SchoolClass).where(SchoolClass.academic_year_id == year.id)
                if shift_id:
                    q = q.where(SchoolClass.shift_id == shift_id)
                items = session.execute(q).scalars().all()
                for c in items:
                    self.filter_combo.addItem(
                        f"{c.grade}{c.letter} ({self._get_shift_name(session, c.shift_id)})",
                        ("class", c.id)
                    )

            elif self._current_cat == "teachers":
                q = select(Teacher)
                if shift_id:
                    q = q.where(Teacher.shift_id == shift_id)
                items = session.execute(q).scalars().all()
                for t in items:
                    self.filter_combo.addItem(t.full_name, ("teacher", t.id))

            elif self._current_cat == "cabinets":
                q = select(Cabinet)
                if shift_id:
                    q = q.where(Cabinet.shift_id == shift_id)
                items = session.execute(q).scalars().all()
                for c in items:
                    self.filter_combo.addItem(
                        f"{c.number} ({c.room_type})", ("cabinet", c.id)
                    )

        if prev:
            for i in range(self.filter_combo.count()):
                if self.filter_combo.itemData(i) == prev:
                    self.filter_combo.setCurrentIndex(i)
                    break
        self.filter_combo.blockSignals(False)

        if self.filter_combo.count() > 0:
            self._show_content()
            if self.filter_combo.currentIndex() >= 0:
                self._on_filter_changed()
        else:
            self._show_empty()

    def _show_empty(self):
        self._stack.setCurrentWidget(self.empty_widget)

    def _show_content(self):
        self._stack.setCurrentWidget(self.content_widget)

    def _get_shift_name(self, session, shift_id):
        if not shift_id:
            return "—"
        from app.data.models import Shift
        s = session.get(Shift, shift_id)
        return s.name if s else "—"

    def _on_filter_changed(self):
        data = self.filter_combo.currentData()
        if not data:
            self.grid.clear_grid()
            return

        self._current_filter = data
        filter_type, entity_id = data
        db_path = self._find_db_path()
        conn = sqlite3.connect(db_path)

        if self._current_cat == "classes":
            entries = self._get_class_schedule(conn, entity_id)
        elif self._current_cat == "teachers":
            entries = self._get_teacher_schedule(conn, entity_id)
        else:
            entries = self._get_cabinet_schedule(conn, entity_id)

        self.grid.set_schedule(entries)
        self._update_stats(entries)
        self._rebuild_color_legend()
        conn.close()

    def _update_stats(self, entries):
        total = len(entries)
        conflicts = sum(1 for e in entries if e.get("is_conflict"))
        try:
            if conflicts:
                self.stats_label.setText(f"Уроков: {total}    Конфликтов: {conflicts}")
                self.stats_label.setStyleSheet(
                    "font-size: 11px; color: #e74c3c; font-weight: bold;"
                )
            else:
                self.stats_label.setText(f"Уроков: {total}")
                self.stats_label.setStyleSheet(
                    "font-size: 11px; color: #7f8c8d; font-weight: bold;"
                )
        except RuntimeError:
            pass

    def _find_db_path(self):
        return find_db_path(self.engine)

    def _get_class_schedule(self, conn, class_id):
        rows = conn.execute("""
            SELECT te.day_of_week, te.lesson_number,
                   s.id, s.name, t.full_name,
                   c2.number, sg.group_number, cs.is_split,
                   sg.id, te.subject_group_id, c.grade, c.letter,
                   cs.profile_id
            FROM timetable_entries te
            JOIN subject_groups sg ON sg.id = te.subject_group_id
            JOIN class_subjects cs ON cs.id = sg.class_subject_id
            JOIN classes c ON c.id = cs.class_id
            JOIN subjects s ON s.id = cs.subject_id
            JOIN teachers t ON t.id = sg.teacher_id
            LEFT JOIN cabinets c2 ON c2.id = te.cabinet_id
            WHERE c.id = ?
            ORDER BY te.day_of_week, te.lesson_number
        """, (class_id,)).fetchall()

        sg_ids = list({r[8] for r in rows})
        conflict_groups = self._find_conflicts(conn, sg_ids)

        plain = []
        for r in rows:
            plain.append(dict(
                day=r[0], lesson=r[1],
                subject_id=r[2], subject_name=r[3], teacher_name=r[4],
                cabinet=r[5] or "", group_number=r[6], is_split=bool(r[7]),
                is_conflict=r[8] in conflict_groups,
                class_label="",
                profile_id=r[12],
            ))

        by_slot = {}
        for e in plain:
            key = (e["day"], e["lesson"])
            by_slot.setdefault(key, []).append(e)

        result = []
        for (day, lesson), entries_at_slot in by_slot.items():
            profile_groups = {}
            non_profile = []
            for e in entries_at_slot:
                pid = e.get("profile_id")
                if pid is not None:
                    profile_groups.setdefault(pid, []).append(e)
                else:
                    non_profile.append(e)

            used = set()
            for pid, group_entries in profile_groups.items():
                if len(group_entries) >= 2:
                    a = group_entries[0]
                    b = group_entries[1]
                    merged = dict(
                        day=day, lesson=lesson,
                        subject_id=a["subject_id"], subject_name=a["subject_name"],
                        teacher_name=a["teacher_name"], cabinet=a["cabinet"],
                        group_number=1, is_split=False,
                        is_conflict=a["is_conflict"] or b["is_conflict"],
                        class_label="",
                        is_profile_split=True,
                        subject_id2=b["subject_id"], subject_name2=b["subject_name"],
                        teacher_name2=b["teacher_name"], cabinet2=b["cabinet"],
                        profile_id=pid,
                    )
                    result.append(merged)
                    used.add(a["subject_id"])
                    used.add(b["subject_id"])
                elif len(group_entries) == 1:
                    e = group_entries[0]
                    e.pop("profile_id", None)
                    result.append(e)

            for e in non_profile:
                if e["subject_id"] not in used:
                    e.pop("profile_id", None)
                    result.append(e)

        return result

    def _get_teacher_schedule(self, conn, teacher_id):
        rows = conn.execute("""
            SELECT te.day_of_week, te.lesson_number,
                   s.id, s.name, c.grade, c.letter,
                   c2.number, sg.group_number, cs.is_split,
                   sg.id, te.subject_group_id
            FROM timetable_entries te
            JOIN subject_groups sg ON sg.id = te.subject_group_id
            JOIN class_subjects cs ON cs.id = sg.class_subject_id
            JOIN classes c ON c.id = cs.class_id
            JOIN subjects s ON s.id = cs.subject_id
            LEFT JOIN cabinets c2 ON c2.id = te.cabinet_id
            WHERE sg.teacher_id = ?
            ORDER BY te.day_of_week, te.lesson_number
        """, (teacher_id,)).fetchall()

        sg_ids = list({r[9] for r in rows})
        conflict_groups = self._find_conflicts(conn, sg_ids)

        return [dict(
            day=r[0], lesson=r[1],
            subject_id=r[2], subject_name=r[3], teacher_name="",
            cabinet=r[6] or "", group_number=r[7], is_split=bool(r[8]),
            is_conflict=r[9] in conflict_groups,
            class_label=f"{r[4]}{r[5]}",
        ) for r in rows]

    def _get_cabinet_schedule(self, conn, cabinet_id):
        rows = conn.execute("""
            SELECT te.day_of_week, te.lesson_number,
                   s.id, s.name, t.full_name, c.grade, c.letter,
                   sg.group_number, cs.is_split,
                   sg.id, te.subject_group_id
            FROM timetable_entries te
            JOIN subject_groups sg ON sg.id = te.subject_group_id
            JOIN class_subjects cs ON cs.id = sg.class_subject_id
            JOIN classes c ON c.id = cs.class_id
            JOIN subjects s ON s.id = cs.subject_id
            JOIN teachers t ON t.id = sg.teacher_id
            WHERE te.cabinet_id = ?
            ORDER BY te.day_of_week, te.lesson_number
        """, (cabinet_id,)).fetchall()

        sg_ids = list({r[9] for r in rows})
        conflict_groups = self._find_conflicts(conn, sg_ids)

        return [dict(
            day=r[0], lesson=r[1],
            subject_id=r[2], subject_name=r[3], teacher_name=r[4],
            cabinet="", group_number=r[7], is_split=bool(r[8]),
            is_conflict=r[9] in conflict_groups,
            class_label=f"{r[5]}{r[6]}",
        ) for r in rows]

    def _find_conflicts(self, conn, sg_ids):
        if not sg_ids:
            return set()
        placeholders = ",".join("?" * len(sg_ids))
        rows = conn.execute(f"""
            SELECT te1.subject_group_id, te2.subject_group_id
            FROM timetable_entries te1
            JOIN timetable_entries te2
                ON te1.day_of_week = te2.day_of_week
                AND te1.lesson_number = te2.lesson_number
                AND te1.subject_group_id != te2.subject_group_id
            JOIN subject_groups sg1 ON sg1.id = te1.subject_group_id
            JOIN subject_groups sg2 ON sg2.id = te2.subject_group_id
            JOIN class_subjects cs1 ON cs1.id = sg1.class_subject_id
            JOIN class_subjects cs2 ON cs2.id = sg2.class_subject_id
            WHERE te1.subject_group_id IN ({placeholders})
              AND (
                sg1.teacher_id = sg2.teacher_id
                OR (te1.cabinet_id = te2.cabinet_id AND te1.cabinet_id IS NOT NULL
                    AND te1.cabinet_id != 0)
              )
              AND NOT (cs1.id = cs2.id AND cs1.is_split = 1)
              AND NOT (cs1.profile_id IS NOT NULL AND cs2.profile_id IS NOT NULL
                       AND cs1.profile_id = cs2.profile_id)
        """, sg_ids).fetchall()

        conflicts = set()
        for a, b in rows:
            if a in sg_ids:
                conflicts.add(a)
            if b in sg_ids:
                conflicts.add(b)
        return conflicts

    def _on_cell_clicked(self, day, lesson, cell):
        self._current_click = (day, lesson, cell)
        self.info_title.setText(f"{DAY_NAMES[day]}, урок {lesson}")

        is_editable = self._edit_mode
        self.swap_btn.setEnabled(is_editable and not cell.is_empty)

        if is_editable and not cell.is_empty:
            if cell.is_profile_split:
                hint_text = (
                    f"Выбрана профильная пара: {cell.subject_name} / {cell.subject_name2} — "
                    "перетащите на другой урок или нажмите «Поменять местами»"
                )
            else:
                hint_text = (
                    f"Выбран: {cell.subject_name} ({cell.teacher_name}) — "
                    "перетащите на другой урок или нажмите «Поменять местами»"
                )
            self.swap_hint.setText(hint_text)
            self.swap_hint.setVisible(True)
        else:
            self.swap_hint.setVisible(False)

        if cell.is_empty:
            self.info_subject.setText("Пусто")
            self.info_teacher.setText("")
            self.info_cabinet.setText("")
            self.info_group.setText("")
            self.info_conflict.setText("")
            return

        if cell.is_profile_split:
            self.info_subject.setText(f"{cell.subject_name}\n+\n{cell.subject_name2}")
            self.info_teacher.setText(f"\U0001f468 {cell.teacher_name}\n\U0001f468 {cell.teacher_name2}")
            if cell.cabinet:
                self.info_cabinet.setText(f"\U0001f4cd Кабинет {cell.cabinet}")
            else:
                self.info_cabinet.setText("")
            self.info_group.setText("Профильная пара")
        else:
            self.info_subject.setText(cell.subject_name)
            self.info_teacher.setText(f"\U0001f468 {cell.teacher_name}")
            if cell.cabinet:
                self.info_cabinet.setText(f"\U0001f4cd Кабинет {cell.cabinet}")
            else:
                self.info_cabinet.setText("")
            if cell.is_split:
                self.info_group.setText(f"Подгруппа {cell.group_number}")
            else:
                self.info_group.setText("")

        if cell.is_conflict:
            self.info_conflict.setText("Конфликт!")
        else:
            self.info_conflict.setText("")

    def _on_cell_dropped(self, src_day, src_lesson, tgt_day, tgt_lesson):
        if not self._edit_mode:
            return
        src_cell = self.grid.get_cell(src_day, src_lesson)
        tgt_cell = self.grid.get_cell(tgt_day, tgt_lesson)
        if not src_cell or not tgt_cell:
            return
        if src_cell.is_empty and tgt_cell.is_empty:
            return

        src_text = src_cell.display_text() or "пусто"
        tgt_text = tgt_cell.display_text() or "пусто"

        reply = QMessageBox.question(
            self, "Подтверждение обмена",
            f"Поменять местами?\n\n"
            f"{DAY_NAMES[src_day]}, ур. {src_lesson}: {src_text}\n"
            f"  ↔\n"
            f"{DAY_NAMES[tgt_day]}, ур. {tgt_lesson}: {tgt_text}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        db_path = self._find_db_path()
        conn = sqlite3.connect(db_path)
        try:
            where_clause, params = self._build_filter_clause()
            if not where_clause:
                QMessageBox.warning(self, "Ошибка", "Не удалось определить текущий фильтр.")
                return

            src_entries = conn.execute(
                f"SELECT id, subject_group_id, cabinet_id FROM timetable_entries te "
                f"WHERE day_of_week=? AND lesson_number=? AND {where_clause}",
                (src_day, src_lesson) + tuple(params)
            ).fetchall()

            tgt_entries = conn.execute(
                f"SELECT id, subject_group_id, cabinet_id FROM timetable_entries te "
                f"WHERE day_of_week=? AND lesson_number=? AND {where_clause}",
                (tgt_day, tgt_lesson) + tuple(params)
            ).fetchall()

            if not src_entries and not tgt_entries:
                QMessageBox.information(self, "Обмен", "Нет записей для обмена в текущем фильтре.")
                return

            src_sg_ids = {sg for _, sg, _ in src_entries}
            tgt_sg_ids = {sg for _, sg, _ in tgt_entries}

            existing_at_tgt = conn.execute(
                f"SELECT subject_group_id FROM timetable_entries te "
                f"WHERE day_of_week=? AND lesson_number=? AND {where_clause}",
                (tgt_day, tgt_lesson) + tuple(params)
            ).fetchall()
            existing_src_at_tgt = {sg for (sg,) in existing_at_tgt if sg in src_sg_ids}

            existing_at_src = conn.execute(
                f"SELECT subject_group_id FROM timetable_entries te "
                f"WHERE day_of_week=? AND lesson_number=? AND {where_clause}",
                (src_day, src_lesson) + tuple(params)
            ).fetchall()
            existing_tgt_at_src = {sg for (sg,) in existing_at_src if sg in tgt_sg_ids}

            if existing_src_at_tgt:
                QMessageBox.warning(
                    self, "Невозможно обменять",
                    "Один из предметов уже стоит в целевом слоте.\n"
                    "Попробуйте обменять с другим слотом."
                )
                return

            if existing_tgt_at_src:
                QMessageBox.warning(
                    self, "Невозможно обменять",
                    "Один из предметов уже стоит в исходном слоте.\n"
                    "Попробуйте обменять с другим слотом."
                )
                return

            swap_action = {"moves": []}

            for entry_id, sg_id, cab_id in src_entries:
                swap_action["moves"].append({
                    "entry_id": entry_id,
                    "orig_day": src_day,
                    "orig_lesson": src_lesson,
                })

            for entry_id, sg_id, cab_id in tgt_entries:
                swap_action["moves"].append({
                    "entry_id": entry_id,
                    "orig_day": tgt_day,
                    "orig_lesson": tgt_lesson,
                })

            for eid, sg_id, cab_id in src_entries:
                conn.execute(
                    "UPDATE timetable_entries SET day_of_week=?, lesson_number=? WHERE id=?",
                    (tgt_day, tgt_lesson, eid)
                )

            for eid, sg_id, cab_id in tgt_entries:
                conn.execute(
                    "UPDATE timetable_entries SET day_of_week=?, lesson_number=? WHERE id=?",
                    (src_day, src_lesson, eid)
                )

            conn.commit()

            if len(self._undo_stack) >= 20:
                self._undo_stack.pop(0)
            self._undo_stack.append(swap_action)

            self.undo_btn.setEnabled(True)
            self._on_filter_changed()

        except Exception as e:
            conn.rollback()
            QMessageBox.warning(self, "Ошибка", f"Не удалось обменять: {e}")
        finally:
            conn.close()

    def _on_cell_copy(self, day, lesson, cell):
        if cell.is_empty:
            return
        db_path = self._find_db_path()
        conn = sqlite3.connect(db_path)
        try:
            where_clause, params = self._build_filter_clause()
            if not where_clause:
                return
            entries = conn.execute(
                f"SELECT id, subject_group_id, cabinet_id FROM timetable_entries te "
                f"WHERE day_of_week=? AND lesson_number=? AND {where_clause}",
                (day, lesson) + tuple(params)
            ).fetchall()
            if entries:
                self._clipboard = {
                    "entries": entries,
                    "day": day,
                    "lesson": lesson,
                    "text": cell.display_text(),
                }
                self.swap_hint.setText(f"Скопировано: {cell.display_text()} — ПКМ на пустой ячейке для вставки")
                self.swap_hint.setVisible(True)
        finally:
            conn.close()

    def _on_cell_delete(self, day, lesson, cell):
        if cell.is_empty:
            return
        reply = QMessageBox.question(
            self, "Удаление урока",
            f"Удалить «{cell.display_text()}» из {DAY_NAMES[day]}, ур. {lesson}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        db_path = self._find_db_path()
        conn = sqlite3.connect(db_path)
        try:
            where_clause, params = self._build_filter_clause()
            if not where_clause:
                return
            entries = conn.execute(
                f"SELECT id FROM timetable_entries te "
                f"WHERE day_of_week=? AND lesson_number=? AND {where_clause}",
                (day, lesson) + tuple(params)
            ).fetchall()

            swap_action = {"moves": []}
            for (entry_id,) in entries:
                swap_action["moves"].append({
                    "entry_id": entry_id,
                    "orig_day": day,
                    "orig_lesson": lesson,
                })

            for (entry_id,) in entries:
                conn.execute(
                    "DELETE FROM timetable_entries WHERE id=?",
                    (entry_id,)
                )
            conn.commit()

            if len(self._undo_stack) >= 20:
                self._undo_stack.pop(0)
            self._undo_stack.append(swap_action)
            self.undo_btn.setEnabled(True)
            self._on_filter_changed()

        except Exception as e:
            conn.rollback()
            QMessageBox.warning(self, "Ошибка", f"Не удалось удалить: {e}")
        finally:
            conn.close()

    def _on_cell_edit(self, day, lesson, cell):
        if cell.is_empty:
            return
        from app.ui.dialogs.edit_lesson_dialog import EditLessonDialog
        dlg = EditLessonDialog(
            self.engine, day, lesson, cell, parent=self
        )
        if dlg.exec() == EditLessonDialog.Accepted:
            self._on_filter_changed()

    def _build_filter_clause(self):
        if not self._current_filter:
            return None, []
        filter_type, entity_id = self._current_filter

        if self._current_cat == "classes":
            return (
                "te.subject_group_id IN ("
                "  SELECT sg.id FROM subject_groups sg"
                "  JOIN class_subjects cs ON cs.id = sg.class_subject_id"
                "  WHERE cs.class_id = ?"
                ")",
                [entity_id],
            )
        elif self._current_cat == "teachers":
            return (
                "te.subject_group_id IN ("
                "  SELECT sg.id FROM subject_groups sg"
                "  WHERE sg.teacher_id = ?"
                ")",
                [entity_id],
            )
        elif self._current_cat == "cabinets":
            return (
                "te.cabinet_id = ?",
                [entity_id],
            )
        return None, []

    def _open_swap_dialog(self):
        if not hasattr(self, "_current_click") or not self._current_click:
            return
        day, lesson, cell = self._current_click
        if cell.is_empty:
            return

        dlg = SwapDialog(
            self.engine,
            src_day=day, src_lesson=lesson,
            src_cell_text=cell.subject_name,
            src_teacher=cell.teacher_name,
            parent=self,
        )
        if dlg.exec() == SwapDialog.Accepted and dlg.selected_target:
            self._execute_cross_swap(day, lesson, cell, dlg.selected_target)

    def _execute_cross_swap(self, src_day, src_lesson, src_cell, target):
        src_entry_text = src_cell.subject_name
        src_teacher_text = src_cell.teacher_name
        tgt_day = target["target_day"]
        tgt_lesson = target["target_lesson"]
        tgt_class = target["class_label"]
        tgt_subject = target["subject_name"]

        db_path = self._find_db_path()
        conn = sqlite3.connect(db_path)
        try:
            where_clause, params = self._build_filter_clause()
            if not where_clause:
                QMessageBox.warning(self, "Ошибка", "Не удалось определить текущий фильтр.")
                return

            src_entries = conn.execute(
                f"SELECT id, subject_group_id, cabinet_id FROM timetable_entries te "
                f"WHERE day_of_week=? AND lesson_number=? AND {where_clause}",
                (src_day, src_lesson) + tuple(params)
            ).fetchall()

            target_entry = conn.execute(
                "SELECT id, subject_group_id, cabinet_id FROM timetable_entries "
                "WHERE id=?",
                (target["entry_id"],)
            ).fetchone()

            if not target_entry:
                QMessageBox.warning(self, "Ошибка", "Целевая запись не найдена.")
                return

            tgt_entry_id, tgt_sg_id, tgt_cab_id = target_entry

            if src_entries and all(sg == tgt_sg_id for _, sg, _ in src_entries):
                QMessageBox.information(self, "Обмен", "Этот урок уже находится в выбранной ячейке.")
                return

            conflict_check = conn.execute(
                f"SELECT id FROM timetable_entries te "
                f"WHERE day_of_week=? AND lesson_number=? AND subject_group_id=? "
                f"AND {where_clause}",
                (src_day, src_lesson, tgt_sg_id) + tuple(params)
            ).fetchone()
            if conflict_check:
                QMessageBox.warning(
                    self, "Невозможно обменять",
                    "Этот предмет уже стоит в исходном слоте.\n"
                    "Попробуйте обменять с другим слотом."
                )
                return

            swap_action = {
                "moves": [],
            }
            src_ids_to_move = []
            for entry_id, sg_id, cab_id in src_entries:
                if sg_id == tgt_sg_id:
                    continue
                swap_action["moves"].append({
                    "entry_id": entry_id,
                    "orig_day": src_day,
                    "orig_lesson": src_lesson,
                })
                src_ids_to_move.append(entry_id)

            swap_action["moves"].append({
                "entry_id": tgt_entry_id,
                "orig_day": tgt_day,
                "orig_lesson": tgt_lesson,
            })

            if len(self._undo_stack) >= 20:
                self._undo_stack.pop(0)
            self._undo_stack.append(swap_action)

            for eid in src_ids_to_move:
                conn.execute(
                    "UPDATE timetable_entries SET day_of_week=?, lesson_number=? WHERE id=?",
                    (tgt_day, tgt_lesson, eid)
                )

            conn.execute(
                "UPDATE timetable_entries SET day_of_week=?, lesson_number=? WHERE id=?",
                (src_day, src_lesson, tgt_entry_id)
            )

            conn.commit()

            QMessageBox.information(
                self, "Обмен выполнен",
                f"{tgt_subject} ({tgt_class}) ↔ {src_entry_text} ({src_teacher_text})\n"
                f"({DAY_NAMES[tgt_day]} ур. {tgt_lesson}) ↔ ({DAY_NAMES[src_day]} ур. {src_lesson})"
            )

            self.undo_btn.setEnabled(True)
            self._on_filter_changed()

        except Exception as e:
            conn.rollback()
            QMessageBox.warning(self, "Ошибка", f"Не удалось обменять: {e}")
        finally:
            conn.close()

    def _toggle_edit_mode(self, checked):
        self._edit_mode = checked
        self.grid.set_edit_mode(checked)
        if checked:
            self.edit_btn.setStyleSheet(STYLE_TOGGLE_ON)
            self.edit_btn.setText("Режим просмотра")
            self.edit_hint.setText(
                "Перетащите урок на другой слот для обмена, "
                "или выделите и нажмите «Поменять местами»"
            )
            self.edit_hint.setVisible(True)
        else:
            self.edit_btn.setStyleSheet(STYLE_TOGGLE_OFF)
            self.edit_btn.setText("Режим редактирования")
            self.edit_hint.setVisible(False)
            self.swap_hint.setVisible(False)
            self.swap_btn.setEnabled(False)

    def _undo(self):
        if not self._undo_stack:
            return
        db_path = self._find_db_path()
        conn = sqlite3.connect(db_path)
        try:
            action = self._undo_stack.pop()
            for move in action["moves"]:
                conn.execute(
                    "UPDATE timetable_entries SET day_of_week=?, lesson_number=? WHERE id=?",
                    (move["orig_day"], move["orig_lesson"], move["entry_id"])
                )
            conn.commit()
            self._on_filter_changed()
        except Exception as e:
            conn.rollback()
            QMessageBox.warning(self, "Ошибка", f"Не удалось отменить: {e}")
        finally:
            conn.close()
            if not self._undo_stack:
                self.undo_btn.setEnabled(False)

    def _rebuild_color_legend(self):
        while self.legendFlowLayout.count() > 1:
            item = self.legendFlowLayout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()

        with make_session(self.engine) as session:
            subjects = session.execute(select(Subject)).scalars().all()
            for s in subjects:
                if s.id in self.grid._subject_colors:
                    color = self.grid._subject_colors[s.id]
                    entry = QLabel()
                    entry.setFixedWidth(12)
                    entry.setFixedHeight(12)
                    entry.setStyleSheet(
                        f"background-color: {color.name()}; border-radius: 3px;"
                    )
                    self.legendFlowLayout.insertWidget(self.legendFlowLayout.count() - 1, entry)

                    name = QLabel(s.name)
                    name.setStyleSheet("font-size: 11px; color: #555;")
                    self.legendFlowLayout.insertWidget(self.legendFlowLayout.count() - 1, name)

        while self.legend_container.count():
            w = self.legend_container.takeAt(0).widget()
            if w:
                w.deleteLater()

        with make_session(self.engine) as session:
            subjects = session.execute(select(Subject)).scalars().all()
            for s in subjects:
                if s.id in self.grid._subject_colors:
                    color = self.grid._subject_colors[s.id]
                    row = QHBoxLayout()
                    swatch = QLabel()
                    swatch.setFixedSize(14, 14)
                    swatch.setStyleSheet(
                        f"background-color: {color.name()}; border-radius: 3px;"
                    )
                    row.addWidget(swatch)
                    lbl = QLabel(s.name)
                    lbl.setStyleSheet("font-size: 11px; color: #333;")
                    row.addWidget(lbl)
                    row.addStretch()
                    container = QWidget()
                    container.setLayout(row)
                    self.legend_container.addWidget(container)

    def refresh(self):
        self._rebuild_filter()
