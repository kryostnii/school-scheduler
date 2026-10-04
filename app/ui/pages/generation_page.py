"""Страница генерации: запуск поиска расписания, прогресс, результат."""
import sqlite3
import time
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QProgressBar, QGroupBox, QFormLayout, QSpinBox, QDoubleSpinBox,
    QTextEdit, QMessageBox, QCheckBox, QFrame,
)
from PySide6.QtCore import Qt, QThread, Signal

from sqlalchemy import select

from app.data.models import (AcademicYear, SchoolClass, ClassSubject, make_session)
from app.services.db_context_builder import build_context_from_db, save_chromosome_to_db
from app.services.db_utils import find_db_path
from app.services.reference_scheduler import GAParams, run_genetic_algorithm
from app.styles import GROUPBOX_STYLE, BTN_SUCCESS, BTN_DANGER

StyleSheet = GROUPBOX_STYLE

PRESET_STYLE_TPL = (
    "QPushButton {{ padding: 12px 18px; border-radius: 6px; font-size: 12px; "
    "font-weight: bold; border: 2px solid {border}; background-color: {bg}; color: {fg}; }}"
    "QPushButton:hover {{ border-color: {hover}; }}"
    "QPushButton:pressed {{ background-color: {pressed}; }}"
)
PRESET_SELECTED_TPL = (
    "QPushButton {{ padding: 12px 18px; border-radius: 6px; font-size: 12px; "
    "font-weight: bold; border: 2px solid {border}; background-color: {bg}; color: {fg}; }}"
)

PRESETS = {
    "fast": {"label": "Быстро", "pop": 40, "gen": 150,
             "desc": "~1 мин, результат может содержать мелкие недочёты"},
    "standard": {"label": "Стандарт", "pop": 80, "gen": 400,
                 "desc": "~3 мин, хороший баланс скорости и качества"},
    "quality": {"label": "Качественно", "pop": 200, "gen": 1000,
                "desc": "~10 мин, максимально чистое расписание"},
}

class GenerationWorker(QThread):
    progress = Signal(int, float, int)
    finished = Signal(object)

    def __init__(self, db_path, year_id, params):
        super().__init__()
        self.db_path = db_path
        self.year_id = year_id
        self.params = params
        self._stopped = False

    def run(self):
        conn = sqlite3.connect(self.db_path)
        ctx = build_context_from_db(conn, self.year_id)

        def on_progress(gen, fitness, hard):
            if self._stopped:
                raise InterruptedError("Остановлено пользователем")
            self.progress.emit(gen, fitness, hard)

        try:
            result = run_genetic_algorithm(ctx, self.params, on_progress)
            save_chromosome_to_db(conn, ctx, result.best)
            conn.close()
            self.finished.emit(result)
        except InterruptedError:
            conn.close()
            self.finished.emit(None)

    def stop(self):
        self._stopped = True


