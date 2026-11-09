"""Рабочий графический прототип генератора школьного расписания."""
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

from app.services.reference_scheduler import (
    GAParams,
    GAResult,
    Gene,
    ScheduleContext,
    SubjectGroupInfo,
    evaluate,
    run_genetic_algorithm,
)


DAY_NAMES = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб"]
SAMPLE_CLASSES = {101: "5А", 102: "5Б", 201: "2А"}
SCHEDULE_FORMAT = "school-scheduler-schedule"
SCHEDULE_VERSION = 1
SUBJECT_COLORS = [
    "#d6eaf8", "#d5f5e3", "#fcf3cf", "#fadbd8", "#e8daef",
    "#d1f2eb", "#f5cba7", "#d6dbdf", "#f9e79f", "#aed6f1",
]


def build_sample_context() -> tuple[ScheduleContext, dict[int, str]]:
    """Создать небольшие тестовые данные, включающие общих учителей и кабинеты."""
    ctx = ScheduleContext(days_per_week=6)
    subject_names: dict[int, str] = {}
    next_id = 1

    def add_group(class_id, grade, teacher_id, subject, hours, *, pe=False, heavy=False):
        nonlocal next_id
        group_id = next_id
        next_id += 1
        ctx.groups.append(SubjectGroupInfo(
            id=group_id,
            class_id=class_id,
            grade=grade,
            teacher_id=teacher_id,
            hours_per_week=hours,
            is_physical_education=pe,
            is_heavy_subject=heavy,
        ))
        subject_names[group_id] = subject

    add_group(101, 5, 1, "Математика", 5, heavy=True)
    add_group(101, 5, 2, "Русский язык", 4, heavy=True)
    add_group(101, 5, 3, "Физкультура", 2, pe=True)
    add_group(101, 5, 4, "История", 3)
    add_group(101, 5, 5, "Биология", 2)

    add_group(102, 5, 1, "Математика", 5, heavy=True)
    add_group(102, 5, 6, "Русский язык", 4, heavy=True)
    add_group(102, 5, 3, "Физкультура", 2, pe=True)
    add_group(102, 5, 7, "История", 3)
    add_group(102, 5, 8, "Биология", 2)

    add_group(201, 2, 9, "Математика", 5, heavy=True)
    add_group(201, 2, 10, "Чтение", 4)
    add_group(201, 2, 11, "Физкультура", 2, pe=True)
    add_group(201, 2, 12, "Окружающий мир", 3)

    ctx.build_lesson_instances()
    return ctx, subject_names


