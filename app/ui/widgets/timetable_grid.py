"""Интерактивная сетка расписания с цветовой кодировкой и drag-and-drop обменом."""
from PySide6.QtWidgets import (
    QWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QVBoxLayout, QAbstractItemView, QMenu,
)
from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtGui import QColor, QFont, QPen, QBrush, QAction

from app.config import DAY_NAMES_RU as _DAY_NAMES, MAX_LESSONS as _APP_MAX_LESSONS

DAY_NAMES = list(_DAY_NAMES[1:])

SUBJECT_COLORS = [
    QColor("#3498db"), QColor("#e74c3c"), QColor("#2ecc71"),
    QColor("#f39c12"), QColor("#9b59b6"), QColor("#1abc9c"),
    QColor("#e67e22"), QColor("#34495e"), QColor("#16a085"),
    QColor("#c0392b"), QColor("#b03a2e"), QColor("#8e44ad"),
]

EMPTY_COLOR = QColor("#ffffff")
HEADER_BG = "#2c3e50"
HEADER_FG = "#ffffff"


def _conflict_tint(base):
    """Смешивает базовый цвет предмета с красным, чтобы подсветить конфликт."""
    base = QColor(base)
    blend = 0.45
    return QColor(
        int(base.red() * (1 - blend) + 231 * blend),
        int(base.green() * (1 - blend) + 76 * blend),
        int(base.blue() * (1 - blend) + 60 * blend),
    )


class TimetableCell:
    __slots__ = (
        "subject_id", "subject_name", "teacher_name", "cabinet",
        "group_number", "is_split", "is_conflict", "color",
        "class_label", "day", "lesson",
        "is_profile_split",
        "subject_id2", "subject_name2", "teacher_name2", "cabinet2", "color2",
    )

    def __init__(self, subject_id=0, subject_name="", teacher_name="",
                 cabinet="", group_number=1, is_split=False,
                 is_conflict=False, color=None, class_label="",
                 day=0, lesson=0,
                 is_profile_split=False,
                 subject_id2=0, subject_name2="", teacher_name2="",
                 cabinet2="", color2=None):
        self.subject_id = subject_id
        self.subject_name = subject_name
        self.teacher_name = teacher_name
        self.cabinet = cabinet
        self.group_number = group_number
        self.is_split = is_split
        self.is_conflict = is_conflict
        self.color = color or EMPTY_COLOR
        self.class_label = class_label
        self.day = day
        self.lesson = lesson
        self.is_profile_split = is_profile_split
        self.subject_id2 = subject_id2
        self.subject_name2 = subject_name2
        self.teacher_name2 = teacher_name2
        self.cabinet2 = cabinet2
        self.color2 = color2 or EMPTY_COLOR

    @property
    def is_empty(self):
        return self.subject_id == 0

    def display_text(self):
        if self.is_empty:
            return ""
        if self.is_profile_split:
            left = self.subject_name
            right = self.subject_name2
            text = f"{left} | {right}"
        else:
            text = self.subject_name
            if self.is_split:
                text += f" (гр.{self.group_number})"
            if self.class_label:
                text += f" [{self.class_label}]"
        if self.is_conflict:
            text = "⚠  " + text
        return text

    def tooltip_text(self):
        if self.is_empty:
            return ""
        if self.is_profile_split:
            parts = [
                f"<b>Профильная пара:</b>",
                f"<b>{self.subject_name}</b> — {self.teacher_name}",
                f"<b>{self.subject_name2}</b> — {self.teacher_name2}",
            ]
            if self.cabinet:
                parts.append(f"Кабинет: {self.cabinet}")
            if self.class_label:
                parts.append(f"Класс: {self.class_label}")
            if self.is_conflict:
                parts.append('<br><span style="color:#e74c3c"><b>Конфликт!</b></span>')
            return "<br>".join(parts)
        parts = [f"<b>{self.subject_name}</b>"]
        if self.is_split:
            parts.append(f"Подгруппа {self.group_number}")
        parts.append(f"Учитель: {self.teacher_name}")
        if self.cabinet:
            parts.append(f"Кабинет: {self.cabinet}")
        if self.class_label:
            parts.append(f"Класс: {self.class_label}")
        if self.is_conflict:
            parts.append('<br><span style="color:#e74c3c"><b>Конфликт!</b></span>')
        return "<br>".join(parts)