class GenerationPage(QWidget):
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.worker = None
        self._start_time = 0.0
        self._active_preset = "standard"
        self._setup_ui()
        self._apply_preset("standard")
        self._check_empty()

    def _check_empty(self):
        with make_session(self.engine) as session:
            year = session.execute(
                select(AcademicYear).where(AcademicYear.is_active == 1)
            ).scalar_one_or_none()
            if not year:
                return
            items = session.execute(select(ClassSubject)).scalars().all()

        if not items:
            self.start_btn.setEnabled(False)
            self.start_btn.setToolTip("Сначала создайте учебные планы на вкладке «Данные»")
        else:
            self.start_btn.setEnabled(True)
            self.start_btn.setToolTip("")

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        intro = QLabel(
            "Автоматический поиск расписания. Программа устраняет:\n"
            "учителя в двух классах, занятые кабинеты, окна, нарушения норм."
        )
        intro.setStyleSheet("color: #555; font-size: 13px; padding: 4px 0;")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        preset_group = QGroupBox("Режим поиска")
        preset_group.setStyleSheet(StyleSheet)
        preset_layout = QVBoxLayout()

        preset_row = QHBoxLayout()
        preset_row.setSpacing(10)
        self._preset_btns = {}
        for key, p in PRESETS.items():
            btn = QPushButton(p["label"])
            btn.setProperty("preset_key", key)
            btn.clicked.connect(lambda checked, k=key: self._apply_preset(k))
            btn.setCursor(Qt.PointingHandCursor)
            self._preset_btns[key] = btn
            preset_row.addWidget(btn)
        preset_row.addStretch()
        preset_layout.addLayout(preset_row)

        self.preset_desc = QLabel(PRESETS["standard"]["desc"])
        self.preset_desc.setStyleSheet("color: #7f8c8d; font-size: 12px; padding: 2px 0 4px 4px;")
        self.preset_desc.setWordWrap(True)
        preset_layout.addWidget(self.preset_desc)

        preset_group.setLayout(preset_layout)
        layout.addWidget(preset_group)

        params_group = QGroupBox("Параметры")
        params_group.setStyleSheet(StyleSheet)
        form = QFormLayout()
        form.setSpacing(10)

        self.pop_size_spin = QSpinBox()
        self.pop_size_spin.setRange(10, 500)
        self.pop_size_spin.setValue(80)
        self.pop_size_spin.setFixedWidth(120)
        self.pop_size_spin.setToolTip(
            "Количество вариантов расписания в памяти.\n"
            "Больше = лучше, но медленнее."
        )
        form.addRow("Вариантов в памяти:", self.pop_size_spin)

        self.max_gen_spin = QSpinBox()
        self.max_gen_spin.setRange(10, 5000)
        self.max_gen_spin.setValue(400)
        self.max_gen_spin.setFixedWidth(120)
        self.max_gen_spin.setToolTip(
            "Шагов улучшения расписания.\n"
            "Больше = чище, но с уменьшающейся отдачей."
        )
        form.addRow("Шагов улучшения:", self.max_gen_spin)

        form.addRow("", QLabel(""))

        self.show_advanced = QCheckBox("Расширенные настройки")
        self.show_advanced.setStyleSheet("QCheckBox { font-size: 12px; color: #7f8c8d; }")
        self.show_advanced.toggled.connect(self._toggle_advanced)
        form.addRow("", self.show_advanced)

        self._adv_widget = QWidget()
        adv_layout = QVBoxLayout(self._adv_widget)
        adv_layout.setContentsMargins(8, 8, 8, 8)
        adv_layout.setSpacing(8)

        adv_form = QFormLayout()
        adv_form.setSpacing(6)

        self.mutation_spin = QDoubleSpinBox()
        self.mutation_spin.setRange(0.01, 1.0)
        self.mutation_spin.setSingleStep(0.05)
        self.mutation_spin.setValue(0.1)
        self.mutation_spin.setFixedWidth(100)
        self.mutation_spin.setToolTip("Вероятность случайных изменений (0.01–1.0)")
        adv_form.addRow("Изменений:", self.mutation_spin)

        self.crossover_spin = QDoubleSpinBox()
        self.crossover_spin.setRange(0.1, 1.0)
        self.crossover_spin.setSingleStep(0.05)
        self.crossover_spin.setValue(0.8)
        self.crossover_spin.setFixedWidth(100)
        self.crossover_spin.setToolTip("Вероятность комбинирования двух лучших вариантов")
        adv_form.addRow("Комбинирования:", self.crossover_spin)

        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(0, 99999)
        self.seed_spin.setValue(42)
        self.seed_spin.setFixedWidth(100)
        self.seed_spin.setToolTip("Начальное число генератора случайных чисел.\nРазные числа → разные расписания.")
        adv_form.addRow("Зерно генератора:", self.seed_spin)

        adv_layout.addLayout(adv_form)
        self._adv_widget.setVisible(False)
        form.addRow(self._adv_widget)

        params_group.setLayout(form)
        layout.addWidget(params_group)

        btn_row = QHBoxLayout()
        self.start_btn = QPushButton("▶  Найти расписание")
        self.start_btn.setStyleSheet(BTN_SUCCESS)
        self.start_btn.clicked.connect(self._start_generation)

        self.stop_btn = QPushButton("■  Остановить")
        self.stop_btn.setStyleSheet(BTN_DANGER)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_generation)

        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.stop_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        progress_group = QGroupBox("Ход поиска")
        progress_group.setStyleSheet(StyleSheet)
        pg_layout = QVBoxLayout()

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        pg_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Нажмите «Найти расписание» для начала")
        self.status_label.setStyleSheet("font-size: 14px; color: #7f8c8d; padding: 4px 0;")
        self.status_label.setWordWrap(True)
        pg_layout.addWidget(self.status_label)

        self.conflict_label = QLabel("")
        self.conflict_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; padding: 4px 0;"
        )
        pg_layout.addWidget(self.conflict_label)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(160)
        self.log.setStyleSheet(
            "background-color: #2c3e50; color: #ecf0f1; "
            "border-radius: 4px; font-family: monospace; font-size: 12px; padding: 8px;"
        )
        pg_layout.addWidget(self.log)

        progress_group.setLayout(pg_layout)
        layout.addWidget(progress_group)

        layout.addStretch()

    def _apply_preset(self, key):
        self._active_preset = key
        p = PRESETS[key]
        self.pop_size_spin.setValue(p["pop"])
        self.max_gen_spin.setValue(p["gen"])
        self.preset_desc.setText(p["desc"])

        colors = {
            "fast": ("#e74c3c", "#fdecea", "#c0392b"),
            "standard": ("#3498db", "#eaf2f8", "#2980b9"),
            "quality": ("#27ae60", "#eafaf1", "#219a52"),
        }
        for k, btn in self._preset_btns.items():
            border, bg, hover = colors[k]
            if k == key:
                btn.setStyleSheet(PRESET_SELECTED_TPL.format(
                    border=border, bg=bg, fg="#2c3e50"
                ))
            else:
                btn.setStyleSheet(PRESET_STYLE_TPL.format(
                    border="#d5d8dc", bg="white", fg="#555", hover="#bdc3c7", pressed="#ecf0f1"
                ))

    def _toggle_advanced(self, checked):
        self._adv_widget.setVisible(checked)

    def _start_generation(self):
        year_id = None
        with make_session(self.engine) as session:
            year = session.execute(
                select(AcademicYear).where(AcademicYear.is_active == 1)
            ).scalar_one_or_none()
            if year:
                year_id = year.id

        if year_id is None:
            QMessageBox.warning(self, "Ошибка", "Нет активного учебного года.")
            return

        params = GAParams(
            population_size=self.pop_size_spin.value(),
            max_generations=self.max_gen_spin.value(),
            mutation_rate=self.mutation_spin.value(),
            crossover_rate=self.crossover_spin.value(),
            random_seed=self.seed_spin.value(),
        )

        db_path = find_db_path(self.engine)
        self.worker = GenerationWorker(db_path, year_id, params)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)

        self._start_time = time.time()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.log.clear()
        self.log.append("Поиск расписания запущен...")
        self.status_label.setText("Идёт поиск расписания...")
        self.conflict_label.setText("")
        self.conflict_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; padding: 4px 0;"
        )
        self.worker.start()

    def _stop_generation(self):
        if self.worker:
            self.worker.stop()
            self.log.append("Остановка поиска...")

    def _on_progress(self, gen, fitness, hard):
        max_gen = self.max_gen_spin.value()
        if max_gen > 0:
            pct = int(gen / max_gen * 100)
            self.progress_bar.setValue(pct)
            self.progress_bar.setFormat(f"{pct}%")

        chunk_color = "#27ae60" if hard == 0 else "#3498db"
        self.progress_bar.setStyleSheet(
            "QProgressBar { border: 1px solid #d5d8dc; border-radius: 5px; "
            "background-color: #e8eaed; text-align: center; height: 26px; "
            "font-size: 12px; font-weight: bold; color: #2c3e50; }"
            f"QProgressBar::chunk {{ background-color: {chunk_color}; border-radius: 4px; }}"
        )

        elapsed = time.time() - self._start_time
        elapsed_str = self._format_time(elapsed)
        remaining = ""
        if gen > 0:
            est_total = elapsed / gen * max_gen
            rem = est_total - elapsed
            if rem > 0:
                remaining = f"  |  ~{self._format_time(rem)}"

        self.status_label.setText(
            f"Шаг {gen}/{max_gen}  |  {elapsed_str}{remaining}"
        )

        if hard == 0:
            self.conflict_label.setText("Ошибок нет!")
            self.conflict_label.setStyleSheet(
                "font-size: 16px; font-weight: bold; color: #27ae60; padding: 4px 0;"
            )
        else:
            self.conflict_label.setText(f"Ошибок: {hard}")
            self.conflict_label.setStyleSheet(
                "font-size: 16px; font-weight: bold; color: #e74c3c; padding: 4px 0;"
            )

        if gen % 100 == 0 or (hard == 0 and gen % 10 == 0):
            self.log.append(
                f"  Шаг {gen:4d}  |  ошибок: {hard:3d}  |  качество: {fitness:.0f}"
            )

    def _on_finished(self, result):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        elapsed = time.time() - self._start_time

        if result is None:
            self.log.append("Поиск остановлен пользователем.")
            self.status_label.setText("Остановлено вручную")
            self.conflict_label.setText("")
        elif result.best_fitness.hard_conflicts == 0:
            self.log.append("Расписание без ошибок найдено!")
            self.status_label.setText(f"Готово за {self._format_time(elapsed)}")
            self.progress_bar.setValue(100)
            self.progress_bar.setFormat("100%")
            penalty = result.best_fitness.soft_penalty
            self.conflict_label.setText(f"Готово! Мелких замечаний: {penalty:.0f}")
            self.conflict_label.setStyleSheet(
                "font-size: 16px; font-weight: bold; color: #27ae60; padding: 4px 0;"
            )
            QMessageBox.information(
                self, "Готово",
                f"Расписание успешно сгенерировано и сохранено!\n\n"
                f"Серьёзных ошибок: 0\n"
                f"Мелких замечаний (окна, чередование): {penalty:.0f}\n"
                f"Время поиска: {self._format_time(elapsed)}"
            )
        else:
            hard = result.best_fitness.hard_conflicts
            self.log.append(f"Поиск завершён, остались ошибки: {hard}")
            self.status_label.setText(f"Завершено за {self._format_time(elapsed)}")
            self.conflict_label.setText(f"Осталось ошибок: {hard}")
            self.conflict_label.setStyleSheet(
                "font-size: 16px; font-weight: bold; color: #e67e22; padding: 4px 0;"
            )
            QMessageBox.warning(
                self, "Внимание",
                f"Расписание найдено, но не удалось устранить все ошибки ({hard}).\n"
                f"Попробуйте режим «Качественно» или увеличьте шаги поиска."
            )

    def _format_time(self, seconds):
        if seconds < 0:
            seconds = 0
        if seconds < 60:
            return f"{seconds:.0f} сек"
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins} мин {secs} сек"
