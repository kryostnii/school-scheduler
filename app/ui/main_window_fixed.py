"""Рабочий графический прототип генератора школьного расписания."""
import sys

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
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
    ScheduleContext,
    SubjectGroupInfo,
    run_genetic_algorithm,
)


DAY_NAMES = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб"]
SAMPLE_CLASSES = {101: "5А", 102: "5Б", 201: "2А"}


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
    """GUI-прототип: тестовые данные → реальный алгоритм → таблица результата."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Школьное расписание — рабочий прототип")
        self.resize(1100, 760)
        self.ctx, self.subject_names = build_sample_context()
        self.worker = None
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
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(title)

        intro = QLabel(
            "Рабочий прототип: оптимизатор запускается на тестовой школе и "
            "показывает фактические конфликты и результат поиска. "
            "Пользовательские данные и импорт пока не подключены."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("color: #566573; padding: 4px;")
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
        buttons.addWidget(self.run_button)
        buttons.addWidget(self.stop_button)
        buttons.addStretch()
        layout.addLayout(buttons)

        self.progress = QProgressBar()
        self.progress.setRange(0, self.generations_spin.value())
        self.progress.setFormat("Ожидание запуска")
        layout.addWidget(self.progress)

        result_group = QGroupBox("Результат и ход поиска")
        result_layout = QVBoxLayout(result_group)
        self.results = QTextEdit()
        self.results.setReadOnly(True)
        self.results.setMaximumHeight(150)
        result_layout.addWidget(self.results)
        layout.addWidget(result_group)

        schedule_group = QGroupBox("Расписание выбранного класса")
        schedule_layout = QVBoxLayout(schedule_group)
        self.schedule_table = QTableWidget(10, 6)
        self.schedule_table.setHorizontalHeaderLabels(DAY_NAMES)
        self.schedule_table.setVerticalHeaderLabels([f"Урок {i}" for i in range(1, 11)])
        self.schedule_table.horizontalHeader().setSectionResizeMode(
            self.schedule_table.horizontalHeader().Stretch
        )
        self.schedule_table.setEditTriggers(QTableWidget.NoEditTriggers)
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

        self.worker = GenerationWorker(self.ctx, params, self)
        self.worker.progress.connect(self._on_progress)
        self.worker.completed.connect(self._on_completed)
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
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.worker = None

        if error:
            self.progress.setFormat("Поиск остановлен или завершился ошибкой")
            self.results.append(error)
            self.statusBar().showMessage(error)
            return

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

    def _render_schedule(self):
        self.schedule_table.clearContents()
        if not self.result or not self.result.best:
            return
        class_id = self.class_combo.currentData()
        slots: dict[tuple[int, int], list[str]] = {}
        for index, instance in enumerate(self.ctx.lesson_instances):
            group = self.ctx.groups[instance.group_index]
            if group.class_id != class_id:
                continue
            gene = self.result.best[index]
            label = self.subject_names.get(group.id, f"Предмет {group.id}")
            slots.setdefault((gene.day, gene.lesson_number), []).append(label)

        for (day, lesson), subjects in slots.items():
            if not (1 <= day <= 6 and 1 <= lesson <= self.schedule_table.rowCount()):
                continue
            text = " / ".join(subjects)
            item = QTableWidgetItem(text)
            item.setTextAlignment(Qt.AlignCenter)
            item.setBackground(QColor("#fdebd0" if len(subjects) > 1 else "#eaf2f8"))
            if len(subjects) > 1:
                item.setToolTip("В одном слоте несколько уроков: проверьте конфликт")
            self.schedule_table.setItem(lesson - 1, day - 1, item)

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
    window = SchoolSchedulerMainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
