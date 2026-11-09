"""Рабочий графический прототип генератора школьного расписания."""
import gc
import json
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.services.reference_scheduler import GAParams, GAResult, Gene, evaluate, run_genetic_algorithm
from app.services.school_data import (
    build_context,
    load_school_data,
    sample_school_data,
    validate_school_data,
)
from app.services.schedule_files import load_schedule_document, make_schedule_document

DAY_NAMES = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
SUBJECT_COLORS = [
    "#d6eaf8", "#d5f5e3", "#fcf3cf", "#fadbd8", "#e8daef",
    "#d1f2eb", "#f5cba7", "#d6dbdf", "#f9e79f", "#aed6f1",
]


class GenerationWorker(QThread):
    """Выполняет поиск вне GUI-потока и отправляет безопасные Qt-сигналы."""

    progress = Signal(int, float, int)
    completed = Signal(object, str)

    def __init__(self, context, params, parent=None):
        super().__init__(parent)
        self.context = context
        self.params = params
        self._stop_requested = False

    def run(self):
        def report_progress(generation, fitness, hard_conflicts):
            if self._stop_requested:
                raise InterruptedError("Поиск остановлен пользователем")
            self.progress.emit(generation, fitness, hard_conflicts)

        try:
            result = run_genetic_algorithm(self.context, self.params, report_progress)
        except InterruptedError as exc:
            self.completed.emit(None, str(exc))
        except Exception as exc:
            self.completed.emit(None, f"{type(exc).__name__}: {exc}")
        else:
            self.completed.emit(result, "")

    def stop(self):
        self._stop_requested = True


