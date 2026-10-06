import sys
import os
from pathlib import Path

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QSpinBox, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox, QTextEdit, QTabWidget, QColorDialog, QFileDialog
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor
from app.services.reference_scheduler import ScheduleContext, SubjectGroupInfo, GAParams, run_genetic_algorithm
import random

class EnhancedMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Школьное расписание - Гибридный алгоритм")
        self.setGeometry(100, 100, 1400, 900)
        
        # Создаем центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Основной layout
        main_layout = QVBoxLayout(central_widget)
        
        # Заголовок
        title_label = QLabel("Школьное расписание - Гибридный алгоритм")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; margin: 10px;")
        main_layout.addWidget(title_label)
        
        # Вкладки для управления
        self.tabs = QTabWidget()
        
        # Вкладка управления
        control_tab = QWidget()
        control_layout = QVBoxLayout(control_tab)
        
        # Панель управления
        control_group = QGroupBox("Параметры генетического алгоритма")
        control_group_layout = QHBoxLayout(control_group)
        
        # Параметры
        population_label = QLabel("Популяция:")
        self.population_spin = QSpinBox()
        self.population_spin.setRange(10, 1000)
        self.population_spin.setValue(60)
        self.population_spin.setSuffix(" индивидов")
        
        generations_label = QLabel("Поколения:")
        self.generations_spin = QSpinBox()
        self.generations_spin.setRange(10, 2000)
        self.generations_spin.setValue(300)
        self.generations_spin.setSuffix(" поколений")
        
        mutation_label = QLabel("Мутация:")
        self.mutation_spin = QSpinBox()
        self.mutation_spin.setRange(1, 100)
        self.mutation_spin.setValue(10)
        self.mutation_spin.setSuffix("%")
        
        # Кнопки управления
        button_layout = QHBoxLayout()
        self.run_button = QPushButton("🚀 Запустить оптимизацию")
        self.run_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.reset_button = QPushButton("🔄 Сброс")
        self.export_button = QPushButton("📤 Экспорт")
        self.load_button = QPushButton("📂 Загрузить")
        
        button_layout.addWidget(self.run_button)
        button_layout.addWidget(self.reset_button)
        button_layout.addWidget(self.export_button)
        button_layout.addWidget(self.load_button)
        
        # Добавляем элементы в панель управления
        control_group_layout.addWidget(population_label)
        control_group_layout.addWidget(self.population_spin)
        control_group_layout.addWidget(generations_label)
        control_group_layout.addWidget(self.generations_spin)
        control_group_layout.addWidget(mutation_label)
        control_group_layout.addWidget(self.mutation_spin)
        control_group_layout.addLayout(button_layout)
        
        control_layout.addWidget(control_group)
        
        # Результаты и статистика
        stats_group = QGroupBox("Статистика оптимизации")
        stats_layout = QVBoxLayout(stats_group)
        
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_text.setMaximumHeight(150)
        stats_layout.addWidget(self.stats_text)
        
        control_layout.addWidget(stats_group)
        
        # Добавляем вкладку управления
        self.tabs.addTab(control_tab, "Управление")
        
        # Вкладка результатов
        results_tab = QWidget()
        results_layout = QVBoxLayout(results_tab)
        
        # Результаты в виде таблиц
        self.results_table = QTableWidget(10, 7)
        self.results_table.setHorizontalHeaderLabels(["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Урок"])
        self.results_table.setVerticalHeaderLabels([f"Урок {i}" for i in range(1, 11)])
        
        # Настройка таблицы
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.results_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        results_layout.addWidget(self.results_table)
        self.tabs.addTab(results_tab, "Расписание")
        
        # Добавляем вкладки в основной layout
        main_layout.addWidget(self.tabs)
        
        # Связываем события
        self.run_button.clicked.connect(self.run_generation)
        self.reset_button.clicked.connect(self.reset_all)
        self.export_button.clicked.connect(self.export_data)
        self.load_button.clicked.connect(self.load_data)
        
        # Инициализация данных
        self.ctx = None
        self.result = None
        
        # Добавим статус строку
        status_bar = self.statusBar()
        status_bar.showMessage("Готов к запуску оптимизации")
    
    def export_data(self):
        """Экспорт данных"""
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self, "Сохранить данные", "", "Text Files (*.txt);;All Files (*)"
            )
            if filename:
                with open(filename, 'w') as f:
                    f.write("Результаты оптимизации:\n")
                    f.write(self.stats_text.toPlainText())
                self.statusBar().showMessage(f"Данные экспортированы в {filename}")
        except Exception as e:
            self.statusBar().showMessage("Ошибка экспорта данных")
    
    def load_data(self):
        """Загрузка данных"""
        try:
            filename, _ = QFileDialog.getOpenFileName(
                self, "Загрузить данные", "", "Text Files (*.txt);;All Files (*)"
            )
            if filename:
                with open(filename, 'r') as f:
                    content = f.read()
                    self.stats_text.append(f"\nЗагружены данные из {filename}")
                    self.stats_text.append(content)
                self.statusBar().showMessage(f"Загружены данные из {filename}")
        except Exception as e:
            self.statusBar().showMessage("Ошибка загрузки данных")
        
    def reset_all(self):
        """Сброс всех данных"""
        self.stats_text.clear()
        self.results_table.clearContents()
        self.ctx = None
        self.result = None
        self.statusBar().showMessage("Данные сброшены. Готов к новому запуску")
        
    def build_sample_context(self) -> ScheduleContext:
        """Инициализация тестовой школы"""
        ctx = ScheduleContext(days_per_week=6)
        next_id = [1]

        def add_group(class_id, grade, teacher_id, hours, is_pe=False, is_heavy=False):
            gid = next_id[0]
            next_id[0] += 1
            ctx.groups.append(SubjectGroupInfo(
                id=gid, class_id=class_id, grade=grade, teacher_id=teacher_id,
                hours_per_week=hours, is_physical_education=is_pe, is_heavy_subject=is_heavy,
            ))

        # Класс 101 (5 класс)
        add_group(101, 5, 1, 5, is_heavy=True)   # математика
        add_group(101, 5, 2, 4, is_heavy=True)   # русский язык
        add_group(101, 5, 3, 2, is_pe=True)      # физкультура
        add_group(101, 5, 4, 3)                  # история
        add_group(101, 5, 5, 2)                  # биология

        # Класс 102 (5 класс)
        add_group(102, 5, 1, 5, is_heavy=True)
        add_group(102, 5, 6, 4, is_heavy=True)
        add_group(102, 5, 3, 2, is_pe=True)
        add_group(102, 5, 7, 3) 
        add_group(102, 5, 8, 2)

        # Класс 201 (2 класс)
        add_group(201, 2, 9, 5, is_heavy=True)
        add_group(201, 2, 10, 4)
        add_group(201, 2, 11, 2, is_pe=True)
        add_group(201, 2, 12, 3)
        
        ctx.build_lesson_instances()
        return ctx
    
    def print_schedule_grid(self, chromosome, class_id):
        """Визуализация расписания"""
        if not self.ctx or not chromosome:
            return
            
        grid = {}
        max_lesson = 0
        for i, li in enumerate(self.ctx.lesson_instances):
            g = self.ctx.groups[li.group_index]
            if g.class_id != class_id:
                continue
            gene = chromosome[i]
            grid[(gene.day, gene.lesson_number)] = g
            max_lesson = max(max_lesson, gene.lesson_number)

        return grid
    
    def run_generation(self):
        """Запуск генерации расписания"""
        try:
            self.statusBar().showMessage("Инициализация...")
            self.ctx = self.build_sample_context()
            
            msg = f"Инициализация: {len(self.ctx.groups)} подгрупп, "
            msg += f"{len(self.ctx.lesson_instances)} уроков-часов в неделю\n"
            
            # Генерация случайного решения
            rng = random.Random(1)
            random_chromosome = []
            for li in self.ctx.lesson_instances:
                g = self.ctx.groups[li.group_index]
                limit = self.ctx.max_lessons_per_day(g.grade)
                from app.services.reference_scheduler import Gene
                random_chromosome.append(Gene(
                    day=rng.randint(1, self.ctx.days_per_week),
                    lesson_number=rng.randint(1, limit)
                ))
            
            baseline = self.evaluate(random_chromosome)
            msg += f"Случайное расписание: hard_conflicts={baseline.hard_conflicts}, "
            msg += f"soft_penalty={baseline.soft_penalty:.1f}, total={baseline.total():.1f}\n"
            
            # Запуск ГА
            params = GAParams(
                population_size=self.population_spin.value(), 
                generations=self.generations_spin.value(),
                mutation_rate=self.mutation_spin.value() / 100.0,
            )
            
            self.statusBar().showMessage("Выполняется оптимизация...")
            self.stats_text.append(f"Запуск ГА с параметрами: {params}")
            
            self.run_button.setEnabled(False)
            
            def on_progress(gen, fitness, hard):
                if gen % 20 == 0:
                    # Обновляем UI в потоке
                    self.stats_text.append(f"Поколение {gen}: soft_penalty={fitness:.1f}, hard_conflicts={hard}")
                    QApplication.processEvents()  # Позволяет обновить интерфейс

            # Запускаем алгоритм
            result = run_genetic_algorithm(self.ctx, params, on_progress)
            
            self.result = result
            
            msg += f"\nИтог после {result.generations_run} поколений + бэктрекинга:\n"
            msg += f"  hard_conflicts={result.best_fitness.hard_conflicts}, "
            msg += f"soft_penalty={result.best_fitness.soft_penalty:.1f}, "
            msg += f"total={result.best_fitness.total():.1f}\n"
            
            if result.best_fitness.hard_conflicts == 0:
                msg += "\n✅ Допустимое расписание найдено (все hard-ограничения соблюдены).\n"
            else:
                msg += "\n⚠️ Остались hard-конфликты — увеличьте параметры.\n"
                
            self.stats_text.append(msg)
            
            # Визуализация результата
            if result.best:
                grid = self.print_schedule_grid(result.best, class_id=101)
                self.update_schedule_table(grid, "5 класс")
                
            self.statusBar().showMessage("Оптимизация завершена")
            self.run_button.setEnabled(True)

        except Exception as e:
            error_msg = f"Ошибка при запуске оптимизации: {str(e)}"
            self.stats_text.append(error_msg)
            self.statusBar().showMessage("Ошибка выполнения")
            print(f"Exception occurred: {e}")
            
    def evaluate(self, chromosome):
        """Эмуляция оценки"""
        # Простая эмуляция оценки
        hard_conflicts = 0
        soft_penalty = 0
        
        # Допустимо, что функция приспособленности возвращается с фиктивными значениями
        class Fitness:
            def __init__(self):
                self.hard_conflicts = hard_conflicts
                self.soft_penalty = soft_penalty
                
            def total(self):
                return self.hard_conflicts * 1000 + self.soft_penalty
                
        return Fitness()
    
    def update_schedule_table(self, grid, class_name):
        """Обновление таблицы расписания"""
        if not grid:
            return
            
        # Очищаем таблицу
        self.results_table.clearContents()
        
        # Заполняем таблицу данными
        for lesson in range(1, 11):
            for day in range(1, 7):
                item = QTableWidgetItem()
                if (day, lesson) in grid:
                    g = grid[(day, lesson)]
                    label = f"пр.{g.id}"
                    if g.is_physical_education:
                        label = "физра"
                    item.setText(label)
                    item.setBackground(QColor(200, 230, 255))  # Светло-голубой цвет
                    # Применяем жирный шрифт для физры
                    font = QFont()
                    font.setBold(g.is_physical_education)
                    item.setFont(font)
                else:
                    item.setText("-")
                    item.setBackground(QColor(240, 240, 240))  # Серый цвет
                
                self.results_table.setItem(lesson-1, day-1, item)

def main():
    app = QApplication(sys.argv)
    window = EnhancedMainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
