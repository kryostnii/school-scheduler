import sys
import os
from pathlib import Path

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QSpinBox, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox, QGridLayout, QTextEdit
)
from PySide6.QtCore import Qt
from app.services.reference_scheduler import ScheduleContext, SubjectGroupInfo, GAParams, run_genetic_algorithm
import random

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Школьное расписание - Гибридный алгоритм")
        self.setGeometry(100, 100, 1200, 800)
        
        # Создаем центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Основной layout
        main_layout = QVBoxLayout(central_widget)
        
        # Заголовок
        title_label = QLabel("Школьное расписание - Гибридный алгоритм")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        main_layout.addWidget(title_label)
        
        # Панель управления
        control_group = QGroupBox("Управление")
        control_layout = QHBoxLayout(control_group)
        
        self.run_button = QPushButton("Запустить генерацию")
        self.run_button.clicked.connect(self.run_generation)
        control_layout.addWidget(self.run_button)
        
        self.reset_button = QPushButton("Сброс")
        self.reset_button.clicked.connect(self.reset_all)
        control_layout.addWidget(self.reset_button)
        
        self.population_spin = QSpinBox()
        self.population_spin.setRange(10, 500)
        self.population_spin.setValue(60)
        control_layout.addWidget(QLabel("Популяция:"))
        control_layout.addWidget(self.population_spin)
        
        self.generations_spin = QSpinBox()
        self.generations_spin.setRange(10, 1000)
        self.generations_spin.setValue(300)
        control_layout.addWidget(QLabel("Поколения:"))
        control_layout.addWidget(self.generations_spin)
        
        main_layout.addWidget(control_group)
        
        # Результаты
        results_group = QGroupBox("Результаты")
        results_layout = QVBoxLayout(results_group)
        
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        results_layout.addWidget(self.results_text)
        
        main_layout.addWidget(results_group)
        
        # Таблица расписания
        schedule_group = QGroupBox("Пример расписания")
        schedule_layout = QVBoxLayout(schedule_group)
        
        self.schedule_table = QTableWidget(10, 7)
        self.schedule_table.setHorizontalHeaderLabels(["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Урок"])
        self.schedule_table.setVerticalHeaderLabels([f"Урок {i}" for i in range(1, 11)])
        self.schedule_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        schedule_layout.addWidget(self.schedule_table)
        
        main_layout.addWidget(schedule_group)
        
        # Инициализация данных
        self.ctx = None
        self.result = None
        
    def reset_all(self):
        """Сброс всех данных"""
        self.results_text.clear()
        self.schedule_table.clear()
        self.schedule_table.setHorizontalHeaderLabels(["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Урок"])
        self.ctx = None
        self.result = None
        
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

        # Класс 102 (5 класс) — частично те же учителя
        add_group(102, 5, 1, 5, is_heavy=True)
        add_group(102, 5, 6, 4, is_heavy=True)
        add_group(102, 5, 3, 2, is_pe=True)
        add_group(102, 5, 7, 3)
        add_group(102, 5, 8, 2)

        # Класс 201 (2 класс) — проверка лимита уроков/день
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
            self.ctx = self.build_sample_context()
            
            msg = f"Инициализация: {len(self.ctx.groups)} подгрупп, "
            msg += f"{len(self.ctx.lesson_instances)} уроков-часов в неделю\n"
            
            rng = random.Random(1)
            random_chromosome = []
            for li in self.ctx.lesson_instances:
                g = self.ctx.groups[li.group_index]
                limit = self.ctx.max_lessons_for_grade(g.grade)
                from app.services.reference_scheduler import Gene
                random_chromosome.append(Gene(rng.randint(1, self.ctx.days_per_week), rng.randint(1, limit)))
            baseline = self.evaluate(random_chromosome)
            msg += f"Случайное расписание:  hard_conflicts={baseline.hard_conflicts}  "
            msg += f"soft_penalty={baseline.soft_penalty:.1f}  total={baseline.total():.1f}\n"
            
            params = GAParams(population_size=self.population_spin.value(), 
                            max_generations=self.generations_spin.value(), 
                            mutation_rate=0.1)
            
            self.results_text.append(f"Запуск генетического алгоритма...")
            
            def on_progress(gen, fitness, hard):
                if gen % 50 == 0:
                    self.results_text.append(f"  поколение {gen:4d}  hard_conflicts={hard:3d}  fitness={fitness:.1f}")
            
            result = run_genetic_algorithm(self.ctx, params, on_progress)
            
            self.result = result
            
            msg += f"\nИтог после {result.generations_run} поколений + бэктрекинга:\n"
            msg += f"  hard_conflicts={result.best_fitness.hard_conflicts}  "
            msg += f"soft_penalty={result.best_fitness.soft_penalty:.1f}  "
            msg += f"total={result.best_fitness.total():.1f}\n"
            
            if result.best_fitness.hard_conflicts == 0:
                msg += "\n✓ Допустимое расписание найдено (все hard-ограничения соблюдены).\n"
            else:
                msg += "\n✗ Остались hard-конфликты — увеличьте max_generations/population_size.\n"
            
            self.results_text.append(msg)
            
            # Отображение расписания
            if result.best:
                grid = self.print_schedule_grid(result.best, class_id=101)
                self.update_schedule_table(grid, "5А")
                
        except Exception as e:
            self.results_text.append(f"Ошибка: {str(e)}")
    
    def evaluate(self, chromosome):
        """Эмуляция оценки"""
        # Простая эмуляция для отображения
        from app.services.reference_scheduler import evaluate
        return evaluate(chromosome, self.ctx)
    
    def update_schedule_table(self, grid, class_name):
        """Обновление таблицы расписания"""
        if not grid:
            return
            
        # Очистка таблицы
        self.schedule_table.clear()
        self.schedule_table.setRowCount(10)  # 10 уроков
        self.schedule_table.setColumnCount(7)  # 6 дней + урок
        
        # Заголовки
        self.schedule_table.setHorizontalHeaderLabels(["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Урок"])
        self.schedule_table.setVerticalHeaderLabels([f"Урок {i}" for i in range(1, 11)])
        
        day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб"]
        
        # Заполнение таблицы
        for lesson in range(1, 11):
            for day in range(1, 7):
                item = QTableWidgetItem()
                if (day, lesson) in grid:
                    g = grid[(day, lesson)]
                    label = f"пр.{g.id}"
                    if g.is_physical_education:
                        label = "физра"
                    item.setText(label)
                else:
                    item.setText("")
                item.setTextAlignment(Qt.AlignCenter)
                self.schedule_table.setItem(lesson-1, day-1, item)
                
        # Адаптация размеров
        self.schedule_table.resizeColumnsToContents()

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()