class SchoolSchedulerMainWindow(QMainWindow):
    """Генерация, ручная правка, импорт школы и переносимые JSON-расписания."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Школьное расписание — рабочий прототип")
        self.resize(1120, 800)
        self.school_data = validate_school_data(sample_school_data())
        self.context, self.subject_names, self.class_names = build_context(self.school_data)
        self.worker = None
        self._worker_completed = False
        self._worker_thread_stopped = False
        self.result = None
        self._setup_ui()
        self._refresh_school_summary()

    def _setup_ui(self):
        central = QWidget(self)
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        title = QLabel("Генератор школьного расписания")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #263238;")
        layout.addWidget(title)

        self.school_label = QLabel()
        self.school_label.setWordWrap(True)
        self.school_label.setStyleSheet("color: #455a64; padding: 4px;")
        layout.addWidget(self.school_label)

        actions = QHBoxLayout()
        self.open_school_button = QPushButton("📂 Открыть данные школы")
        self.open_school_button.clicked.connect(self.open_school_data)
        self.save_school_button = QPushButton("💾 Сохранить данные школы")
        self.save_school_button.clicked.connect(self.save_school_data)
        actions.addWidget(self.open_school_button)
        actions.addWidget(self.save_school_button)
        actions.addStretch()
        layout.addLayout(actions)

        settings = QGroupBox("Параметры генерации")
        form = QFormLayout(settings)
        self.class_combo = QComboBox()
        self.class_combo.currentIndexChanged.connect(self._render_schedule)
        form.addRow("Показать класс:", self.class_combo)
        self.population_spin = QSpinBox()
        self.population_spin.setRange(10, 500)
        self.population_spin.setValue(60)
        form.addRow("Размер популяции:", self.population_spin)
        self.generations_spin = QSpinBox()
        self.generations_spin.setRange(10, 2000)
        self.generations_spin.setValue(300)
        form.addRow("Поколения:", self.generations_spin)
        layout.addWidget(settings)

        buttons = QHBoxLayout()
        self.run_button = QPushButton("▶ Запустить генерацию")
        self.run_button.clicked.connect(self.run_optimization)
        self.stop_button = QPushButton("■ Остановить")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_optimization)
        buttons.addWidget(self.run_button)
        buttons.addWidget(self.stop_button)
        buttons.addStretch()
        self.open_schedule_button = QPushButton("Открыть расписание")
        self.open_schedule_button.clicked.connect(self.open_schedule)
        self.save_schedule_button = QPushButton("Сохранить расписание")
        self.save_schedule_button.clicked.connect(self.save_schedule)
        buttons.addWidget(self.open_schedule_button)
        buttons.addWidget(self.save_schedule_button)
        layout.addLayout(buttons)

        self.progress = QProgressBar()
        self.progress.setRange(0, self.generations_spin.value())
        self.progress.setFormat("Ожидание запуска")
        layout.addWidget(self.progress)

        result_group = QGroupBox("Результат и ход поиска")
        result_layout = QVBoxLayout(result_group)
        self.results = QTextEdit()
        self.results.setReadOnly(True)
        self.results.setMaximumHeight(135)
        result_layout.addWidget(self.results)
        layout.addWidget(result_group)

        self.schedule_group = QGroupBox()
        schedule_layout = QVBoxLayout(self.schedule_group)
        self.schedule_table = QTableWidget(10, 6)
        self.schedule_table.setVerticalHeaderLabels([f"Урок {i}" for i in range(1, 11)])
        self.schedule_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.schedule_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.schedule_table.cellDoubleClicked.connect(self._edit_schedule_cell)
        schedule_layout.addWidget(self.schedule_table)
        layout.addWidget(self.schedule_group, stretch=1)

    def _refresh_school_summary(self):
        days = self.school_data["days_per_week"]
        self.school_label.setText(
            f"Школа: {self.school_data['school_name']} · "
            f"классов: {len(self.school_data['classes'])} · "
            f"учебных групп: {len(self.context.groups)} · "
            f"часов в неделю: {len(self.context.lesson_instances)} · дней: {days}"
        )
        self.class_combo.blockSignals(True)
        current_id = self.class_combo.currentData()
        self.class_combo.clear()
        for item in self.school_data["classes"]:
            self.class_combo.addItem(item["name"], item["id"])
        index = self.class_combo.findData(current_id)
        if index >= 0:
            self.class_combo.setCurrentIndex(index)
        self.class_combo.blockSignals(False)
        self.schedule_table.setColumnCount(days)
        self.schedule_table.setHorizontalHeaderLabels(DAY_NAMES[:days])
        self.schedule_group.setTitle(
            f"Расписание: {self.class_combo.currentText()} — двойной щелчок для перемещения"
        )
        self._render_schedule()

    def open_school_data(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Открыть данные школы", "", "Данные школы (*.json)"
        )
        if not filename:
            return
        try:
            school = load_school_data(filename)
            context, subjects, classes = build_context(school)
        except (OSError, UnicodeError, ValueError) as exc:
            QMessageBox.critical(self, "Ошибка загрузки данных", str(exc))
            return
        self.school_data = school
        self.context, self.subject_names, self.class_names = context, subjects, classes
        self.result = None
        self.results.clear()
        self.schedule_table.clearContents()
        self._refresh_school_summary()
        self.statusBar().showMessage(f"Данные школы загружены: {filename}")

    def save_school_data(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Сохранить данные школы", "school-data.json", "Данные школы (*.json)"
        )
        if not filename:
            return
        path = Path(filename)
        if path.suffix.lower() != ".json":
            path = path.with_suffix(".json")
        try:
            path.write_text(json.dumps(self.school_data, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:
            QMessageBox.critical(self, "Ошибка сохранения данных", str(exc))
            return
        self.statusBar().showMessage(f"Данные школы сохранены: {path}")

    def run_optimization(self):
        if self.worker and self.worker.isRunning():
            return
        if not self.context.lesson_instances:
            QMessageBox.warning(self, "Нет данных", "В учебных группах нет часов для генерации.")
            return
        params = GAParams(
            population_size=self.population_spin.value(),
            max_generations=self.generations_spin.value(),
            mutation_rate=0.1,
            random_seed=42,
        )
        self.result = None
        self.schedule_table.clearContents()
        self.results.clear()
        self.results.append(
            f"Генерация: {self.school_data['school_name']}; "
            f"{len(self.context.groups)} групп; {len(self.context.lesson_instances)} часов."
        )
        self.progress.setRange(0, params.max_generations)
        self.progress.setValue(0)
        self.progress.setFormat("Поиск расписания…")
        self.run_button.setEnabled(False)
        self.open_school_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self._worker_completed = False
        self._worker_thread_stopped = False
        self.worker = GenerationWorker(self.context, params, self)
        self.worker.progress.connect(self._on_progress)
        self.worker.completed.connect(self._on_completed)
        self.worker.finished.connect(self._on_worker_thread_finished)
        self.worker.start()
        self.statusBar().showMessage("Алгоритм выполняется в фоновом потоке")

    def stop_optimization(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.stop_button.setEnabled(False)
            self.statusBar().showMessage("Остановка после текущего поколения…")

    def _on_progress(self, generation, fitness, hard_conflicts):
        self.progress.setValue(generation)
        self.progress.setFormat(f"Поколение {generation}: ошибок {hard_conflicts}")
        if generation == 1 or generation % 25 == 0:
            self.results.append(
                f"Поколен��е {generation}: жёстких конфликтов {hard_conflicts}, штраф {fitness:.1f}"
            )

    def _on_completed(self, result, error):
        self._worker_completed = True
        self.run_button.setEnabled(True)
        self.open_school_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        if error:
            self.progress.setFormat("Поиск остановлен или завершился ошибкой")
            self.results.append(error)
            self.statusBar().showMessage(error)
        else:
            self.result = result
            fitness = result.best_fitness
            self.results.append(
                f"Завершено за {result.generations_run} поколений. "
                f"Жёстких конфликтов: {fitness.hard_conflicts}; "
                f"мягкий штраф: {fitness.soft_penalty:.1f}."
            )
            if fitness.hard_conflicts == 0:
                self.results.append("Допустимое расписание найдено относительно реализованных ограничений.")
                self.progress.setFormat("Готово — жёстких конфликтов нет")
            else:
                self.results.append("Остались жёсткие конфликты; проверьте расписание перед использованием.")
                self.progress.setFormat(f"Готово — осталось ошибок: {fitness.hard_conflicts}")
            self._render_schedule()
            self.statusBar().showMessage("Поиск завершён")
        self._release_worker_if_done()

    def _on_worker_thread_finished(self):
        self._worker_thread_stopped = True
        self._release_worker_if_done()

    def _release_worker_if_done(self):
        if self.worker and self._worker_completed and self._worker_thread_stopped:
            worker = self.worker
            self.worker = None
            worker.deleteLater()

    def _render_schedule(self):
        days = self.school_data["days_per_week"]
        self.schedule_table.clearContents()
        if not self.result or not self.result.best:
            return
        class_id = self.class_combo.currentData()
        slots = {}
        for index, instance in enumerate(self.context.lesson_instances):
            group = self.context.groups[instance.group_index]
            if group.class_id != class_id:
                continue
            gene = self.result.best[index]
            slots.setdefault((gene.day, gene.lesson_number), []).append(
                (self.subject_names.get(group.id, f"Предмет {group.id}"), index)
            )
        colors = {
            name: SUBJECT_COLORS[index % len(SUBJECT_COLORS)]
            for index, name in enumerate(sorted(set(self.subject_names.values())))
        }
        for (day, lesson), placements in slots.items():
            if not (1 <= day <= days and 1 <= lesson <= self.schedule_table.rowCount()):
                continue
            labels = [label for label, _ in placements]
            item = QTableWidgetItem(" / ".join(labels))
            item.setTextAlignment(Qt.AlignCenter)
            item.setForeground(QColor("#263238"))
            item.setBackground(QColor("#f5b7b1" if len(labels) > 1 else colors[labels[0]]))
            item.setToolTip(" / ".join(labels))
            self.schedule_table.setItem(lesson - 1, day - 1, item)

    def _edit_schedule_cell(self, row, column):
        if not self.result or not self.result.best:
            QMessageBox.information(self, "Нет расписания", "Сначала запустите генерацию или откройте файл расписания.")
            return
        class_id = self.class_combo.currentData()
        target_slot = (column + 1, row + 1)
        class_indices = [
            i for i, lesson in enumerate(self.context.lesson_instances)
            if self.context.groups[lesson.group_index].class_id == class_id
        ]
        target_indices = [
            i for i in class_indices
            if (self.result.best[i].day, self.result.best[i].lesson_number) == target_slot
        ]
        if len(target_indices) > 1:
            QMessageBox.warning(self, "Конфликтный слот", "В слоте несколько уроков; сначала выберите другой урок для перемещения.")
            return
        choices, indices = [], []
        for i in class_indices:
            instance = self.context.lesson_instances[i]
            group = self.context.groups[instance.group_index]
            gene = self.result.best[i]
            day_name = DAY_NAMES[gene.day - 1]
            choices.append(
                f"{self.subject_names[group.id]} (час {instance.occurrence + 1}) — {day_name}, урок {gene.lesson_number}"
            )
            indices.append(i)
        selected, accepted = QInputDialog.getItem(
            self, "Переместить урок", "Выберите урок для перемещения в выбранную ячейку:", choices, 0, False
        )
        if not accepted:
            return
        selected_index = indices[choices.index(selected)]
        source = self.result.best[selected_index]
        if (source.day, source.lesson_number) == target_slot:
            return
        proposed = list(self.result.best)
        if target_indices:
            other = target_indices[0]
            proposed[selected_index] = Gene(*target_slot)
            proposed[other] = Gene(source.day, source.lesson_number)
        else:
            proposed[selected_index] = Gene(*target_slot)
        new_fitness = evaluate(proposed, self.context)
        old_fitness = self.result.best_fitness
        if new_fitness.hard_conflicts > old_fitness.hard_conflicts:
            answer = QMessageBox.question(
                self, "Изменение добавляет конфликты",
                f"Жёстких конфликтов станет {new_fitness.hard_conflicts} вместо {old_fitness.hard_conflicts}. Применить?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
        self.result = GAResult(proposed, new_fitness, self.result.generations_run)
        self._render_schedule()
        self.results.append(
            f"Правка применена. Жёстких конфликтов: {new_fitness.hard_conflicts}; "
            f"мягкий штраф: {new_fitness.soft_penalty:.1f}."
        )
        self.statusBar().showMessage("Расписание изменено; сохраните результат в JSON")

    def save_schedule(self):
        if not self.result or not self.result.best:
            QMessageBox.information(self, "Нет расписания", "Сначала сгенерируйте или откройте расписание.")
            return
        filename, _ = QFileDialog.getSaveFileName(
            self, "Сохранить расписание", "school-schedule.json", "Расписание (*.json)"
        )
        if not filename:
            return
        path = Path(filename)
        if path.suffix.lower() != ".json":
            path = path.with_suffix(".json")
        try:
            document = make_schedule_document(self.school_data, self.context, self.result.best)
            path.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Ошибка сохранения расписания", str(exc))
            return
        self.results.append(f"Расписание сохранено: {path}")
        self.statusBar().showMessage(f"Расписание сохранено: {path}")

    def open_schedule(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Открыть расписание", "", "Расписание (*.json)"
        )
        if not filename:
            return
        try:
            document = json.loads(Path(filename).read_text(encoding="utf-8"))
            school, context, subjects, classes, chromosome = load_schedule_document(document)
        except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            QMessageBox.critical(self, "Ошибка открытия расписания", str(exc))
            return
        self.school_data = school
        self.context, self.subject_names, self.class_names = context, subjects, classes
        self.result = GAResult(chromosome, evaluate(chromosome, context), 0)
        self.results.clear()
        self.results.append(
            f"Открыто расписание: {filename}. Жёстких конфликтов: "
            f"{self.result.best_fitness.hard_conflicts}; "
            f"мягкий штраф: {self.result.best_fitness.soft_penalty:.1f}."
        )
        self._refresh_school_summary()
        self.statusBar().showMessage(f"Расписание открыто: {filename}")

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(5000)
            if self.worker.isRunning():
                QMessageBox.warning(self, "Поиск ещё выполняется", "Дождитесь завершения поиска и закройте окно ещё раз.")
                event.ignore()
                return
        event.accept()


def main():
    # Work around the reproducible PySide6/Shiboken cyclic-GC shutdown crash on Fedora.
    gc.disable()
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet("""
        QWidget { background: #ffffff; color: #263238; }
        QGroupBox { border: 1px solid #cfd8dc; border-radius: 6px; margin-top: 10px; padding: 10px; font-weight: bold; }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        QPushButton { background: #f5f7f8; border: 1px solid #b0bec5; border-radius: 5px; padding: 7px 12px; color: #263238; }
        QPushButton:hover { background: #e8f1f5; }
        QPushButton:disabled { color: #90a4ae; background: #eceff1; }
        QComboBox, QSpinBox, QTextEdit { background: #ffffff; border: 1px solid #b0bec5; border-radius: 4px; padding: 4px; }
        QTableWidget { background: #ffffff; alternate-background-color: #f8fafb; gridline-color: #cfd8dc; selection-background-color: #bbdefb; }
        QHeaderView::section { background: #eceff1; color: #263238; padding: 5px; border: 1px solid #cfd8dc; font-weight: bold; }
        QProgressBar { background: #eceff1; border: 1px solid #b0bec5; border-radius: 4px; text-align: center; min-height: 18px; }
        QProgressBar::chunk { background: #81c784; border-radius: 3px; }
        QStatusBar { background: #f5f7f8; color: #455a64; }
    """)
    palette = app.palette()
    palette.setColor(QPalette.Window, QColor("#ffffff"))
    palette.setColor(QPalette.Base, QColor("#ffffff"))
    palette.setColor(QPalette.Text, QColor("#263238"))
    palette.setColor(QPalette.WindowText, QColor("#263238"))
    app.setPalette(palette)
    window = SchoolSchedulerMainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
