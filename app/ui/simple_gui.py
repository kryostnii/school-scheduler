import sys
from pathlib import Path

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QSpinBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox, QTextEdit, QTabWidget, QFileDialog
)
from PySide6.QtCore import Qt
import random

class SimpleMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Школьное расписание - Прототип")
        self.setGeometry(100, 100, 1000, 700)
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Основной layout
        main_layout = QVBoxLayout(central_widget)
        
        # Заголовок
        title_label = QLabel("Школьное расписание - Прототип")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        main_layout.addWidget(title_label)
        
        # Панель управления
        control_group = QGroupBox("Управление")
        control_layout = QHBoxLayout(control_group)
        
        self.run_button = QPushButton("🚀 Запустить")
        self.run_button.clicked.connect(self.run_simulation)
        control_layout.addWidget(self.run_button)
        
        self.reset_button = QPushButton("🔄 Сброс")
        self.reset_button.clicked.connect(self.reset_simulation)
        control_layout.addWidget(self.reset_button)
        
        self.export_button = QPushButton("📤 Экспорт")
        self.export_button.clicked.connect(self.export_csv)
        control_layout.addWidget(self.export_button)
        
        main_layout.addWidget(control_group)
        
        # Таблица результатов
        self.results_table = QTableWidget(10, 7)
        self.results_table.setHorizontalHeaderLabels(["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Урок"])
        self.results_table.setVerticalHeaderLabels([f"Урок {i}" for i in range(1, 11)])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        main_layout.addWidget(self.results_table)
        
        # Статус
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Готов к запуску")
        
    def run_simulation(self):
        """Симуляция запуска"""
        self.status_bar.showMessage("Выполняется симуляция...")
        
        # Создаем случайную таблицу
        for i in range(10):
            for j in range(6):
                item = QTableWidgetItem(f"пр.{random.randint(1, 99)}")
                self.results_table.setItem(i, j, item)
                
        self.status_bar.showMessage("Симуляция завершена")
        
    def reset_simulation(self):
        """Сброс"""
        self.results_table.clearContents()
        self.status_bar.showMessage("Данные сброшены")
        
    def export_csv(self):
        """Экспорт в CSV"""
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self, "Сохранить как CSV", "", "CSV Files (*.csv);;All Files (*)"
            )
            if filename:
                with open(filename, 'w') as f:
                    f.write("Пн,Вт,Ср,Чт,Пт,Сб\n")
                    for i in range(10):
                        row = []
                        for j in range(6):
                            item = self.results_table.item(i, j)
                            if item:
                                row.append(item.text())
                            else:
                                row.append("")
                        f.write(",".join(row) + "\n")
                self.status_bar.showMessage(f"Экспортировано в {filename}")
        except Exception as e:
            self.status_bar.showMessage("Ошибка экспорта")

def main():
    app = QApplication(sys.argv)
    window = SimpleMainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()