"""Страница настроек: санитарные правила (sanpin_rules) и экспорт БД."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGroupBox, QCheckBox,
    QPushButton, QHBoxLayout, QMessageBox,
)
from PySide6.QtCore import Qt

from sqlalchemy import select, update

from app.data.models import SanpinRule, make_session
from app.styles import GROUPBOX_STYLE, BTN_SUCCESS


class SettingsPage(QWidget):
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self._checkboxes = {}
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QLabel("\U0001f527  Настройки")
        header.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #2c3e50; padding-bottom: 2px;"
        )
        layout.addWidget(header)

        sub = QLabel("Санитарные правила, учитываемые при генерации расписания")
        sub.setStyleSheet("font-size: 12px; color: #7f8c8d; padding-bottom: 8px;")
        layout.addWidget(sub)

        sanpin_group = QGroupBox("Санитарные нормы (вкл/выкл)")
        sanpin_group.setStyleSheet(GROUPBOX_STYLE)
        self.sanpin_layout = QVBoxLayout()
        sanpin_group.setLayout(self.sanpin_layout)
        layout.addWidget(sanpin_group)

        btn_row = QHBoxLayout()
        save_btn = QPushButton("\U0001f4be  Сохранить")
        save_btn.setStyleSheet(BTN_SUCCESS)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        layout.addStretch()

    def refresh(self):
        for i in reversed(range(self.sanpin_layout.count())):
            widget = self.sanpin_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        self._checkboxes.clear()

        with make_session(self.engine) as session:
            rules = session.execute(select(SanpinRule)).scalars().all()
            for rule in rules:
                cb = QCheckBox(rule.description)
                cb.setChecked(bool(rule.is_enabled))
                cb.setStyleSheet("QCheckBox { font-size: 13px; padding: 4px; }")
                self._checkboxes[rule.id] = cb
                self.sanpin_layout.addWidget(cb)

        if not self._checkboxes:
            lbl = QLabel("Санитарные правила не найдены в БД. Инициализируйте БД через db/schema.sql.")
            lbl.setStyleSheet("color: #7f8c8d; font-style: italic;")
            self.sanpin_layout.addWidget(lbl)

    def _save(self):
        with make_session(self.engine) as session:
            for rule_id, cb in self._checkboxes.items():
                session.execute(
                    update(SanpinRule).where(SanpinRule.id == rule_id).values(
                        is_enabled=int(cb.isChecked())
                    )
                )
            session.commit()
        QMessageBox.information(self, "Сохранено", "Настройки санитарных норм обновлены.")
