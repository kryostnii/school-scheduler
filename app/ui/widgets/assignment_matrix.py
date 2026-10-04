"""Недельное расписание учителей: учитель × (урок 1-10) × (день Пн-Сб)."""
from PySide6.QtWidgets import (
    QWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame,
    QMessageBox, QAbstractItemView, QPushButton, QButtonGroup, QMenu,
)
from PySide6.QtCore import Qt, Signal, QMimeData, QByteArray
from PySide6.QtGui import QColor, QFont, QDrag

from sqlalchemy import select

from app.config import MAX_LESSONS as _APP_MAX_LESSONS
from app.data.models import (
    Teacher, Subject, SchoolClass, SubjectGroup, ClassSubject,
    TimetableEntry, make_session,
)
from app.styles import TABLE_STYLE

CLASS_COLORS = [
    "#3498db", "#e74c3c", "#2ecc71", "#f39c12", "#9b59b6",
    "#1abc9c", "#e67e22", "#34495e", "#16a085", "#c0392b",
    "#8e44ad", "#2980b9", "#27ae60", "#d35400", "#7f8c8d",
]

MIME_TYPE = "application/x-class-cube"

DAY_NAMES = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб"]
MAX_LESSONS = _APP_MAX_LESSONS


class ClassCube(QLabel):
    def __init__(self, class_id, class_label, color, parent=None):
        super().__init__(class_label, parent)
        self.class_id = class_id
        self.class_label = class_label
        self.setFixedSize(72, 36)
        self.setAlignment(Qt.AlignCenter)
        self.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.setStyleSheet(
            f"background-color: {color}; color: white; border-radius: 6px; "
            f"padding: 4px; margin: 2px;"
        )
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(f"Перетащите класс {class_label} в ячейку урока")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            drag = QDrag(self)
            mime = QMimeData()
            mime.setData(MIME_TYPE, QByteArray(str(self.class_id).encode()))
            mime.setText(self.class_label)
            drag.setMimeData(mime)
            pixmap = self.grab()
            drag.setPixmap(pixmap.scaled(72, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            drag.exec(Qt.MoveAction)


class AssignmentMatrix(QWidget):
    """Недельное расписание учителей.

    Столбцы = дни недели (Пн-Сб).
    Строки = для каждого учителя 10 слотов уроков (ур.1 – ур.10).
    Ячейка = класс + предмет.
    Перетаскивание кубика класса в ячейку создаёт запись в расписании.
    """

    assignment_changed = Signal()

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._class_colors = {}
        self._color_idx = 0
        self._teachers = []
        self._classes = []
        self._week_grid = {}
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setFixedHeight(40)
        header.setStyleSheet("background: #ffffff; border-bottom: 1px solid #e5e8e8;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(12, 0, 12, 0)
        title = QLabel("Назначения: расписание учителей на неделю")
        title.setStyleSheet("font-size: 13px; font-weight: bold; color: #2c3e50;")
        h_layout.addWidget(title)
        h_layout.addStretch()
        hint = QLabel("Перетащите кубик класса в ячейку (учитель × день × урок)")
        hint.setStyleSheet("font-size: 11px; color: #95a5a6; font-style: italic;")
        h_layout.addWidget(hint)
        layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: white; }")

        self.matrix_container = QWidget()
        self.matrix_layout = QVBoxLayout(self.matrix_container)
        self.matrix_layout.setContentsMargins(8, 8, 8, 8)
        self.matrix_layout.setSpacing(8)

        self.table = QTableWidget()
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setShowGrid(True)
        self.table.verticalHeader().setVisible(True)
        self.table.horizontalHeader().setVisible(True)
        self.table.setAcceptDrops(True)
        self.table.viewport().setAcceptDrops(True)
        self.table.viewport().installEventFilter(self)
        self.table.setStyleSheet(TABLE_STYLE)
        self.table.verticalHeader().setDefaultSectionSize(28)
        self.table.verticalHeader().setMinimumSectionSize(24)
        self.table.horizontalHeader().setDefaultSectionSize(90)
        self.table.horizontalHeader().setMinimumSectionSize(70)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)

        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_context_menu)

        self.matrix_layout.addWidget(self.table)

        cubes_frame = QFrame()
        cubes_frame.setStyleSheet(
            "QFrame { background: #f0f3f4; border: 1px solid #d5d8dc; "
            "border-radius: 6px; padding: 8px; }"
        )
        cubes_layout = QVBoxLayout(cubes_frame)
        cubes_layout.setContentsMargins(12, 8, 12, 8)
        cubes_layout.setSpacing(4)

        cubes_header = QLabel("Классы:")
        cubes_header.setStyleSheet(
            "font-size: 12px; font-weight: bold; color: #2c3e50; padding-bottom: 4px;"
        )
        cubes_layout.addWidget(cubes_header)

        cubes_row = QHBoxLayout()
        cubes_row.setSpacing(4)
        cubes_row.setContentsMargins(0, 0, 0, 0)
        self._cubes_container = QWidget()
        self._cubes_layout = QHBoxLayout(self._cubes_container)
        self._cubes_layout.setContentsMargins(0, 0, 0, 0)
        self._cubes_layout.setSpacing(4)
        cubes_row.addWidget(self._cubes_container)
        cubes_row.addStretch()
        cubes_layout.addLayout(cubes_row)

        self.matrix_layout.addWidget(cubes_frame)

        scroll.setWidget(self.matrix_container)
        layout.addWidget(scroll, stretch=1)

    def refresh(self):
        with make_session(self.engine) as session:
            self._teachers = session.execute(
                select(Teacher).order_by(Teacher.full_name)
            ).scalars().all()
            self._subjects = {
                s.id: s.name for s in session.execute(select(Subject)).scalars()
            }
            self._classes = session.execute(
                select(SchoolClass).order_by(SchoolClass.grade, SchoolClass.letter)
            ).scalars().all()
            self._class_map = {c.id: f"{c.grade}{c.letter}" for c in self._classes}

            self._sg_teacher_subj = {}
            for sg in session.execute(select(SubjectGroup)).scalars():
                cs = session.get(ClassSubject, sg.class_subject_id)
                key = (sg.teacher_id, cs.class_id, cs.subject_id)
                self._sg_teacher_subj[key] = sg.id

            self._week_grid = {}
            rows = session.execute(
                select(
                    TimetableEntry.day_of_week, TimetableEntry.lesson_number,
                    SubjectGroup.teacher_id, SchoolClass.id, Subject.id,
                    Subject.name, SchoolClass.grade, SchoolClass.letter,
                    TimetableEntry.id,
                )
                .join(SubjectGroup, SubjectGroup.id == TimetableEntry.subject_group_id)
                .join(ClassSubject, ClassSubject.id == SubjectGroup.class_subject_id)
                .join(Subject, Subject.id == ClassSubject.subject_id)
                .join(SchoolClass, SchoolClass.id == ClassSubject.class_id)
                .order_by(TimetableEntry.day_of_week, TimetableEntry.lesson_number)
            ).all()

            for r in rows:
                day, lesson, teacher_id = r[0], r[1], r[2]
                class_id, subj_id, subj_name = r[3], r[4], r[5]
                grade, letter, entry_id = r[6], r[7], r[8]
                key = (teacher_id, day, lesson)
                self._week_grid[key] = {
                    "class_id": class_id,
                    "class_label": f"{grade}{letter}",
                    "subject_id": subj_id,
                    "subject_name": subj_name,
                    "entry_id": entry_id,
                }

        self._build_table()
        self._build_cubes()

    def _build_table(self):
        num_teachers = len(self._teachers)
        total_rows = num_teachers * MAX_LESSONS
        num_days = len(DAY_NAMES)

        self.table.setRowCount(total_rows)
        self.table.setColumnCount(num_days + 1)

        headers = ["Учитель"] + DAY_NAMES
        self.table.setHorizontalHeaderLabels(headers)

        vert_headers = []
        for t_idx, teacher in enumerate(self._teachers):
            for lesson in range(1, MAX_LESSONS + 1):
                vert_headers.append(str(lesson))
        self.table.setVerticalHeaderLabels(vert_headers)

        for t_idx, teacher in enumerate(self._teachers):
            teacher_id = teacher.id
            teacher_name = teacher.full_name
            base_row = t_idx * MAX_LESSONS

            for lesson in range(1, MAX_LESSONS + 1):
                row = base_row + lesson - 1
                self.table.setRowHeight(row, 28)

            self.table.setSpan(base_row, 0, MAX_LESSONS, 1)

            name_item = QTableWidgetItem(teacher_name)
            name_item.setTextAlignment(Qt.AlignCenter)
            name_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
            name_item.setBackground(QColor("#34495e"))
            name_item.setForeground(QColor("white"))
            name_item.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(base_row, 0, name_item)

            for day in range(1, num_days + 1):
                for lesson in range(1, MAX_LESSONS + 1):
                    row = base_row + lesson - 1
                    col = day  # col 0 = teacher name, col 1-6 = days

                    key = (teacher_id, day, lesson)
                    cell_data = self._week_grid.get(key)

                    if cell_data:
                        cls_label = cell_data["class_label"]
                        subj_name = cell_data["subject_name"]
                        text = f"{cls_label}\n{subj_name}"
                        item = QTableWidgetItem(text)
                        item.setTextAlignment(Qt.AlignCenter)
                        item.setFont(QFont("Segoe UI", 8, QFont.Bold))

                        color = self._get_class_color(cell_data["class_id"])
                        item.setBackground(QColor(color).lighter(160))
                        item.setForeground(QColor("#2c3e50"))

                        tooltip = (
                            f"{teacher_name}\n"
                            f"{DAY_NAMES[day]}, урок {lesson}\n"
                            f"Класс: {cls_label}\n"
                            f"Предмет: {subj_name}"
                        )
                        item.setToolTip(tooltip)
                    else:
                        item = QTableWidgetItem("")
                        item.setBackground(QColor("#fafafa"))
                        item.setForeground(QColor("#d5d8dc"))

                    item.setData(Qt.UserRole, {
                        "teacher_id": teacher_id,
                        "day": day,
                        "lesson": lesson,
                    })
                    self.table.setItem(row, col, item)

    def _build_cubes(self):
        while self._cubes_layout.count():
            item = self._cubes_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for cobj in self._classes:
            class_id = cobj.id
            label = f"{cobj.grade}{cobj.letter}"
            color = self._get_class_color(class_id)
            cube = ClassCube(class_id, label, color)
            self._cubes_layout.addWidget(cube)

        self._cubes_layout.addStretch()

    def _get_class_color(self, class_id):
        if class_id not in self._class_colors:
            self._class_colors[class_id] = CLASS_COLORS[
                self._color_idx % len(CLASS_COLORS)]
            self._color_idx += 1
        return self._class_colors[class_id]

    def _on_context_menu(self, pos):
        idx = self.table.indexAt(pos)
        if not idx.isValid() or idx.column() == 0:
            return

        row, col = idx.row(), idx.column()
        t_idx = row // MAX_LESSONS
        lesson = (row % MAX_LESSONS) + 1
        day = col

        if t_idx >= len(self._teachers):
            return

        _teacher = self._teachers[t_idx]
        teacher_id = _teacher.id
        teacher_name = _teacher.full_name
        key = (teacher_id, day, lesson)
        cell_data = self._week_grid.get(key)
        if not cell_data:
            return

        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background: white; border: 1px solid #d5d8dc; border-radius: 4px; "
            "padding: 4px; }"
            "QMenu::item { padding: 6px 20px; font-size: 12px; }"
            "QMenu::item:selected { background: #e74c3c; color: white; border-radius: 2px; }"
        )

        day_name = DAY_NAMES[day - 1]
        info_text = (
            f"{cell_data['class_label']} — {cell_data['subject_name']}\n"
            f"{teacher_name}, {day_name}, ур. {lesson}"
        )
        info_action = menu.addAction(info_text)
        info_action.setEnabled(False)
        menu.addSeparator()

        del_action = menu.addAction("\U0001f5d1 Удалить урок")
        del_action.triggered.connect(
            lambda: self._delete_entry(key, cell_data, teacher_name, day_name, lesson)
        )

        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _delete_entry(self, key, cell_data, teacher_name, day_name, lesson):
        reply = QMessageBox.question(
            self, "Удаление урока",
            f"Удалить?\n\n"
            f"{teacher_name}\n"
            f"{cell_data['class_label']} — {cell_data['subject_name']}\n"
            f"{day_name}, урок {lesson}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        with make_session(self.engine) as session:
            try:
                entry = session.get(TimetableEntry, cell_data["entry_id"])
                if entry:
                    session.delete(entry)
                    session.commit()
                self.refresh()
                self.assignment_changed.emit()
            except Exception as e:
                session.rollback()
                QMessageBox.warning(self, "Ошибка", f"Не удалось удалить: {e}")

    def eventFilter(self, obj, event):
        if obj == self.table.viewport():
            if event.type() == event.Type.DragEnter:
                if event.mimeData().hasFormat(MIME_TYPE):
                    event.acceptProposedAction()
                    return True
            elif event.type() == event.Type.DragMove:
                if event.mimeData().hasFormat(MIME_TYPE):
                    event.acceptProposedAction()
                    return True
            elif event.type() == event.Type.Drop:
                if event.mimeData().hasFormat(MIME_TYPE):
                    class_id = int(event.mimeData().data(MIME_TYPE).data().decode())
                    idx = self.table.indexAt(event.pos())
                    if idx.isValid():
                        self._on_class_dropped(class_id, idx.row(), idx.column())
                    event.acceptProposedAction()
                    return True
        return super().eventFilter(obj, event)

    def _on_class_dropped(self, class_id, row, col):
        if row < 0 or col < 0:
            return
        num_teachers = len(self._teachers)
        if num_teachers == 0:
            return

        t_idx = row // MAX_LESSONS
        lesson = (row % MAX_LESSONS) + 1
        day = col  # col 1-6 = days 1-6

        if t_idx >= num_teachers:
            return
        if day < 1 or day > len(DAY_NAMES):
            return

        _teacher = self._teachers[t_idx]
        teacher_id = _teacher.id
        teacher_name = _teacher.full_name
        day_name = DAY_NAMES[day - 1]

        class_obj = next((c for c in self._classes if c.id == class_id), None)
        if not class_obj:
            return
        class_label = f"{class_obj.grade}{class_obj.letter}"

        existing = self._week_grid.get((teacher_id, day, lesson))
        if existing:
            QMessageBox.information(
                self, "Слот занят",
                f"{teacher_name} уже ведёт урок в {day_name}, ур. {lesson}:\n"
                f"{existing['class_label']} — {existing['subject_name']}"
            )
            return

        sg_entries = []
        for (tid, cid, sid), sg_id in self._sg_teacher_subj.items():
            if tid == teacher_id and cid == class_id:
                subj_name = self._subjects.get(sid, "?")
                sg_entries.append((sid, subj_name, sg_id))

        if not sg_entries:
            QMessageBox.warning(
                self, "Нет привязки",
                f"Нет привязки «{teacher_name} → {class_label}».\n"
                "Сначала создайте предметную группу в учебном плане."
            )
            return

        if len(sg_entries) == 1:
            subject_id, subject_name, sg_id = sg_entries[0]
        else:
            from PySide6.QtWidgets import QInputDialog
            names = [f"{s[1]}" for s in sg_entries]
            item, ok = QInputDialog.getItem(
                self, "Выбор предмета",
                f"{teacher_name} ведёт несколько предметов у {class_label}:\nВыберите:",
                names, 0, False
            )
            if not ok:
                return
            idx = names.index(item)
            subject_id, subject_name, sg_id = sg_entries[idx]

        reply = QMessageBox.question(
            self, "Назначение урока",
            f"Назначить?\n\n"
            f"Учитель: {teacher_name}\n"
            f"Предмет: {subject_name}\n"
            f"Класс: {class_label}\n"
            f"Когда: {day_name}, урок {lesson}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        with make_session(self.engine) as session:
            try:
                conflict = session.execute(
                    select(TimetableEntry.id).where(
                        TimetableEntry.subject_group_id == sg_id,
                        TimetableEntry.day_of_week == day,
                        TimetableEntry.lesson_number == lesson,
                    )
                ).scalar_one_or_none()
                if conflict:
                    QMessageBox.warning(
                        self, "Конфликт",
                        "Этот предмет уже назначен на этот слот."
                    )
                    return

                teacher_conflict = session.execute(
                    select(
                        TimetableEntry.id, Subject.name,
                        SchoolClass.grade, SchoolClass.letter,
                    )
                    .join(SubjectGroup, SubjectGroup.id == TimetableEntry.subject_group_id)
                    .join(ClassSubject, ClassSubject.id == SubjectGroup.class_subject_id)
                    .join(Subject, Subject.id == ClassSubject.subject_id)
                    .join(SchoolClass, SchoolClass.id == ClassSubject.class_id)
                    .where(
                        TimetableEntry.day_of_week == day,
                        TimetableEntry.lesson_number == lesson,
                        SubjectGroup.teacher_id == teacher_id,
                    )
                ).first()
                if teacher_conflict:
                    _, sname, grade, letter = teacher_conflict
                    QMessageBox.warning(
                        self, "Учитель занят",
                        f"{teacher_name} уже ведёт {sname} ({grade}{letter}) "
                        f"в {day_name}, ур. {lesson}."
                    )
                    return

                session.add(TimetableEntry(
                    subject_group_id=sg_id,
                    day_of_week=day,
                    lesson_number=lesson,
                    cabinet_id=None,
                ))
                session.commit()
                self.refresh()
                self.assignment_changed.emit()

            except Exception as e:
                session.rollback()
                QMessageBox.warning(self, "Ошибка", f"Не удалось назначить: {e}")
