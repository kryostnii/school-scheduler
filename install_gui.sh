#!/bin/bash

# Установка необходимых зависимостей для запуска GUI
echo "Установка зависимостей..."

# Проверяем, установлен ли Python и pip
if ! command -v python3 &> /dev/null; then
    echo "Python3 не найден. Установите Python3."
    exit 1
fi

if ! command -v pip3 &> /dev/null; then
    echo "pip3 не найден. Установите pip3."
    exit 1
fi

# Устанавливаем необходимые пакеты
echo "Установка PySide6..."
pip3 install PySide6

echo "Готово! Теперь можно запустить приложение командой:"
echo "python3 app/main.py"