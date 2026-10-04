"""Диалог добавления/редактирования подгруппы (subject_group)."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QSpinBox,
    QPushButton, QHBoxLayout, QMessageBox,
)


class SubjectGroupDialog(QDialog):
    def __init__(self, parent=None, subject_group=None,
                 class_subjects=None, teachers=None, cabinets=None,
                 current_class_subject_id=None):
        super().__init__(parent)
        self.setWindowTitle("Подгруппа" if not subject_group else "Редактирование подгруппы")
        self.setMinimumWidth(420)
        self.result_data = None

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.cs_combo = QComboBox()
        if class_subjects:
            for cs in class_subjects:
                label = f"{cs.class_label} — {cs.subject_name}"
                self.cs_combo.addItem(label, cs.id)
        if current_class_subject_id is not None:
            self._set_combo(self.cs_combo, current_class_subject_id)
        form.addRow("Предмет класса:", self.cs_combo)

        self.group_spin = QSpinBox()
        self.group_spin.setRange(1, 5)
        self.group_spin.setValue(1)
        form.addRow("Номер подгруппы:", self.group_spin)

        self.teacher_combo = QComboBox()
        if teachers:
            for t in teachers:
                self.teacher_combo.addItem(t.full_name, t.id)
        form.addRow("Учитель:", self.teacher_combo)

        self.cabinet_combo = QComboBox()
        self.cabinet_combo.addItem("— не указан —", None)
        if cabinets:
            for cab in cabinets:
                self.cabinet_combo.addItem(
                    f"{cab.number} ({cab.room_type})", cab.id
                )
        form.addRow("Кабинет:", self.cabinet_combo)

        layout.addLayout(form)

        if subject_group:
            self._set_combo(self.cs_combo, subject_group.class_subject_id)
            self.group_spin.setValue(subject_group.group_number)
            self._set_combo(self.teacher_combo, subject_group.teacher_id)
            self._set_combo(self.cabinet_combo, subject_group.cabinet_id)

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
        if self.cs_combo.currentData() is None:
            QMessageBox.warning(self, "Ошибка", "Выберите предмет класса.")
            return
        if self.teacher_combo.currentData() is None:
            QMessageBox.warning(self, "Ошибка", "Выберите учителя.")
            return
        self.result_data = {
            "class_subject_id": self.cs_combo.currentData(),
            "group_number": self.group_spin.value(),
            "teacher_id": self.teacher_combo.currentData(),
            "cabinet_id": self.cabinet_combo.currentData(),
        }
        self.accept()
