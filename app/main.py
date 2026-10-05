"""Точка входа приложения School Scheduler."""
import os
import sys
import shutil
import sqlite3
import pathlib
import platform

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

# Для упрощения использования UI-интерфейса без сложной архитектуры
# Будем использовать упрощенную версию, которая инициализирует GUI напрямую

from PySide6.QtWidgets import QApplication
from app.ui.main_window import main as gui_main

def main():
    # Просто запускаем GUI
    return gui_main()

if __name__ == "__main__":
    main()