class CellItem(QTableWidgetItem):
    def __init__(self, cell: TimetableCell):
        super().__init__()
        self.cell = cell
        self.setText(cell.display_text())
        self.setTextAlignment(Qt.AlignCenter)
        self.setFont(QFont("Segoe UI", 8 if cell.class_label else 9, QFont.Bold if not cell.is_empty else QFont.Normal))
        self.setToolTip(cell.tooltip_text())
        self._apply_style()

    def _apply_style(self):
        c = self.cell
        if c.is_empty:
            self.setBackground(EMPTY_COLOR)
            self.setForeground(QColor("#d5d8dc"))
        elif c.is_conflict:
            lighter = _conflict_tint(c.color)
            self.setBackground(lighter)
            self.setForeground(QColor("#2c3e50"))
        else:
            self.setBackground(c.color)
            fg = QColor("white") if c.color.lightness() < 160 else QColor("#2c3e50")
            self.setForeground(fg)


class SplitCellWidget(QWidget):
    def __init__(self, cell: TimetableCell, parent=None):
        super().__init__(parent)
        self.cell = cell
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setToolTip(cell.tooltip_text())
        self._click_callback = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self._click_callback:
            self._click_callback()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QPen, QFontMetrics
        c = self.cell
        w = self.width()
        h = self.height()
        half = w // 2

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        def draw_half(x, w_half, color, name, teacher):
            if c.is_conflict:
                bg = _conflict_tint(color)
            else:
                bg = QColor(color)
            painter.fillRect(x, 0, w_half, h, bg)
            painter.setPen(QPen(QColor("#d5d8dc"), 1))
            painter.drawLine(x, 0, x, h)

            fg = QColor("white") if bg.lightness() < 160 else QColor("#2c3e50")
            painter.setPen(fg)

            name_font = QFont("Segoe UI", 8, QFont.Bold)
            teacher_font = QFont("Segoe UI", 7)
            fm_name = QFontMetrics(name_font)
            fm_teacher = QFontMetrics(teacher_font)

            name_rect_w = w_half - 8
            name_elided = fm_name.elidedText(name, Qt.ElideRight, name_rect_w)
            teacher_elided = fm_teacher.elidedText(teacher, Qt.ElideRight, name_rect_w)

            text_block_h = fm_name.height() + fm_teacher.height() + 2
            y_start = (h - text_block_h) // 2

            painter.setFont(name_font)
            painter.drawText(x + 4, y_start, name_rect_w, fm_name.height(), Qt.AlignCenter, name_elided)

            painter.setFont(teacher_font)
            painter.drawText(x + 4, y_start + fm_name.height() + 2, name_rect_w, fm_teacher.height(), Qt.AlignCenter, teacher_elided)

        draw_half(0, half, c.color, c.subject_name, c.teacher_name)
        draw_half(half, w - half, c.color2, c.subject_name2, c.teacher_name2)

        if c.is_conflict:
            painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
            painter.setPen(QColor("#c0392b"))
            painter.drawText(w - 18, h - 5, "⚠")

        border_pen = QPen(QColor("#d5d8dc"), 1)
        painter.setPen(border_pen)
        painter.drawRect(0, 0, w - 1, h - 1)

        painter.end()


