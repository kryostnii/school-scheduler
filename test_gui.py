#!/usr/bin/env python3
"""Тестовый запуск для проверки GUI"""

import sys
import os
sys.path.insert(0, '/home/kryostnii/Storage/projects')

try:
    from app.ui.main_window_enhanced import main
    
    print("Запуск GUI...")
    main()
    
except Exception as e:
    print(f"Ошибка при запуске GUI: {e}")
    import traceback
    traceback.print_exc()