class GenerationWorker(QThread):
    """Выполняет поиск вне GUI-потока и отправляет безопасные Qt-сигналы."""

    progress = Signal(int, float, int)
    completed = Signal(object, str)

    def __init__(self, ctx: ScheduleContext, params: GAParams, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.params = params
        self._stop_requested = False

    def run(self):
        def report_progress(generation, fitness, hard_conflicts):
            if self._stop_requested:
                raise InterruptedError("Поиск остановлен пользователем")
            self.progress.emit(generation, fitness, hard_conflicts)

        try:
            result = run_genetic_algorithm(self.ctx, self.params, report_progress)
        except InterruptedError as exc:
            self.completed.emit(None, str(exc))
        except Exception as exc:  # Передать ошибку главному потоку, не уронить приложение.
            self.completed.emit(None, f"{type(exc).__name__}: {exc}")
        else:
            self.completed.emit(result, "")

    def stop(self):
        self._stop_requested = True


class SchoolSchedulerMainWindow(QMainWindow):
    """GUI-прототип: тестовые данные → алгоритм → ручное редактирование → файл."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Школьное расписание — рабочий прототип")
        self.resize(1100, 780)
        self.ctx, self.subject_names = build_sample_context()
        self.worker = None
        self._worker_completed = False
        self._worker_thread_stopped = False
        self.result = None
        self._setup_ui()

    def _setup_ui(self):
        central = QWidget(self)
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Генератор школьного расписания")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #263238;")
        layout.addWidget(title)

        intro = QLabel(
            "Демо-данные: запустите генерацию, затем дважды щёлкните по ячейке, "
            "чтобы переместить урок. Сохранение и открытие работают с JSON-файлами. "
            "Данные реальной школы пока не подключены."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("color: #455a64; padding: 4px;")
        layout.addWidget(intro)

        settings = QGroupBox("Параметры поиска")
        form = QFormLayout(settings)
        self.class_combo = QComboBox()
        for class_id, label in SAMPLE_CLASSES.items():
            self.class_combo.addItem(label, class_id)
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
        self.save_button = QPushButton("💾 Сохранить расписание")
        self.save_button.clicked.connect(self.save_schedule)
        self.load_button = QPushButton("📂 Открыть расписание")
        self.load_button.clicked.connect(self.load_schedule)
        buttons.addWidget(self.run_button)
        buttons.addWidget(self.stop_button)
        buttons.addStretch()
        buttons.addWidget(self.load_button)
        buttons.addWidget(self.save_button)
        layout.addLayout(buttons)

        self.progress = QProgressBar()
        self.progress.setRange(0, self.generations_spin.value())
        self.progress.setFormat("Ожидание запуска")
        layout.addWidget(self.progress)

        result_group = QGroupBox("Результат и ход поиска")
        result_layout = QVBoxLayout(result_group)
        self.results = QTextEdit()
        self.results.setReadOnly(True)
        self.results.setMaximumHeight(145)
        result_layout.addWidget(self.results)
        layout.addWidget(result_group)

        schedule_group = QGroupBox("Расписание выбранного класса — двойной щелчок для перемещения")
        schedule_layout = QVBoxLayout(schedule_group)
        self.schedule_table = QTableWidget(10, 6)
        self.schedule_table.setHorizontalHeaderLabels(DAY_NAMES)
        self.schedule_table.setVerticalHeaderLabels([f"Урок {i}" for i in range(1, 11)])
        self.schedule_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.schedule_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.schedule_table.cellDoubleClicked.connect(self._edit_schedule_cell)
        schedule_layout.addWidget(self.schedule_table)
        layout.addWidget(schedule_group, stretch=1)

        self.statusBar().showMessage(
            f"Тестовые данные: {len(self.ctx.groups)} учебных групп, "
            f"{len(self.ctx.lesson_instances)} часов в неделю"
        )

    def run_optimization(self):
        if self.worker and self.worker.isRunning():
            return
        self.ctx, self.subject_names = build_sample_context()
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
            f"Запуск реального Python-алгоритма: {len(self.ctx.groups)} групп, "
            f"{len(self.ctx.lesson_instances)} уроков-часов, "
            f"популяция {params.population_size}, поколений {params.max_generations}."
        )
        self.progress.setRange(0, params.max_generations)
        self.progress.setValue(0)
        self.progress.setFormat("Поиск расписания…")
        self.run_button.setEnabled(False)
        self.stop_button.setEnabled(True)

        self._worker_completed = False
        self._worker_thread_stopped = False
        self.worker = GenerationWorker(self.ctx, params, self)
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
                f"Поколение {generation}: жёстких конфликтов {hard_conflicts}, "
                f"общий штраф {fitness:.1f}"
            )

    def _on_completed(self, result, error):
        self._worker_completed = True
        self.run_button.setEnabled(True)
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
                f"Жёсткие конфликты: {fitness.hard_conflicts}; "
                f"мягкий штраф: {fitness.soft_penalty:.1f}; "
                f"итоговая оценка: {fitness.total():.1f}."
            )
            if fitness.hard_conflicts == 0:
                self.results.append("Допустимое расписание найдено: жёстких конфликтов нет.")
                self.progress.setFormat("Готово — жёстких конфликтов нет")
            else:
                self.results.append(
                    "Полностью допустимое расписание не найдено; результат отображён "
                    "для анализа и не объявляется успешным."
                )
                self.progress.setFormat(f"Готово — осталось ошибок: {fitness.hard_conflicts}")
            self._render_schedule()
            self.statusBar().showMessage("Поиск завершён")
        self._release_worker_if_done()

    def _on_worker_thread_finished(self):
        self._worker_thread_stopped = True
        self._release_worker_if_done()

    def _release_worker_if_done(self):
        # Не уничтожать Python-обёртку QThread до завершения и доставки результата.
        if self.worker and self._worker_completed and self._worker_thread_stopped:
            worker = self.worker
            self.worker = None
            worker.deleteLater()

    def _render_schedule(self):
        self.schedule_table.clearContents()
        if not self.result or not self.result.best:
            return
        class_id = self.class_combo.currentData()
        slots: dict[tuple[int, int], list[tuple[str, int]]] = {}
        for index, instance in enumerate(self.ctx.lesson_instances):
            group = self.ctx.groups[instance.group_index]
            if group.class_id != class_id:
                continue
            gene = self.result.best[index]
            label = self.subject_names.get(group.id, f"Предмет {group.id}")
            slots.setdefault((gene.day, gene.lesson_number), []).append((label, index))

        subject_order = {
            name: index % len(SUBJECT_COLORS)
            for index, name in enumerate(sorted(set(self.subject_names.values())))
        }
        for (day, lesson), placements in slots.items():
            if not (1 <= day <= 6 and 1 <= lesson <= self.schedule_table.rowCount()):
                continue
            labels = [label for label, _ in placements]
            item = QTableWidgetItem(" / ".join(labels))
            item.setTextAlignment(Qt.AlignCenter)
            color = "#f5b7b1" if len(labels) > 1 else SUBJECT_COLORS[subject_order[labels[0]]]
            item.setBackground(QColor(color))
            item.setForeground(QColor("#263238"))
            if len(labels) > 1:
                item.setToolTip("Несколько уроков в одном слоте: проверьте конфликт")
            else:
                item.setToolTip(labels[0])
            self.schedule_table.setItem(lesson - 1, day - 1, item)

    def _edit_schedule_cell(self, row, column):
        if not self.result or not self.result.best:
            QMessageBox.information(self, "Нет расписания", "Сначала запустите генерацию или откройте файл расписания.")
            return

        class_id = self.class_combo.currentData()
        target_slot = (column + 1, row + 1)
        class_indices = [
            index for index, instance in enumerate(self.ctx.lesson_instances)
            if self.ctx.groups[instance.group_index].class_id == class_id
        ]
        target_indices = [
            index for index in class_indices
            if (self.result.best[index].day, self.result.best[index].lesson_number) == target_slot
        ]
        if len(target_indices) > 1:
            QMessageBox.warning(
                self, "Слот содержит конфликт",
                "В целевой ячейке уже несколько уроков. Сначала устраните этот конфликт, "
                "переместив один из уроков.",
            )
            return

        choices = []
        choice_indices = []
        for index in class_indices:
            instance = self.ctx.lesson_instances[index]
            group = self.ctx.groups[instance.group_index]
            gene = self.result.best[index]
            subject = self.subject_names.get(group.id, f"Предмет {group.id}")
            position = f"{DAY_NAMES[gene.day - 1]}, урок {gene.lesson_number}"
            choices.append(f"{subject} (час {instance.occurrence + 1}) — {position}")
            choice_indices.append(index)
        if not choices:
            return

        selected, accepted = QInputDialog.getItem(
            self, "Переместить урок", "Выберите урок этого класса для перемещения:",
            choices, 0, False,
        )
        if not accepted:
            return
        selected_index = choice_indices[choices.index(selected)]
        source_gene = self.result.best[selected_index]
        if (source_gene.day, source_gene.lesson_number) == target_slot:
            return

        proposed = list(self.result.best)
        if target_indices:
            other_index = target_indices[0]
            proposed[selected_index] = Gene(target_slot[0], target_slot[1])
            proposed[other_index] = Gene(source_gene.day, source_gene.lesson_number)
        else:
            proposed[selected_index] = Gene(target_slot[0], target_slot[1])

        new_fitness = evaluate(proposed, self.ctx)
        old_fitness = self.result.best_fitness
        if new_fitness.hard_conflicts > old_fitness.hard_conflicts:
            answer = QMessageBox.question(
                self,
                "Появятся дополнительные конфликты",
                f"После изменения жёстких конфликтов станет {new_fitness.hard_conflicts} "
                f"(было {old_fitness.hard_conflicts}). Всё равно применить?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return

        self.result = GAResult(
            best=proposed,
            best_fitness=new_fitness,
            generations_run=self.result.generations_run,
        )
        self._render_schedule()
        self.results.append(
            f"Расписание вручную изменено. Жёсткие конфликты: {new_fitness.hard_conflicts}; "
            f"мягкий штраф: {new_fitness.soft_penalty:.1f}."
        )
        self.statusBar().showMessage("Изменение применено; сохраните расписание в файл")

    def _schedule_document(self):
        entries = []
        for index, instance in enumerate(self.ctx.lesson_instances):
            gene = self.result.best[index]
            group = self.ctx.groups[instance.group_index]
            entries.append({
                "group_id": group.id,
                "occurrence": instance.occurrence,
                "day": gene.day,
                "lesson": gene.lesson_number,
            })
        return {
            "format": SCHEDULE_FORMAT,
            "version": SCHEDULE_VERSION,
            "days_per_week": self.ctx.days_per_week,
            "groups": [
                {
                    "id": group.id,
                    "class_id": group.class_id,
                    "grade": group.grade,
                    "teacher_id": group.teacher_id,
                    "hours_per_week": group.hours_per_week,
                    "subject": self.subject_names.get(group.id, ""),
                }
                for group in self.ctx.groups
            ],
            "schedule": entries,
        }

    def save_schedule(self):
        if not self.result or not self.result.best:
            QMessageBox.information(self, "Нет расписания", "Сначала сгенерируйте или откройте расписание.")
            return
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Сохранить расписание", "school-schedule.json", "Файлы расписания (*.json)"
        )
        if not file_name:
            return
        path = Path(file_name)
        if path.suffix.lower() != ".json":
            path = path.with_suffix(".json")
        try:
            path.write_text(
                json.dumps(self._schedule_document(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            QMessageBox.critical(self, "Ошибка сохранения", str(exc))
            return
        self.statusBar().showMessage(f"Расписание сохранено: {path}")
        self.results.append(f"Файл расписания сохранён: {path}")

    def load_schedule(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Открыть расписание", "", "Файлы расписания (*.json)"
        )
        if not file_name:
            return
        try:
            document = json.loads(Path(file_name).read_text(encoding="utf-8"))
            chromosome = self._validate_schedule_document(document)
        except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError, KeyError) as exc:
            QMessageBox.critical(self, "Не удалось открыть расписание", str(exc))
            return

        self.result = GAResult(
            best=chromosome,
            best_fitness=evaluate(chromosome, self.ctx),
            generations_run=0,
        )
        self._render_schedule()
        self.results.append(
            f"Загружен файл: {file_name}. Жёстких конфликтов: "
            f"{self.result.best_fitness.hard_conflicts}; мягкий штраф: "
            f"{self.result.best_fitness.soft_penalty:.1f}."
        )
        self.statusBar().showMessage(f"Расписание открыто: {file_name}")

    def _validate_schedule_document(self, document):
        if not isinstance(document, dict):
            raise ValueError("Корень JSON должен быть объектом")
        if document.get("format") != SCHEDULE_FORMAT:
            raise ValueError("Это не файл расписания School Scheduler")
        if document.get("version") != SCHEDULE_VERSION:
            raise ValueError(f"Неподдерживаемая версия файла: {document.get('version')}")
        if document.get("days_per_week") != self.ctx.days_per_week:
            raise ValueError("Число дней в файле не совпадает с текущей моделью")

        expected_groups = [
            {
                "id": group.id,
                "class_id": group.class_id,
                "grade": group.grade,
                "teacher_id": group.teacher_id,
                "hours_per_week": group.hours_per_week,
                "subject": self.subject_names.get(group.id, ""),
            }
            for group in self.ctx.groups
        ]
        if document.get("groups") != expected_groups:
            raise ValueError(
                "Состав учебных групп в файле отличается от текущих демо-данных. "
                "Файлы этой версии можно открывать только в прототипе с тем же набором групп."
            )

        entries = document.get("schedule")
        if not isinstance(entries, list) or len(entries) != len(self.ctx.lesson_instances):
            raise ValueError("В файле должно быть ровно по одной записи на каждый учебный час")

        expected = {
            (instance.subject_group_id, instance.occurrence): index
            for index, instance in enumerate(self.ctx.lesson_instances)
        }
        chromosome: list[Gene | None] = [None] * len(self.ctx.lesson_instances)
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError("Запись расписания должна быть JSON-объектом")
            key = (entry.get("group_id"), entry.get("occurrence"))
            if key not in expected:
                raise ValueError(f"Неизвестный урок в файле: {key}")
            index = expected[key]
            if chromosome[index] is not None:
                raise ValueError(f"Урок {key} встречается в файле повторно")
            day, lesson = entry.get("day"), entry.get("lesson")
            group = self.ctx.groups[self.ctx.lesson_instances[index].group_index]
            if not isinstance(day, int) or not 1 <= day <= self.ctx.days_per_week:
                raise ValueError(f"Некорректный день для урока {key}: {day}")
            if not isinstance(lesson, int) or not 1 <= lesson <= self.ctx.max_lessons_for_grade(group.grade):
                raise ValueError(f"Некорректный номер урока для урока {key}: {lesson}")
            chromosome[index] = Gene(day, lesson)
        if any(gene is None for gene in chromosome):
            raise ValueError("В файле отсутствуют некоторые учебные часы")
        return chromosome

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(5000)
            if self.worker.isRunning():
                QMessageBox.warning(
                    self,
                    "Поиск ещё выполняется",
                    "Дождитесь завершения текущего поколения и закройте окно ещё раз.",
                )
                event.ignore()
                return
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet("""
        QWidget { background-color: #ffffff; color: #263238; }
        QGroupBox { border: 1px solid #cfd8dc; border-radius: 6px; margin-top: 10px;
                    padding: 10px; font-weight: bold; }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        QPushButton { background: #f5f7f8; border: 1px solid #b0bec5; border-radius: 5px;
                      padding: 7px 12px; color: #263238; }
        QPushButton:hover { background: #e8f1f5; }
        QPushButton:disabled { color: #90a4ae; background: #eceff1; }
        QComboBox, QSpinBox, QTextEdit { background: #ffffff; border: 1px solid #b0bec5;
                                         border-radius: 4px; padding: 4px; }
        QTableWidget { background: #ffffff; alternate-background-color: #f8fafb;
                       gridline-color: #cfd8dc; selection-background-color: #bbdefb; }
        QHeaderView::section { background: #eceff1; color: #263238; padding: 5px;
                               border: 1px solid #cfd8dc; font-weight: bold; }
        QProgressBar { background: #eceff1; border: 1px solid #b0bec5; border-radius: 4px;
                       text-align: center; min-height: 18px; }
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