class TimetableGrid(QWidget):
    """Сетка расписания: дни (столбцы) x уроки (строки).

    Режим просмотра: клик показывает информацию.
    Режим редактирования: drag-and-drop между ячейками.
    """

    cell_clicked = Signal(int, int, object)
    cell_dropped = Signal(int, int, int, int)
    cell_copy = Signal(int, int, object)
    cell_delete = Signal(int, int, object)
    cell_edit = Signal(int, int, object)

    def __init__(self, parent=None, max_lessons=_APP_MAX_LESSONS, days=6):
        super().__init__(parent)
        self._max_lessons = max_lessons
        self._days = days
        self._cells: dict[tuple[int, int], TimetableCell] = {}
        self._subject_colors: dict[int, QColor] = {}
        self._color_index = 0
        self._edit_mode = False

        # Drag state
        self._drag_source: tuple[int, int] | None = None
        self._drag_start_pos = None
        self._drag_target: tuple[int, int] | None = None
        self._source_border_items: list = []
        self._split_widgets: dict[tuple[int, int], SplitCellWidget] = {}

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget()
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setShowGrid(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setDefaultSectionSize(64)
        self.table.verticalHeader().setMinimumSectionSize(50)
        self.table.setDragEnabled(False)
        self.table.setAcceptDrops(False)
        self.table.viewport().setAcceptDrops(False)
        self.table.viewport().installEventFilter(self)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_context_menu)

        self.table.cellClicked.connect(self._on_click)

        layout.addWidget(self.table)

    def set_edit_mode(self, enabled):
        self._edit_mode = enabled
        self._drag_source = None
        self._drag_start_pos = None
        self._drag_target = None
        self._clear_cell_borders()
        if enabled:
            self.table.setCursor(Qt.OpenHandCursor)
        else:
            self.table.setCursor(Qt.ArrowCursor)

    def set_schedule(self, entries):
        self._cells.clear()
        self._drag_source = None
        self._drag_start_pos = None
        self._drag_target = None
        self._clear_cell_borders()

        self.table.setColumnCount(self._days + 1)
        self.table.setRowCount(self._max_lessons)

        headers = ["  "] + [f"  {DAY_NAMES[d]}  " for d in range(self._days)]
        self.table.setHorizontalHeaderLabels(headers)

        no_select_style = (
            "QTableWidget { background-color: white; gridline-color: #e3e6ea; "
            "border: 1px solid #d5d8dc; border-radius: 6px; font-size: 11px; }"
            "QHeaderView::section { background-color: #2c3e50; color: white; "
            "border: none; padding: 12px 4px; font-weight: bold; font-size: 12px; }"
            "QHeaderView::section:first { border-top-left-radius: 6px; }"
            "QHeaderView::section:last { border-top-right-radius: 6px; }"
        )
        self.table.setStyleSheet(no_select_style)

        for lesson in range(1, self._max_lessons + 1):
            item = QTableWidgetItem(f"  {lesson}  ")
            item.setTextAlignment(Qt.AlignCenter)
            item.setBackground(QColor(HEADER_BG))
            item.setForeground(QColor(HEADER_FG))
            item.setFont(QFont("Segoe UI", 11, QFont.Bold))
            item.setFlags(Qt.NoItemFlags)
            self.table.setItem(lesson - 1, 0, item)

        for lesson in range(1, self._max_lessons + 1):
            for day in range(1, self._days + 1):
                cell = TimetableCell(day=day, lesson=lesson)
                self._cells[(day, lesson)] = cell
                self.table.setItem(lesson - 1, day, CellItem(cell))

        self._split_widgets = {}

        for entry in entries:
            day, lesson = entry["day"], entry["lesson"]
            if (day, lesson) not in self._cells:
                continue
            color = self._get_color(entry.get("subject_id", 0))
            cell = TimetableCell(
                subject_id=entry.get("subject_id", 0),
                subject_name=entry.get("subject_name", ""),
                teacher_name=entry.get("teacher_name", ""),
                cabinet=entry.get("cabinet", ""),
                group_number=entry.get("group_number", 1),
                is_split=entry.get("is_split", False),
                is_conflict=entry.get("is_conflict", False),
                color=color,
                class_label=entry.get("class_label", ""),
                day=day, lesson=lesson,
                is_profile_split=entry.get("is_profile_split", False),
                subject_id2=entry.get("subject_id2", 0),
                subject_name2=entry.get("subject_name2", ""),
                teacher_name2=entry.get("teacher_name2", ""),
                cabinet2=entry.get("cabinet2", ""),
                color2=self._get_color(entry.get("subject_id2", 0)),
            )
            self._cells[(day, lesson)] = cell
            if cell.is_profile_split:
                self._place_split_widget(day, lesson, cell)
            else:
                self._remove_split_widget(day, lesson)
                self.table.setItem(lesson - 1, day, CellItem(cell))

    def get_cell(self, day, lesson):
        return self._cells.get((day, lesson))

    def update_cell(self, day, lesson, cell):
        self._cells[(day, lesson)] = cell
        if cell.is_profile_split:
            self._place_split_widget(day, lesson, cell)
        else:
            self._remove_split_widget(day, lesson)
            self.table.setItem(lesson - 1, day, CellItem(cell))

    def swap_cells(self, from_day, from_lesson, to_day, to_lesson):
        if (from_day, from_lesson) not in self._cells or (to_day, to_lesson) not in self._cells:
            return
        if from_day == to_day and from_lesson == to_lesson:
            return
        a = self._cells[(from_day, from_lesson)]
        b = self._cells[(to_day, to_lesson)]

        a_new = TimetableCell(
            subject_id=b.subject_id, subject_name=b.subject_name,
            teacher_name=b.teacher_name, cabinet=b.cabinet,
            group_number=b.group_number, is_split=b.is_split,
            is_conflict=b.is_conflict, color=b.color,
            class_label=b.class_label,
            day=from_day, lesson=from_lesson,
            is_profile_split=b.is_profile_split,
            subject_id2=b.subject_id2, subject_name2=b.subject_name2,
            teacher_name2=b.teacher_name2, cabinet2=b.cabinet2, color2=b.color2,
        )
        b_new = TimetableCell(
            subject_id=a.subject_id, subject_name=a.subject_name,
            teacher_name=a.teacher_name, cabinet=a.cabinet,
            group_number=a.group_number, is_split=a.is_split,
            is_conflict=a.is_conflict, color=a.color,
            class_label=a.class_label,
            day=to_day, lesson=to_lesson,
            is_profile_split=a.is_profile_split,
            subject_id2=a.subject_id2, subject_name2=a.subject_name2,
            teacher_name2=a.teacher_name2, cabinet2=a.cabinet2, color2=a.color2,
        )

        self._cells[(from_day, from_lesson)] = a_new
        self._cells[(to_day, to_lesson)] = b_new
        if a_new.is_profile_split:
            self._place_split_widget(from_day, from_lesson, a_new)
        else:
            self._remove_split_widget(from_day, from_lesson)
            self.table.setItem(from_lesson - 1, from_day, CellItem(a_new))
        if b_new.is_profile_split:
            self._place_split_widget(to_day, to_lesson, b_new)
        else:
            self._remove_split_widget(to_day, to_lesson)
            self.table.setItem(to_lesson - 1, to_day, CellItem(b_new))

    def get_color_legend(self):
        return sorted(self._subject_colors.items())

    def _get_color(self, subject_id):
        if subject_id == 0:
            return EMPTY_COLOR
        if subject_id not in self._subject_colors:
            self._subject_colors[subject_id] = SUBJECT_COLORS[
                self._color_index % len(SUBJECT_COLORS)]
            self._color_index += 1
        return self._subject_colors[subject_id]

    def _place_split_widget(self, day, lesson, cell):
        key = (day, lesson)
        if key in self._split_widgets:
            old = self._split_widgets[key]
            self.table.removeCellWidget(lesson - 1, day)
            old.deleteLater()

        dummy = QTableWidgetItem(cell.display_text())
        dummy.setToolTip(cell.tooltip_text())
        self.table.setItem(lesson - 1, day, dummy)

        w = SplitCellWidget(cell, self.table.viewport())
        d, l = day, lesson
        w._click_callback = lambda dd=d, ll=l: self._on_split_click(dd, ll)
        self.table.setCellWidget(lesson - 1, day, w)
        self._split_widgets[key] = w

        w.customContextMenuRequested.connect(
            lambda pos, d=day, l=lesson: self._on_split_context_menu(d, l, pos)
        )

    def _remove_split_widget(self, day, lesson):
        key = (day, lesson)
        if key in self._split_widgets:
            self.table.removeCellWidget(lesson - 1, day)
            w = self._split_widgets.pop(key)
            w.deleteLater()

    def _on_split_click(self, day, lesson):
        cell = self._cells.get((day, lesson))
        if cell:
            self.cell_clicked.emit(day, lesson, cell)

    def _on_split_context_menu(self, day, lesson, pos):
        cell = self._cells.get((day, lesson))
        if not cell:
            return
        widget = self.table.cellWidget(lesson - 1, day)
        if not widget:
            return
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background: white; border: 1px solid #d5d8dc; border-radius: 4px; "
            "padding: 4px; }"
            "QMenu::item { padding: 6px 20px; font-size: 12px; }"
            "QMenu::item:selected { background: #3498db; color: white; border-radius: 2px; }"
        )
        copy_action = menu.addAction("\U0001f4cb Копировать")
        copy_action.triggered.connect(lambda: self.cell_copy.emit(day, lesson, cell))
        edit_action = menu.addAction("\u270f Редактировать")
        edit_action.triggered.connect(lambda: self.cell_edit.emit(day, lesson, cell))
        menu.addSeparator()
        delete_action = menu.addAction("\U0001f5d1 Удалить")
        delete_action.triggered.connect(lambda: self.cell_delete.emit(day, lesson, cell))
        menu.exec(widget.mapToGlobal(pos))

    def _set_cell_border(self, day, lesson, color_name, width=3):
        key = (day, lesson)
        if key in self._split_widgets:
            w = self._split_widgets[key]
            w.setStyleSheet(f"SplitCellWidget {{ border: {width}px solid {color_name}; }}")
            self._source_border_items.append(key)
            return
        item = self.table.item(lesson - 1, day)
        if item:
            item.setData(Qt.UserRole + 10, item.data(Qt.UserRole + 10) or item.background().color().name())
            item.setData(Qt.UserRole + 11, item.foreground().color().name())
            border_color = QColor(color_name)
            bg = border_color.lighter(180)
            item.setBackground(bg)
            item.setForeground(QColor("#2c3e50"))
            self._source_border_items.append(key)

    def _clear_cell_borders(self):
        for key in self._source_border_items:
            day, lesson = key
            if key in self._split_widgets:
                w = self._split_widgets[key]
                w.setStyleSheet("")
                continue
            item = self.table.item(lesson - 1, day)
            if item:
                cell = self._cells.get((day, lesson))
                if cell and not cell.is_empty:
                    item.setBackground(cell.color)
                    fg = QColor("white") if cell.color.lightness() < 160 else QColor("#2c3e50")
                    item.setForeground(fg)
                else:
                    item.setBackground(EMPTY_COLOR)
                    item.setForeground(QColor("#d5d8dc"))
        self._source_border_items.clear()

    def _on_click(self, row, col):
        if col == 0:
            return
        cell = self._cells.get((col, row + 1))
        if cell:
            self.cell_clicked.emit(col, row + 1, cell)

    def eventFilter(self, obj, event):
        if self._edit_mode and obj == self.table.viewport():
            etype = event.type()

            if etype == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                idx = self.table.indexAt(event.pos())
                if idx.isValid() and idx.column() > 0:
                    cell = self._cells.get((idx.column(), idx.row() + 1))
                    if cell and not cell.is_empty:
                        self._drag_source = (idx.column(), idx.row() + 1)
                        self._drag_start_pos = event.pos()
                return False

            if etype == QEvent.MouseMove and self._drag_source:
                if not self._drag_start_pos:
                    return False
                dx = abs(event.pos().x() - self._drag_start_pos.x())
                dy = abs(event.pos().y() - self._drag_start_pos.y())
                if dx > 15 or dy > 15:
                    self.table.setCursor(Qt.ClosedHandCursor)
                    if not self._source_border_items:
                        self._set_cell_border(
                            self._drag_source[0], self._drag_source[1], "#f1c40f", 3
                        )
                    idx = self.table.indexAt(event.pos())
                    if idx.isValid() and idx.column() > 0:
                        new_target = (idx.column(), idx.row() + 1)
                        if new_target != self._drag_target:
                            self._clear_cell_borders()
                            self._set_cell_border(
                                self._drag_source[0], self._drag_source[1], "#f1c40f", 3
                            )
                            if new_target != self._drag_source:
                                self._set_cell_border(
                                    new_target[0], new_target[1], "#2ecc71", 3
                                )
                            self._drag_target = new_target
                    else:
                        self._clear_cell_borders()
                        self._set_cell_border(
                            self._drag_source[0], self._drag_source[1], "#f1c40f", 3
                        )
                        self._drag_target = None
                return True

            if etype == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
                self._clear_cell_borders()
                self._drag_target = None
                if self._drag_source:
                    was_dragging = False
                    if self._drag_start_pos:
                        if (abs(event.pos().x() - self._drag_start_pos.x()) > 15 or
                            abs(event.pos().y() - self._drag_start_pos.y()) > 15):
                            was_dragging = True
                    self.table.setCursor(Qt.OpenHandCursor)

                    if was_dragging:
                        idx = self.table.indexAt(event.pos())
                        if idx.isValid() and idx.column() > 0:
                            target = (idx.column(), idx.row() + 1)
                            if target != self._drag_source:
                                self.cell_dropped.emit(
                                    self._drag_source[0], self._drag_source[1],
                                    target[0], target[1],
                                )

                    self._drag_source = None
                    self._drag_start_pos = None
                    return True

        return super().eventFilter(obj, event)

    def _on_context_menu(self, pos):
        idx = self.table.indexAt(pos)
        if not idx.isValid() or idx.column() == 0:
            return

        day = idx.column()
        lesson = idx.row() + 1
        cell = self._cells.get((day, lesson))
        if not cell:
            return

        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background: white; border: 1px solid #d5d8dc; border-radius: 4px; "
            "padding: 4px; }"
            "QMenu::item { padding: 6px 20px; font-size: 12px; }"
            "QMenu::item:selected { background: #3498db; color: white; border-radius: 2px; }"
        )

        if not cell.is_empty:
            copy_action = menu.addAction("\U0001f4cb Копировать")
            copy_action.triggered.connect(lambda: self.cell_copy.emit(day, lesson, cell))

            edit_action = menu.addAction("\u270f Редактировать")
            edit_action.triggered.connect(lambda: self.cell_edit.emit(day, lesson, cell))

            menu.addSeparator()

            delete_action = menu.addAction("\U0001f5d1 Удалить")
            delete_action.triggered.connect(lambda: self.cell_delete.emit(day, lesson, cell))
        else:
            paste_action = menu.addAction("\U0001f4cb Вставить скопированное")
            paste_action.setEnabled(False)
            paste_action.setToolTip("Скопируйте ячейку через ПКМ на заполненной ячейке")

        menu.exec(self.table.viewport().mapToGlobal(pos))

    def clear_grid(self):
        for w in self._split_widgets.values():
            w.deleteLater()
        self._split_widgets.clear()
        self._cells.clear()
        self._drag_source = None
        self._drag_start_pos = None
        self._drag_target = None
        self._clear_cell_borders()
        for row in range(self.table.rowCount()):
            for col in range(1, self.table.columnCount()):
                self.table.removeCellWidget(row, col)
                self.table.setItem(row, col, CellItem(TimetableCell(day=col, lesson=row + 1)))
