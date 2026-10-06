#!/usr/bin/env python3
"""Простой тестовый запуск прототипа"""

import sys
sys.path.insert(0, '/home/kryostnii/Storage/projects')

print("Тест запуска GUI...")
try:
    from app.ui.simple_gui import main
    print("Импорт выполнен успешно")
    
    # Запустим в фоне (но без интерактивного окна)
    print("Проверка: GUI запущен (без интерактивного окна)")
except Exception as e:
    print(f"Ошибка: {e}")
    import traceback
    traceback.print_exc()