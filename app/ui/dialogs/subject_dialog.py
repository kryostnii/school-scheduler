"""Диалог добавления/редактирования предмета."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QSpinBox,
    QCheckBox, QPushButton, QHBoxLayout, QMessageBox,
)


class SubjectDialog(QDialog):
    def __init__(self, parent=None, subject=None):
        super().__init__(parent)
        self.setWindowTitle("Предмет" if not subject else "Редактирование предмета")
        self.setMinimumWidth(400)
        self.result_data = None

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Название предмета")
        form.addRow("Название:", self.name_edit)

        self.rank_spin = QSpinBox()
        self.rank_spin.setRange(1, 10)
        self.rank_spin.setValue(5)
        form.addRow("Ранг трудности:", self.rank_spin)

        self.is_pe_check = QCheckBox("Физическая культура")
        form.addRow("", self.is_pe_check)

        self.is_heavy_check = QCheckBox("Большое умственное напряжение")
        form.addRow("", self.is_heavy_check)

        self.allows_double_check = QCheckBox("Разрешены сдвоенные уроки")
        form.addRow("", self.allows_double_check)

        layout.addLayout(form)

        if subject:
            self.name_edit.setText(subject.name)
            self.rank_spin.setValue(subject.difficulty_rank)
            self.is_pe_check.setChecked(bool(subject.is_physical_education))
            self.is_heavy_check.setChecked(bool(subject.is_heavy_subject))
            self.allows_double_check.setChecked(bool(subject.allows_double_lesson))

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
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название предмета.")
            return
        self.result_data = {
            "name": name,
            "difficulty_rank": self.rank_spin.value(),
            "is_physical_education": int(self.is_pe_check.isChecked()),
            "is_heavy_subject": int(self.is_heavy_check.isChecked()),
            "allows_double_lesson": int(self.allows_double_check.isChecked()),
        }
        self.accept()
