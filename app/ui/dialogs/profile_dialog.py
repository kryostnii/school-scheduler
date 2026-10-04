"""Диалог создания/редактирования профильной пары."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox,
    QPushButton, QHBoxLayout, QMessageBox, QLabel,
)


class ProfileDialog(QDialog):
    def __init__(self, parent=None, engine=None,
                 existing_class_subjects=None, profile_to_edit=None):
        super().__init__(parent)
        self.engine = engine
        self.result_data = None
        self._existing = existing_class_subjects or []

        if profile_to_edit:
            self.setWindowTitle("Редактирование профиля")
        else:
            self.setWindowTitle("Новый профиль")

        self.setMinimumWidth(460)
        layout = QVBoxLayout(self)

        info = QLabel(
            "Профильная пара — два предмета одного класса, которые\n"
            "проходят одновременно в разных подгруппах.\n"
            "В расписании класса они отображаются как split-ячейка."
        )
        info.setStyleSheet("font-size: 11px; color: #7f8c8d; padding-bottom: 4px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        form = QFormLayout()

        self.class_combo = QComboBox()
        self.class_combo.setStyleSheet(
            "QComboBox { padding: 6px; font-size: 12px; }"
        )
        classes_seen = set()
        for cs in self._existing:
            label = cs.get("class_label", "")
            cid = cs.get("class_id")
            if cid not in classes_seen:
                classes_seen.add(cid)
                self.class_combo.addItem(label, cid)
        self.class_combo.currentIndexChanged.connect(self._on_class_changed)
        form.addRow("Класс:", self.class_combo)

        self.subj1_combo = QComboBox()
        self.subj1_combo.setStyleSheet(
            "QComboBox { padding: 6px; font-size: 12px; }"
        )
        form.addRow("Предмет 1:", self.subj1_combo)

        self.subj2_combo = QComboBox()
        self.subj2_combo.setStyleSheet(
            "QComboBox { padding: 6px; font-size: 12px; }"
        )
        form.addRow("Предмет 2:", self.subj2_combo)

        layout.addLayout(form)

        if profile_to_edit:
            self._set_initial(profile_to_edit)

        btn_layout = QHBoxLayout()
        cancel = QPushButton("Отмена")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Сохранить")
        save.setDefault(True)
        save.setStyleSheet(
            "QPushButton { padding: 8px 20px; background: #27ae60; color: white; "
            "border: none; border-radius: 6px; font-weight: bold; }"
            "QPushButton:hover { background: #2ecc71; }"
        )
        save.clicked.connect(self._on_save)
        btn_layout.addStretch()
        btn_layout.addWidget(cancel)
        btn_layout.addWidget(save)
        layout.addLayout(btn_layout)

        if self.class_combo.count() > 0:
            self._on_class_changed()

    def _on_class_changed(self):
        self.subj1_combo.clear()
        self.subj2_combo.clear()
        cid = self.class_combo.currentData()
        if cid is None:
            return
        for cs in self._existing:
            if cs.get("class_id") == cid:
                label = f"{cs.get('subject_name', '?')} (ID {cs.get('cs_id')})"
                self.subj1_combo.addItem(label, cs.get("cs_id"))
                self.subj2_combo.addItem(label, cs.get("cs_id"))
        if self.subj2_combo.count() > 1:
            self.subj2_combo.setCurrentIndex(1)

    def _set_initial(self, profile):
        cid = profile.get("class_id")
        for i in range(self.class_combo.count()):
            if self.class_combo.itemData(i) == cid:
                self.class_combo.setCurrentIndex(i)
                break
        self._on_class_changed()
        cs1 = profile.get("cs1_id")
        cs2 = profile.get("cs2_id")
        if cs1 is not None:
            for i in range(self.subj1_combo.count()):
                if self.subj1_combo.itemData(i) == cs1:
                    self.subj1_combo.setCurrentIndex(i)
                    break
        if cs2 is not None:
            for i in range(self.subj2_combo.count()):
                if self.subj2_combo.itemData(i) == cs2:
                    self.subj2_combo.setCurrentIndex(i)
                    break

    def _on_save(self):
        cs1_id = self.subj1_combo.currentData()
        cs2_id = self.subj2_combo.currentData()
        class_id = self.class_combo.currentData()

        if cs1_id is None or cs2_id is None:
            QMessageBox.warning(self, "Ошибка", "Выберите два предмета.")
            return
        if cs1_id == cs2_id:
            QMessageBox.warning(self, "Ошибка", "Выберите два разных предмета.")
            return

        subj1 = self.subj1_combo.currentText().split(" (ID ")[0]
        subj2 = self.subj2_combo.currentText().split(" (ID ")[0]

        self.result_data = {
            "class_id": class_id,
            "cs1_id": cs1_id,
            "cs2_id": cs2_id,
            "label": f"{subj1} / {subj2}",
        }
        self.accept()
