"""Страница управления данными: учителя, классы, предметы, кабинеты, учебные планы."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QTableWidget, QTableWidgetItem, QPushButton, QHeaderView,
    QMessageBox, QLabel, QFrame, QStackedWidget, QScrollArea,
)
from PySide6.QtCore import Qt

from sqlalchemy import select

from app.data.models import (
    Teacher, SchoolClass, Subject, Cabinet, Shift, AcademicYear,
    ClassSubject, SubjectGroup,
    make_session,
)
from app.styles import TABLE_STYLE, BTN_PRIMARY, BTN_DEFAULT, BTN_DANGER
from app.ui.dialogs.teacher_dialog import TeacherDialog
from app.ui.dialogs.class_dialog import ClassDialog
from app.ui.dialogs.cabinet_dialog import CabinetDialog
from app.ui.dialogs.subject_dialog import SubjectDialog
from app.ui.dialogs.class_subject_dialog import ClassSubjectDialog
from app.ui.dialogs.subject_group_dialog import SubjectGroupDialog
from app.ui.dialogs.profile_dialog import ProfileDialog

EMPTY_STYLE = """
    QLabel {
        color: #95a5a6;
        font-size: 12px;
        padding: 20px;
    }
"""


class EmptyWidget(QWidget):
    """Пустое состояние — показывается когда нет данных."""
    def __init__(self, text, hint="", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        msg = QLabel(text)
        msg.setStyleSheet(
            "font-size: 14px; color: #95a5a6; font-weight: bold;"
        )
        msg.setAlignment(Qt.AlignCenter)
        layout.addWidget(msg)
        if hint:
            lbl = QLabel(hint)
            lbl.setStyleSheet("font-size: 12px; color: #bdc3c7;")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setWordWrap(True)
            layout.addWidget(lbl)


class DataPage(QWidget):
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        header = QLabel("Данные школы")
        header.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #2c3e50; padding-bottom: 2px;"
        )
        layout.addWidget(header)

        sub = QLabel("Справочники и учебные планы: учителя, классы, предметы, кабинеты")
        sub.setStyleSheet("font-size: 12px; color: #7f8c8d; padding-bottom: 8px;")
        layout.addWidget(sub)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #d0d0d0; border-radius: 4px; }
            QTabBar::tab { padding: 8px 16px; font-size: 12px; }
        """)

        self.teachers_table = self._create_table(["ID", "ФИО", "Часов/нед", "Кабинет", "Смена"])
        self.classes_table = self._create_table(["ID", "Класс", "Параллель", "Буква", "Смена"])
        self.subjects_table = self._create_table(["ID", "Название", "Трудность", "Физкультура", "Тяжёлый", "Сдвоенные"])
        self.cabinets_table = self._create_table(["ID", "Номер", "Вместимость", "Тип", "Смена"])

        self.curriculum_widget = self._build_curriculum_tab()

        self.tabs.addTab(
            self._wrap_table(self.teachers_table, "teachers",
                            "Нажмите «Добавить», чтобы создать учителя"),
            "Учителя"
        )
        self.tabs.addTab(
            self._wrap_table(self.classes_table, "classes",
                            "Нажмите «Добавить», чтобы создать класс"),
            "Классы"
        )
        self.tabs.addTab(
            self._wrap_table(self.subjects_table, "subjects",
                            "Нажмите «Добавить», чтобы создать предмет"),
            "Предметы"
        )
        self.tabs.addTab(
            self._wrap_table(self.cabinets_table, "cabinets",
                            "Нажмите «Добавить», чтобы создать кабинет"),
            "Кабинеты"
        )
        self.tabs.addTab(self.curriculum_widget, "Учебные планы")

        layout.addWidget(self.tabs)

    def _update_tab_counts(self):
        self.tabs.setTabText(0, f"Учителя ({self.teachers_table.rowCount()})")
        self.tabs.setTabText(1, f"Классы ({self.classes_table.rowCount()})")
        self.tabs.setTabText(2, f"Предметы ({self.subjects_table.rowCount()})")
        self.tabs.setTabText(3, f"Кабинеты ({self.cabinets_table.rowCount()})")

    def _create_table(self, headers):
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setStyleSheet(TABLE_STYLE)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setMinimumHeight(200)
        return table

    def _wrap_table(self, table, entity, empty_hint=""):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        layout.addWidget(table)

        if empty_hint:
            lbl = QLabel(empty_hint)
            lbl.setStyleSheet("font-size: 11px; color: #95a5a6; padding: 2px 4px;")
            layout.addWidget(lbl)

        btn_row = QHBoxLayout()
        btn_add = QPushButton("+ Добавить")
        btn_add.setStyleSheet(BTN_DEFAULT)
        btn_add.setToolTip("Добавить новую запись")
        btn_edit = QPushButton("Редактировать")
        btn_edit.setStyleSheet(BTN_DEFAULT)
        btn_edit.setToolTip("Изменить выбранную запись")
        btn_delete = QPushButton("Удалить")
        btn_delete.setStyleSheet(BTN_DANGER)
        btn_delete.setToolTip("Удалить выбранную запись")

        btn_add.clicked.connect(lambda: self._add_entity(entity))
        btn_edit.clicked.connect(lambda: self._edit_entity(entity, table))
        btn_delete.clicked.connect(lambda: self._delete_entity(entity, table))

        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_edit)
        btn_row.addStretch()
        btn_row.addWidget(btn_delete)
        layout.addLayout(btn_row)
        return container

    def _build_curriculum_tab(self):
        container = QWidget()
        outer_layout = QVBoxLayout(container)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        step1 = QFrame()
        step1.setStyleSheet("""
            QFrame { background: white; border: 1px solid #d0d0d0; border-radius: 6px; padding: 8px; }
        """)
        s1_layout = QVBoxLayout(step1)
        s1_layout.setContentsMargins(12, 10, 12, 10)
        s1_layout.setSpacing(4)

        s1_header = QHBoxLayout()
        s1_badge = QLabel(" 1 ")
        s1_badge.setStyleSheet(
            "background: #3498db; color: white; font-weight: bold; "
            "border-radius: 10px; padding: 2px 8px; font-size: 12px;"
        )
        s1_badge.setFixedWidth(24)
        s1_header.addWidget(s1_badge)
        s1_title = QLabel("Учебные планы классов")
        s1_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #2c3e50;")
        s1_header.addWidget(s1_title)
        s1_header.addStretch()
        s1_layout.addLayout(s1_header)

        s1_hint = QLabel(
            "Укажите, какие предметы изучаются в каждом классе и сколько часов в неделю"
        )
        s1_hint.setStyleSheet("font-size: 11px; color: #7f8c8d;")
        s1_hint.setWordWrap(True)
        s1_layout.addWidget(s1_hint)

        self.cs_table = self._create_table(["ID", "Класс", "Предмет", "Часов/нед", "Split"])
        self.cs_table.setMaximumHeight(220)
        self.cs_table.itemSelectionChanged.connect(self._on_cs_selected)
        s1_layout.addWidget(self.cs_table)

        cs_btn_row = QHBoxLayout()
        cs_add = QPushButton("+ Добавить план")
        cs_add.setStyleSheet(BTN_DEFAULT)
        cs_edit = QPushButton("Редактировать")
        cs_edit.setStyleSheet(BTN_DEFAULT)
        cs_delete = QPushButton("Удалить")
        cs_delete.setStyleSheet(BTN_DANGER)
        cs_add.clicked.connect(self._add_class_subject)
        cs_edit.clicked.connect(self._edit_class_subject)
        cs_delete.clicked.connect(self._delete_class_subject)
        cs_btn_row.addWidget(cs_add)
        cs_btn_row.addWidget(cs_edit)
        cs_btn_row.addStretch()
        cs_btn_row.addWidget(cs_delete)
        s1_layout.addLayout(cs_btn_row)

        layout.addWidget(step1)

        arrow = QLabel()
        arrow.setText("\u25bc")
        arrow.setStyleSheet("color: #bdc3c7; font-size: 18px;")
        arrow.setAlignment(Qt.AlignCenter)
        arrow.setVisible(False)
        self._arrow_label = arrow
        layout.addWidget(arrow)

        step2 = QFrame()
        step2.setStyleSheet("""
            QFrame { background: white; border: 1px solid #d0d0d0; border-radius: 6px; padding: 8px; }
        """)
        self._step2_frame = step2
        s2_layout = QVBoxLayout(step2)
        s2_layout.setContentsMargins(12, 10, 12, 10)
        s2_layout.setSpacing(4)

        s2_header = QHBoxLayout()
        s2_badge = QLabel(" 2 ")
        s2_badge.setStyleSheet(
            "background: #e67e22; color: white; font-weight: bold; "
            "border-radius: 10px; padding: 2px 8px; font-size: 12px;"
        )
        s2_badge.setFixedWidth(24)
        s2_header.addWidget(s2_badge)
        self._s2_title = QLabel("Подгруппы (преподаватели)")
        self._s2_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #2c3e50;")
        s2_header.addWidget(self._s2_title)
        s2_header.addStretch()
        s2_layout.addLayout(s2_header)

        self._s2_hint = QLabel(
            "Выберите предмет класса выше, затем добавьте преподавателя"
        )
        self._s2_hint.setStyleSheet("font-size: 11px; color: #7f8c8d;")
        self._s2_hint.setWordWrap(True)
        s2_layout.addWidget(self._s2_hint)

        self.sg_table = self._create_table(["ID", "№ группы", "Учитель", "Кабинет"])
        s2_layout.addWidget(self.sg_table)

        sg_btn_row = QHBoxLayout()
        sg_add = QPushButton("+ Добавить группу")
        sg_add.setStyleSheet(BTN_DEFAULT)
        sg_edit = QPushButton("Редактировать")
        sg_edit.setStyleSheet(BTN_DEFAULT)
        sg_delete = QPushButton("Удалить")
        sg_delete.setStyleSheet(BTN_DANGER)
        sg_add.clicked.connect(self._add_subject_group)
        sg_edit.clicked.connect(self._edit_subject_group)
        sg_delete.clicked.connect(self._delete_subject_group)
        sg_btn_row.addWidget(sg_add)
        sg_btn_row.addWidget(sg_edit)
        sg_btn_row.addStretch()
        sg_btn_row.addWidget(sg_delete)
        s2_layout.addLayout(sg_btn_row)

        layout.addWidget(step2)

        arrow3 = QLabel()
        arrow3.setText("\u25bc")
        arrow3.setStyleSheet("color: #bdc3c7; font-size: 18px;")
        arrow3.setAlignment(Qt.AlignCenter)
        self._arrow3_label = arrow3
        arrow3.setVisible(False)
        layout.addWidget(arrow3)

        step3 = QFrame()
        step3.setStyleSheet("""
            QFrame { background: white; border: 1px solid #d0d0d0; border-radius: 6px; padding: 8px; }
        """)
        self._step3_frame = step3
        s3_layout = QVBoxLayout(step3)
        s3_layout.setContentsMargins(12, 10, 12, 10)
        s3_layout.setSpacing(4)

        s3_header = QHBoxLayout()
        s3_badge = QLabel(" 3 ")
        s3_badge.setStyleSheet(
            "background: #8e44ad; color: white; font-weight: bold; "
            "border-radius: 10px; padding: 2px 8px; font-size: 12px;"
        )
        s3_badge.setFixedWidth(24)
        s3_header.addWidget(s3_badge)
        s3_title = QLabel("Профильные пары")
        s3_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #2c3e50;")
        s3_header.addWidget(s3_title)
        s3_header.addStretch()
        s3_layout.addLayout(s3_header)

        s3_hint = QLabel(
            "Профильные пары — два предмета одного класса, которые "
            "проходят одновременно в разных подгруппах (например, Информатика / Математика). "
            "В расписании класса отображается_split-ячейка с двумя цветами."
        )
        s3_hint.setStyleSheet("font-size: 11px; color: #7f8c8d;")
        s3_hint.setWordWrap(True)
        s3_layout.addWidget(s3_hint)

        self.profiles_table = self._create_table(
            ["ID", "Класс", "Предмет 1", "Предмет 2", "Профиль ID"]
        )
        self.profiles_table.setMaximumHeight(200)
        s3_layout.addWidget(self.profiles_table)

        p_btn_row = QHBoxLayout()
        p_add = QPushButton("+ Создать профиль")
        p_add.setStyleSheet(BTN_DEFAULT)
        p_add.setToolTip("Связать два предмета одного класса в профильную пару")
        p_delete = QPushButton("Удалить")
        p_delete.setStyleSheet(BTN_DANGER)
        p_delete.setToolTip("Разорвать профильную связь")
        p_add.clicked.connect(self._add_profile)
        p_delete.clicked.connect(self._delete_profile)
        p_btn_row.addWidget(p_add)
        p_btn_row.addStretch()
        p_btn_row.addWidget(p_delete)
        s3_layout.addLayout(p_btn_row)

        layout.addWidget(step3)

        layout.addStretch()

        scroll.setWidget(inner)
        outer_layout.addWidget(scroll)

        return container

    def _on_cs_selected(self):
        row = self.cs_table.currentRow()
        has_selection = row >= 0
        self._arrow_label.setVisible(has_selection)
        self._step2_frame.setVisible(True)

        if has_selection:
            class_label = self.cs_table.item(row, 1)
            subject = self.cs_table.item(row, 2)
            if class_label and subject:
                self._s2_title.setText(
                    f"Подгруппы: {class_label.text()} — {subject.text()}"
                )
                self._s2_hint.setText("Добавьте преподавателя для этой группы")
        else:
            self._s2_title.setText("Подгруппы (преподаватели)")
            self._s2_hint.setText("Выберите предмет класса выше, затем добавьте преподавателя")

        self._fill_subject_groups()

    def refresh(self):
        with make_session(self.engine) as session:
            self._fill_teachers(session)
            self._fill_classes(session)
            self._fill_subjects(session)
            self._fill_cabinets(session)
            self._fill_class_subjects(session)
            self._fill_subject_groups(session)
            self._fill_profiles(session)
        self._update_tab_counts()

    def _fill_teachers(self, session):
        teachers = session.execute(select(Teacher)).scalars().all()
        self.teachers_table.setRowCount(len(teachers))
        for i, t in enumerate(teachers):
            cab_num = ""
            if t.home_cabinet_id:
                cab = session.get(Cabinet, t.home_cabinet_id)
                cab_num = cab.number if cab else ""
            shift_name = ""
            if t.shift_id:
                shift = session.get(Shift, t.shift_id)
                shift_name = shift.name if shift else ""
            self._set_row(self.teachers_table, i, [
                str(t.id), t.full_name, str(t.max_load_hours), cab_num, shift_name,
            ])

    def _fill_classes(self, session):
        classes = session.execute(select(SchoolClass)).scalars().all()
        self.classes_table.setRowCount(len(classes))
        for i, c in enumerate(classes):
            shift_name = ""
            if c.shift_id:
                shift = session.get(Shift, c.shift_id)
                shift_name = shift.name if shift else ""
            self._set_row(self.classes_table, i, [
                str(c.id), f"{c.grade}{c.letter}", str(c.grade), c.letter, shift_name,
            ])

    def _fill_subjects(self, session):
        subjects = session.execute(select(Subject)).scalars().all()
        self.subjects_table.setRowCount(len(subjects))
        for i, s in enumerate(subjects):
            self._set_row(self.subjects_table, i, [
                str(s.id), s.name, str(s.difficulty_rank),
                "\u2714" if s.is_physical_education else "",
                "\u2714" if s.is_heavy_subject else "",
                "\u2714" if s.allows_double_lesson else "",
            ])

    def _fill_cabinets(self, session):
        cabinets = session.execute(select(Cabinet)).scalars().all()
        self.cabinets_table.setRowCount(len(cabinets))
        for i, c in enumerate(cabinets):
            shift_name = ""
            if c.shift_id:
                shift = session.get(Shift, c.shift_id)
                shift_name = shift.name if shift else ""
            self._set_row(self.cabinets_table, i, [
                str(c.id), c.number, str(c.capacity or ""), c.room_type, shift_name,
            ])

    def _set_row(self, table, row, values):
        for col, val in enumerate(values):
            item = QTableWidgetItem(val)
            item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, col, item)

    def _get_active_year_id(self):
        with make_session(self.engine) as session:
            year = session.execute(
                select(AcademicYear).where(AcademicYear.is_active == 1)
            ).scalar_one_or_none()
            return year.id if year else None

    def _add_entity(self, entity):
        with make_session(self.engine) as session:
            shifts = session.execute(select(Shift)).scalars().all()
            cabinets = session.execute(select(Cabinet)).scalars().all()

            if entity == "teachers":
                dlg = TeacherDialog(self, cabinets=cabinets, shifts=shifts)
                if dlg.exec() == TeacherDialog.Accepted and dlg.result_data:
                    t = Teacher(**dlg.result_data)
                    session.add(t)
                    session.commit()
            elif entity == "classes":
                year_id = self._get_active_year_id()
                if not year_id:
                    QMessageBox.warning(self, "Ошибка", "Нет активного учебного года. Создайте его в БД.")
                    return
                dlg = ClassDialog(self, shifts=shifts, academic_year_id=year_id)
                if dlg.exec() == ClassDialog.Accepted and dlg.result_data:
                    c = SchoolClass(**dlg.result_data)
                    session.add(c)
                    session.commit()
            elif entity == "subjects":
                dlg = SubjectDialog(self)
                if dlg.exec() == SubjectDialog.Accepted and dlg.result_data:
                    s = Subject(**dlg.result_data)
                    session.add(s)
                    session.commit()
            elif entity == "cabinets":
                dlg = CabinetDialog(self, shifts=shifts)
                if dlg.exec() == CabinetDialog.Accepted and dlg.result_data:
                    c = Cabinet(**dlg.result_data)
                    session.add(c)
                    session.commit()
        self.refresh()

    def _edit_entity(self, entity, table):
        row = table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Подсказка", "Выберите строку для редактирования.")
            return
        item = table.item(row, 0)
        if item is None or not item.text().isdigit():
            return
        entity_id = int(item.text())

        with make_session(self.engine) as session:
            shifts = session.execute(select(Shift)).scalars().all()
            cabinets = session.execute(select(Cabinet)).scalars().all()

            if entity == "teachers":
                obj = session.get(Teacher, entity_id)
                if not obj:
                    return
                dlg = TeacherDialog(self, teacher=obj, cabinets=cabinets, shifts=shifts)
                if dlg.exec() == TeacherDialog.Accepted and dlg.result_data:
                    for k, v in dlg.result_data.items():
                        setattr(obj, k, v)
                    session.commit()
            elif entity == "classes":
                obj = session.get(SchoolClass, entity_id)
                if not obj:
                    return
                dlg = ClassDialog(self, school_class=obj, shifts=shifts, academic_year_id=obj.academic_year_id)
                if dlg.exec() == ClassDialog.Accepted and dlg.result_data:
                    for k, v in dlg.result_data.items():
                        setattr(obj, k, v)
                    session.commit()
            elif entity == "subjects":
                obj = session.get(Subject, entity_id)
                if not obj:
                    return
                dlg = SubjectDialog(self, subject=obj)
                if dlg.exec() == SubjectDialog.Accepted and dlg.result_data:
                    for k, v in dlg.result_data.items():
                        setattr(obj, k, v)
                    session.commit()
            elif entity == "cabinets":
                obj = session.get(Cabinet, entity_id)
                if not obj:
                    return
                dlg = CabinetDialog(self, cabinet=obj, shifts=shifts)
                if dlg.exec() == CabinetDialog.Accepted and dlg.result_data:
                    for k, v in dlg.result_data.items():
                        setattr(obj, k, v)
                    session.commit()
        self.refresh()

    def _delete_entity(self, entity, table):
        row = table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Подсказка", "Выберите строку для удаления.")
            return
        item = table.item(row, 0)
        if item is None or not item.text().isdigit():
            return
        entity_id = int(item.text())
        reply = QMessageBox.question(
            self, "Подтверждение", "Удалить запись?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        model_map = {
            "teachers": Teacher,
            "classes": SchoolClass,
            "subjects": Subject,
            "cabinets": Cabinet,
        }
        with make_session(self.engine) as session:
            obj = session.get(model_map[entity], entity_id)
            if obj:
                session.delete(obj)
                session.commit()
        self.refresh()

    def _fill_class_subjects(self, session):
        rows = session.execute(select(ClassSubject)).scalars().all()
        self.cs_table.setRowCount(len(rows))
        for i, cs in enumerate(rows):
            class_obj = session.get(SchoolClass, cs.class_id)
            subj_obj = session.get(Subject, cs.subject_id)
            class_label = f"{class_obj.grade}{class_obj.letter}" if class_obj else "?"
            subj_name = subj_obj.name if subj_obj else "?"
            self._set_row(self.cs_table, i, [
                str(cs.id), class_label, subj_name, str(cs.hours_per_week),
                "\u2714" if cs.is_split else "",
            ])

    def _fill_subject_groups(self, session=None):
        row = self.cs_table.currentRow()
        if row < 0:
            self.sg_table.setRowCount(0)
            return
        item = self.cs_table.item(row, 0)
        if item is None or not item.text().isdigit():
            self.sg_table.setRowCount(0)
            return
        cs_id = int(item.text())
        own_session = session is None
        if own_session:
            session = make_session(self.engine)
        try:
            rows = session.execute(
                select(SubjectGroup).where(SubjectGroup.class_subject_id == cs_id)
            ).scalars().all()
            self.sg_table.setRowCount(len(rows))
            for i, sg in enumerate(rows):
                teacher = session.get(Teacher, sg.teacher_id)
                cab = session.get(Cabinet, sg.cabinet_id) if sg.cabinet_id else None
                self._set_row(self.sg_table, i, [
                    str(sg.id), str(sg.group_number),
                    teacher.full_name if teacher else "?",
                    f"{cab.number} ({cab.room_type})" if cab else "\u2014",
                ])
        finally:
            if own_session:
                session.close()

    def _add_class_subject(self):
        with make_session(self.engine) as session:
            classes = session.execute(select(SchoolClass)).scalars().all()
            subjects = session.execute(select(Subject)).scalars().all()
            if not classes:
                QMessageBox.information(self, "Подсказка",
                    "Сначала добавьте классы на вкладке «Классы».")
                return
            if not subjects:
                QMessageBox.information(self, "Подсказка",
                    "Сначала добавьте предметы на вкладке «Предметы».")
                return
            dlg = ClassSubjectDialog(self, classes=classes, subjects=subjects)
            if dlg.exec() == ClassSubjectDialog.Accepted and dlg.result_data:
                cs = ClassSubject(**dlg.result_data)
                session.add(cs)
                session.commit()
        self.refresh()

    def _edit_class_subject(self):
        row = self.cs_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Подсказка", "Выберите предмет класса.")
            return
        item = self.cs_table.item(row, 0)
        if item is None or not item.text().isdigit():
            return
        cs_id = int(item.text())
        with make_session(self.engine) as session:
            cs = session.get(ClassSubject, cs_id)
            if not cs:
                return
            classes = session.execute(select(SchoolClass)).scalars().all()
            subjects = session.execute(select(Subject)).scalars().all()
            dlg = ClassSubjectDialog(self, class_subject=cs,
                                     classes=classes, subjects=subjects)
            if dlg.exec() == ClassSubjectDialog.Accepted and dlg.result_data:
                for k, v in dlg.result_data.items():
                    setattr(cs, k, v)
                session.commit()
        self.refresh()

    def _delete_class_subject(self):
        row = self.cs_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Подсказка", "Выберите предмет класса.")
            return
        item = self.cs_table.item(row, 0)
        if item is None or not item.text().isdigit():
            return
        cs_id = int(item.text())
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Удалить предмет из учебного плана?\nВсе подгруппы этого предмета будут удалены.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        with make_session(self.engine) as session:
            cs = session.get(ClassSubject, cs_id)
            if cs:
                session.delete(cs)
                session.commit()
        self.refresh()

    def _add_subject_group(self):
        if self.cs_table.currentRow() < 0:
            QMessageBox.information(self, "Подсказка",
                "Сначала выберите предмет класса в таблице выше.")
            return
        item = self.cs_table.item(self.cs_table.currentRow(), 0)
        if item is None or not item.text().isdigit():
            return
        cs_id = int(item.text())
        with make_session(self.engine) as session:
            cs_list = self._build_cs_list(session)
            teachers = session.execute(select(Teacher)).scalars().all()
            if not teachers:
                QMessageBox.information(self, "Подсказка",
                    "Сначала добавьте учителей на вкладке «Учителя».")
                return
            cabinets = session.execute(select(Cabinet)).scalars().all()
            dlg = SubjectGroupDialog(
                self, class_subjects=cs_list, teachers=teachers,
                cabinets=cabinets, current_class_subject_id=cs_id,
            )
            if dlg.exec() == SubjectGroupDialog.Accepted and dlg.result_data:
                sg = SubjectGroup(**dlg.result_data)
                session.add(sg)
                session.commit()
        self.refresh()

    def _edit_subject_group(self):
        row = self.sg_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Подсказка", "Выберите подгруппу.")
            return
        item = self.sg_table.item(row, 0)
        if item is None or not item.text().isdigit():
            return
        sg_id = int(item.text())
        with make_session(self.engine) as session:
            sg = session.get(SubjectGroup, sg_id)
            if not sg:
                return
            cs_list = self._build_cs_list(session)
            teachers = session.execute(select(Teacher)).scalars().all()
            cabinets = session.execute(select(Cabinet)).scalars().all()
            dlg = SubjectGroupDialog(
                self, subject_group=sg, class_subjects=cs_list,
                teachers=teachers, cabinets=cabinets,
            )
            if dlg.exec() == SubjectGroupDialog.Accepted and dlg.result_data:
                for k, v in dlg.result_data.items():
                    setattr(sg, k, v)
                session.commit()
        self.refresh()

    def _delete_subject_group(self):
        row = self.sg_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Подсказка", "Выберите подгруппу.")
            return
        item = self.sg_table.item(row, 0)
        if item is None or not item.text().isdigit():
            return
        sg_id = int(item.text())
        reply = QMessageBox.question(
            self, "Подтверждение", "Удалить подгруппу?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        with make_session(self.engine) as session:
            sg = session.get(SubjectGroup, sg_id)
            if sg:
                session.delete(sg)
                session.commit()
        self.refresh()

    def _fill_profiles(self, session):
        rows = session.execute(select(ClassSubject)).scalars().all()
        profile_map = {}
        cs_info = {}
        for cs in rows:
            class_obj = session.get(SchoolClass, cs.class_id)
            subj_obj = session.get(Subject, cs.subject_id)
            class_label = f"{class_obj.grade}{class_obj.letter}" if class_obj else "?"
            subj_name = subj_obj.name if subj_obj else "?"
            cs_info[cs.id] = {
                "cs_id": cs.id, "class_id": cs.class_id,
                "class_label": class_label, "subject_name": subj_name,
                "profile_id": cs.profile_id,
            }
            if cs.profile_id is not None:
                key = (cs.class_id, cs.profile_id)
                profile_map.setdefault(key, []).append(cs.id)

        self._cs_info_cache = cs_info

        table_rows = []
        for (class_id, pid), cs_ids in sorted(profile_map.items()):
            if len(cs_ids) >= 2:
                s1 = cs_info.get(cs_ids[0], {})
                s2 = cs_info.get(cs_ids[1], {})
                table_rows.append((pid, s1.get("class_label", "?"),
                                   s1.get("subject_name", "?"),
                                   s2.get("subject_name", "?"), pid))

        self.profiles_table.setRowCount(len(table_rows))
        for i, (pid, cls_label, s1, s2, pid_val) in enumerate(table_rows):
            self._set_row(self.profiles_table, i, [
                str(i + 1), cls_label, s1, s2, str(pid_val),
            ])

    def _add_profile(self):
        with make_session(self.engine) as session:
            cs_rows = session.execute(select(ClassSubject)).scalars().all()
            if len(cs_rows) < 2:
                QMessageBox.information(self, "Подсказка",
                    "Нужно минимум два предмета класса для создания профиля.")
                return
            cs_list = []
            for cs in cs_rows:
                class_obj = session.get(SchoolClass, cs.class_id)
                subj_obj = session.get(Subject, cs.subject_id)
                if class_obj and subj_obj:
                    cs_list.append({
                        "cs_id": cs.id,
                        "class_id": cs.class_id,
                        "class_label": f"{class_obj.grade}{class_obj.letter}",
                        "subject_name": subj_obj.name,
                        "profile_id": cs.profile_id,
                    })

            dlg = ProfileDialog(self, engine=self.engine,
                                existing_class_subjects=cs_list)
            if dlg.exec() == ProfileDialog.Accepted and dlg.result_data:
                data = dlg.result_data
                cs1_id = data["cs1_id"]
                cs2_id = data["cs2_id"]

                existing_pids = [
                    cs.profile_id for cs in cs_rows
                    if cs.profile_id is not None
                ]
                new_pid = (max(existing_pids) + 1) if existing_pids else 1

                cs1 = session.get(ClassSubject, cs1_id)
                cs2 = session.get(ClassSubject, cs2_id)
                if cs1 and cs2:
                    if cs1.profile_id is not None or cs2.profile_id is not None:
                        QMessageBox.warning(self, "Ошибка",
                            "Один из выбранных предметов уже состоит в профильной паре.\n"
                            "Сначала удалите старую профильную связь.")
                        return
                    cs1.profile_id = new_pid
                    cs2.profile_id = new_pid
                    session.commit()
        self.refresh()

    def _delete_profile(self):
        row = self.profiles_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Подсказка", "Выберите профильную пару.")
            return
        pid_item = self.profiles_table.item(row, 4)
        if pid_item is None or not pid_item.text().isdigit():
            return
        pid = int(pid_item.text())
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Разорвать профильную связь?\n"
            "Предметы останутся в учебном плане, но перестанут быть профильной парой.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        with make_session(self.engine) as session:
            cs_rows = session.execute(
                select(ClassSubject).where(ClassSubject.profile_id == pid)
            ).scalars().all()
            for cs in cs_rows:
                cs.profile_id = None
            session.commit()
        self.refresh()

    def _build_cs_list(self, session):
        class CsItem:
            def __init__(self, id, class_label, subject_name):
                self.id = id
                self.class_label = class_label
                self.subject_name = subject_name
        items = []
        rows = session.execute(select(ClassSubject)).scalars().all()
        for cs in rows:
            class_obj = session.get(SchoolClass, cs.class_id)
            subj_obj = session.get(Subject, cs.subject_id)
            if class_obj and subj_obj:
                items.append(CsItem(
                    cs.id,
                    f"{class_obj.grade}{class_obj.letter}",
                    subj_obj.name,
                ))
        return items
