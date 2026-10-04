"""Диалог добавления/редактирования учителя."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QSpinBox,
    QComboBox, QPushButton, QHBoxLayout, QMessageBox,
)


class TeacherDialog(QDialog):
    def __init__(self, parent=None, teacher=None, cabinets=None, shifts=None):
        super().__init__(parent)
        self.setWindowTitle("Учитель" if not teacher else "Редактирование учителя")
        self.setMinimumWidth(400)
        self.result_data = None

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("ФИО учителя")
        form.addRow("ФИО:", self.name_edit)

        self.hours_spin = QSpinBox()
        self.hours_spin.setRange(1, 40)
        self.hours_spin.setValue(24)
        form.addRow("Макс. часов/нед.:", self.hours_spin)

        self.cabinet_combo = QComboBox()
        self.cabinet_combo.addItem("— нет —", None)
        if cabinets:
            for cab in cabinets:
                self.cabinet_combo.addItem(f"{cab.number} ({cab.room_type})", cab.id)
        form.addRow("Кабинет:", self.cabinet_combo)

        self.shift_combo = QComboBox()
        self.shift_combo.addItem("— любая —", None)
        if shifts:
            for sh in shifts:
                self.shift_combo.addItem(sh.name, sh.id)
        form.addRow("Смена:", self.shift_combo)

        layout.addLayout(form)

        if teacher:
            self.name_edit.setText(teacher.full_name)
            self.hours_spin.setValue(teacher.max_load_hours)
            self._set_combo(self.cabinet_combo, teacher.home_cabinet_id)
            self._set_combo(self.shift_combo, teacher.shift_id)

        btn_layout = QHBoxLayout()
        cancel = QPushButton("Отмена")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Сохранить")
        save.setDefault(True)
        save.clicked.connect(self._on_save)
        btn_layout.addStretch()
        btn_layout.addWidget(cancel)
        btn_layout.addWidget(save)
        layout.addLayout(btn_layout)

    def _set_combo(self, combo, value):
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i)
                break

    def _on_save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите ФИО учителя.")
            return
        self.result_data = {
            "full_name": name,
            "max_load_hours": self.hours_spin.value(),
            "home_cabinet_id": self.cabinet_combo.currentData(),
            "shift_id": self.shift_combo.currentData(),
        }
        self.accept()
