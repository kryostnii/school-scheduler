"""Диалог добавления/редактирования кабинета."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QSpinBox,
    QComboBox, QPushButton, QHBoxLayout, QMessageBox,
)


class CabinetDialog(QDialog):
    def __init__(self, parent=None, cabinet=None, shifts=None):
        super().__init__(parent)
        self.setWindowTitle("Кабинет" if not cabinet else "Редактирование кабинета")
        self.setMinimumWidth(350)
        self.result_data = None

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.number_edit = QLineEdit()
        self.number_edit.setPlaceholderText("101")
        form.addRow("Номер:", self.number_edit)

        self.capacity_spin = QSpinBox()
        self.capacity_spin.setRange(0, 500)
        self.capacity_spin.setValue(30)
        form.addRow("Вместимость:", self.capacity_spin)

        self.type_combo = QComboBox()
        room_types = [
            ("general", "Общий"),
            ("gym", "Спортзал"),
            ("computer", "Компьютерный"),
            ("chemistry", "Химия"),
            ("physics", "Физика"),
            ("music", "Музыка"),
            ("art", "ИЗО"),
        ]
        for key, label in room_types:
            self.type_combo.addItem(label, key)
        form.addRow("Тип:", self.type_combo)

        self.shift_combo = QComboBox()
        self.shift_combo.addItem("— обе смены —", None)
        if shifts:
            for sh in shifts:
                self.shift_combo.addItem(sh.name, sh.id)
        form.addRow("Смена:", self.shift_combo)

        layout.addLayout(form)

        if cabinet:
            self.number_edit.setText(cabinet.number)
            self.capacity_spin.setValue(cabinet.capacity or 0)
            for i in range(self.type_combo.count()):
                if self.type_combo.itemData(i) == cabinet.room_type:
                    self.type_combo.setCurrentIndex(i)
                    break
            for i in range(self.shift_combo.count()):
                if self.shift_combo.itemData(i) == cabinet.shift_id:
                    self.shift_combo.setCurrentIndex(i)
                    break

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

    def _on_save(self):
        number = self.number_edit.text().strip()
        if not number:
            QMessageBox.warning(self, "Ошибка", "Введите номер кабинета.")
            return
        self.result_data = {
            "number": number,
            "capacity": self.capacity_spin.value(),
            "room_type": self.type_combo.currentData(),
            "shift_id": self.shift_combo.currentData(),
        }
        self.accept()
