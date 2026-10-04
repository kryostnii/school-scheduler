"""Диалог добавления/редактирования учебного плана (class_subject)."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QSpinBox,
    QCheckBox, QPushButton, QHBoxLayout, QMessageBox,
)


class ClassSubjectDialog(QDialog):
    def __init__(self, parent=None, class_subject=None,
                 classes=None, subjects=None):
        super().__init__(parent)
        self.setWindowTitle("Предмет класса" if not class_subject else "Редактирование предмета класса")
        self.setMinimumWidth(420)
        self.result_data = None

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.class_combo = QComboBox()
        if classes:
            for c in classes:
                self.class_combo.addItem(f"{c.grade}{c.letter}", c.id)
        form.addRow("Класс:", self.class_combo)

        self.subject_combo = QComboBox()
        if subjects:
            for s in subjects:
                self.subject_combo.addItem(s.name, s.id)
        form.addRow("Предмет:", self.subject_combo)

        self.hours_spin = QSpinBox()
        self.hours_spin.setRange(1, 10)
        self.hours_spin.setValue(2)
        form.addRow("Часов в неделю:", self.hours_spin)

        self.split_check = QCheckBox("Деление на подгруппы")
        self.split_check.setToolTip(
            "Например, иностранный язык: класс делится на 2 группы"
        )
        form.addRow("", self.split_check)

        layout.addLayout(form)

        if class_subject:
            self._set_combo(self.class_combo, class_subject.class_id)
            self._set_combo(self.subject_combo, class_subject.subject_id)
            self.hours_spin.setValue(class_subject.hours_per_week)
            self.split_check.setChecked(bool(class_subject.is_split))

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
                return

    def _on_save(self):
        if self.class_combo.currentData() is None:
            QMessageBox.warning(self, "Ошибка", "Выберите класс.")
            return
        if self.subject_combo.currentData() is None:
            QMessageBox.warning(self, "Ошибка", "Выберите предмет.")
            return
        self.result_data = {
            "class_id": self.class_combo.currentData(),
            "subject_id": self.subject_combo.currentData(),
            "hours_per_week": self.hours_spin.value(),
            "is_split": int(self.split_check.isChecked()),
        }
        self.accept()
