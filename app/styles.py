"""Централизованные QSS-стили приложения School Scheduler."""
from __future__ import annotations

# ── Цвета ──────────────────────────────────────────────────────────────
PRIMARY = "#3498db"
PRIMARY_DARK = "#2980b9"
PRIMARY_LIGHT = "#5dade2"
SUCCESS = "#27ae60"
SUCCESS_DARK = "#1e8449"
WARNING = "#e67e22"
DANGER = "#e74c3c"
DANGER_DARK = "#c0392b"

BG_DARK = "#2c3e50"
BG_DARKER = "#1a252f"
BG_LIGHT = "#ecf0f1"
BG_WHITE = "#ffffff"
BG_PAGE = "#f5f6fa"

TEXT_DARK = "#2c3e50"
TEXT_MUTED = "#7f8c8d"
TEXT_LIGHT = "#bdc3c7"
TEXT_WHITE = "#ffffff"

BORDER = "#d5d8dc"
BORDER_LIGHT = "#e8e8e8"


# ── Таблицы ────────────────────────────────────────────────────────────
TABLE_STYLE = f"""
    QTableWidget {{
        background-color: {BG_WHITE};
        gridline-color: {BORDER_LIGHT};
        border: 1px solid {BORDER};
        border-radius: 6px;
        font-size: 12px;
        selection-background-color: {PRIMARY};
        outline: none;
    }}
    QTableWidget::item {{
        padding: 6px 10px;
        border-bottom: 1px solid {BORDER_LIGHT};
    }}
    QTableWidget::item:selected {{
        color: {TEXT_WHITE};
        background-color: {PRIMARY};
    }}
    QTableWidget::item:alternate {{
        background-color: #f8f9fa;
    }}
    QTableWidget::item:hover {{
        background-color: #eaf2f8;
    }}
    QHeaderView::section {{
        background-color: {BG_DARK};
        color: {TEXT_WHITE};
        border: none;
        padding: 8px 10px;
        font-weight: bold;
        font-size: 12px;
        border-right: 1px solid {BG_DARKER};
    }}
    QHeaderView::section:last {{
        border-right: none;
    }}
"""

# ── Кнопки ─────────────────────────────────────────────────────────────
BTN_PRIMARY = f"""
    QPushButton {{
        padding: 8px 16px;
        border-radius: 6px;
        border: none;
        background-color: {PRIMARY};
        color: {TEXT_WHITE};
        font-size: 12px;
        font-weight: bold;
    }}
    QPushButton:hover {{
        background-color: {PRIMARY_DARK};
    }}
    QPushButton:pressed {{
        background-color: #2471a3;
    }}
    QPushButton:disabled {{
        background-color: {BORDER};
        color: {TEXT_MUTED};
    }}
"""

BTN_DEFAULT = f"""
    QPushButton {{
        padding: 8px 16px;
        border-radius: 6px;
        border: 1px solid {BORDER};
        background-color: {BG_WHITE};
        color: {TEXT_DARK};
        font-size: 12px;
    }}
    QPushButton:hover {{
        background-color: {PRIMARY};
        color: {TEXT_WHITE};
        border-color: {PRIMARY};
    }}
    QPushButton:pressed {{
        background-color: {PRIMARY_DARK};
        color: {TEXT_WHITE};
    }}
"""

BTN_DANGER = f"""
    QPushButton {{
        padding: 8px 16px;
        border-radius: 6px;
        border: 1px solid {DANGER};
        background-color: {BG_WHITE};
        color: {DANGER};
        font-size: 12px;
    }}
    QPushButton:hover {{
        background-color: {DANGER};
        color: {TEXT_WHITE};
    }}
    QPushButton:pressed {{
        background-color: {DANGER_DARK};
        color: {TEXT_WHITE};
    }}
"""

BTN_SUCCESS = f"""
    QPushButton {{
        padding: 8px 16px;
        border-radius: 6px;
        border: none;
        background-color: {SUCCESS};
        color: {TEXT_WHITE};
        font-size: 12px;
        font-weight: bold;
    }}
    QPushButton:hover {{
        background-color: {SUCCESS_DARK};
    }}
"""

BTN_ICON = f"""
    QPushButton {{
        border: 1px solid {BORDER};
        border-radius: 6px;
        background-color: {BG_WHITE};
        font-size: 16px;
        min-width: 36px;
        min-height: 36px;
        max-width: 36px;
        max-height: 36px;
    }}
    QPushButton:hover {{
        background-color: #eaf2f8;
        border-color: {PRIMARY};
    }}
"""

# ── Sidebar ────────────────────────────────────────────────────────────
SIDEBAR_STYLE = f"""
    QFrame {{
        background-color: {BG_DARK};
        border-right: 1px solid {BG_DARKER};
    }}
    QPushButton {{
        color: {TEXT_LIGHT};
        border: none;
        text-align: left;
        padding: 12px 20px;
        font-size: 13px;
        border-radius: 0px;
    }}
    QPushButton:hover {{
        background-color: #34495e;
        color: {TEXT_WHITE};
    }}
    QPushButton[active="true"] {{
        background-color: {PRIMARY};
        color: {TEXT_WHITE};
        font-weight: bold;
    }}
"""

# ── Диалоги ────────────────────────────────────────────────────────────
DIALOG_STYLE = f"""
    QDialog {{
        background-color: {BG_PAGE};
    }}
    QLabel {{
        color: {TEXT_DARK};
        font-size: 12px;
    }}
    QLineEdit, QComboBox, QSpinBox {{
        padding: 6px 10px;
        border: 1px solid {BORDER};
        border-radius: 4px;
        background-color: {BG_WHITE};
        font-size: 12px;
        min-height: 20px;
    }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
        border-color: {PRIMARY};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QCheckBox {{
        spacing: 8px;
        font-size: 12px;
    }}
"""

