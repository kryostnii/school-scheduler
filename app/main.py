"""Точка входа приложения School Scheduler."""
import sys
import os
from pathlib import Path

# Добавляем путь к модулям 
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Проверяем, запущен ли файл напрямую или через импорт
if __name__ == "__main__":
    from app.ui.main_window_fixed import main as gui_main
    
    def main():
        # Просто запускаем GUI
        return gui_main()
    
    main()
else:
    # В режиме импорта используем упрощенную версию 
    from app.ui.main_window_fixed import SchoolSchedulerMainWindow
    
    def main():
        """Простая функция для запуска"""
        return SchoolSchedulerMainWindow()
    
    __all__ = ["main"]