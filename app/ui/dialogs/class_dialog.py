"""Диалог добавления/редактирования класса."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QSpinBox,
    QComboBox, QPushButton, QHBoxLayout, QMessageBox,
)


class ClassDialog(QDialog):
    def __init__(self, parent=None, school_class=None, shifts=None, academic_year_id=None):
        super().__init__(parent)
        self.setWindowTitle("Класс" if not school_class else "Редактирование класса")
        self.setMinimumWidth(350)
        self.result_data = None
        self._academic_year_id = academic_year_id

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.grade_spin = QSpinBox()
        self.grade_spin.setRange(1, 12)
        self.grade_spin.setValue(5)
        form.addRow("Параллель:", self.grade_spin)

        self.letter_edit = QLineEdit()
        self.letter_edit.setPlaceholderText("А")
        self.letter_edit.setMaxLength(2)
        form.addRow("Буква:", self.letter_edit)

        self.shift_combo = QComboBox()
        if shifts:
            for sh in shifts:
                self.shift_combo.addItem(sh.name, sh.id)
        form.addRow("Смена:", self.shift_combo)

        layout.addLayout(form)

        if school_class:
            self.grade_spin.setValue(school_class.grade)
            self.letter_edit.setText(school_class.letter)
            for i in range(self.shift_combo.count()):
                if self.shift_combo.itemData(i) == school_class.shift_id:
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
        letter = self.letter_edit.text().strip()
        if not letter:
            QMessageBox.warning(self, "Ошибка", "Введите букву класса.")
            return
        self.result_data = {
            "academic_year_id": self._academic_year_id,
            "grade": self.grade_spin.value(),
            "letter": letter,
            "shift_id": self.shift_combo.currentData(),
        }
        self.accept()