FORM_LABEL_STYLE = f"font-size: 12px; font-weight: bold; color: {TEXT_DARK};"
FORM_HINT_STYLE = f"font-size: 11px; color: {TEXT_MUTED};"
ERROR_STYLE = f"border: 2px solid {DANGER};"
SECTION_HEADER_STYLE = f"font-size: 14px; font-weight: bold; color: {TEXT_DARK}; padding-bottom: 4px;"

# ── Прочее ─────────────────────────────────────────────────────────────
GROUPBOX_STYLE = f"""
    QGroupBox {{
        font-weight: bold;
        font-size: 13px;
        color: {TEXT_DARK};
        border: 1px solid {BORDER};
        border-radius: 6px;
        margin-top: 8px;
        padding-top: 16px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
    }}
"""

SCROLLBAR_STYLE = f"""
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {BORDER};
        border-radius: 4px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {TEXT_MUTED};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 8px;
        margin: 0;
    }}
    QScrollBar::handle:horizontal {{
        background: {BORDER};
        border-radius: 4px;
        min-width: 30px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {TEXT_MUTED};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
    }}
"""

STATUSBAR_STYLE = f"""
    QStatusBar {{
        background: {BG_WHITE};
        color: {TEXT_MUTED};
        font-size: 11px;
        border-top: 1px solid {BORDER};
    }}
"""

# ── Глобальный стиль приложения ───────────────────────────────────────
SGLOBAL_STYLE = f"""
    QMainWindow, QWidget {{
        color: {TEXT_DARK};
    }}
    QToolTip {{
        background-color: {BG_DARKER};
        color: {TEXT_WHITE};
        border: 1px solid {PRIMARY};
        padding: 6px 8px;
        font-size: 11px;
        border-radius: 4px;
    }}
    QStackedWidget {{
        background-color: {BG_PAGE};
    }}
    QScrollArea {{
        border: none;
        background: transparent;
    }}
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
        padding: 6px 10px;
        border: 1px solid {BORDER};
        border-radius: 5px;
        background-color: {BG_WHITE};
        color: {TEXT_DARK};
        font-size: 12px;
        min-height: 20px;
        selection-background-color: {PRIMARY};
    }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
        border-color: {PRIMARY};
    }}
    QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{
        background-color: #ecf0f1;
        color: {TEXT_MUTED};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 26px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {BG_WHITE};
        color: {TEXT_DARK};
        selection-background-color: {PRIMARY};
        selection-color: {TEXT_WHITE};
        border: 1px solid {BORDER};
    }}
    QCheckBox {{
        spacing: 8px;
        color: {TEXT_DARK};
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border: 1px solid {BORDER};
        border-radius: 3px;
        background-color: {BG_WHITE};
    }}
    QCheckBox::indicator:checked {{
        background-color: {PRIMARY};
        border-color: {PRIMARY};
    }}
    QProgressBar {{
        border: 1px solid {BORDER};
        border-radius: 5px;
        background-color: #e8eaed;
        text-align: center;
        height: 24px;
        font-size: 12px;
        font-weight: bold;
        color: {TEXT_DARK};
    }}
    QProgressBar::chunk {{
        background-color: {PRIMARY};
        border-radius: 4px;
    }}
    QPushButton {{
        padding: 8px 14px;
        border-radius: 5px;
        font-size: 12px;
    }}
    QMessageBox {{
        background-color: {BG_PAGE};
    }}
    QDialog {{
        background-color: {BG_PAGE};
    }}
    QMessageBox QPushButton {{
        padding: 6px 16px;
        border-radius: 5px;
        font-size: 12px;
        background-color: {BG_WHITE};
        border: 1px solid {BORDER};
        color: {TEXT_DARK};
    }}
    QMessageBox QPushButton:hover {{
        background-color: {PRIMARY};
        color: {TEXT_WHITE};
        border-color: {PRIMARY};
    }}
    QMessageBox QPushButton[text^="&Yes"], QMessageBox QPushButton[text^="&OK"] {{
        background-color: {PRIMARY};
        color: {TEXT_WHITE};
        border: none;
    }}
    QMenu {{
        background-color: {BG_WHITE};
        color: {TEXT_DARK};
        border: 1px solid {BORDER};
        border-radius: 4px;
        padding: 4px;
        font-size: 12px;
    }}
    QMenu::item {{
        padding: 6px 18px;
        border-radius: 3px;
    }}
    QMenu::item:selected {{
        background-color: {PRIMARY};
        color: {TEXT_WHITE};
    }}
    QTabWidget::pane {{
        border: 1px solid {BORDER};
        border-radius: 6px;
        background: transparent;
        top: -1px;
    }}
    QTabBar::tab {{
        padding: 8px 18px;
        font-size: 12px;
        background-color: {BG_WHITE};
        border: 1px solid {BORDER};
        border-bottom: none;
        border-top-left-radius: 5px;
        border-top-right-radius: 5px;
        margin-right: 2px;
        color: {TEXT_MUTED};
    }}
    QTabBar::tab:selected {{
        background-color: {PRIMARY};
        color: {TEXT_WHITE};
        font-weight: bold;
    }}
    QTabBar::tab:hover:!selected {{
        background-color: #eaf2f8;
    }}
    QGroupBox {{
        font-weight: bold;
        font-size: 13px;
        color: {TEXT_DARK};
        border: 1px solid {BORDER};
        border-radius: 6px;
        margin-top: 10px;
        background-color: {BG_WHITE};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
    }}
    QStatusBar {{
        background: {BG_WHITE};
        color: {TEXT_MUTED};
        font-size: 11px;
        border-top: 1px solid {BORDER};
    }}
    {SCROLLBAR_STYLE}
"""
