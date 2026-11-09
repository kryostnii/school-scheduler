"""Validated JSON school-data format and conversion to scheduler context."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.reference_scheduler import ScheduleContext, SubjectGroupInfo

SCHOOL_FORMAT = "school-scheduler-school"
SCHOOL_VERSION = 1


def sample_school_data() -> dict[str, Any]:
    """Return editable starter data; users can save it and customize the JSON."""
    classes = [
        {"id": 101, "name": "5А", "grade": 5},
        {"id": 102, "name": "5Б", "grade": 5},
        {"id": 201, "name": "2А", "grade": 2},
    ]
    groups = []

    def add(class_id, subject, teacher_id, hours, *, pe=False, heavy=False, cabinet_id=None):
        groups.append({
            "id": len(groups) + 1,
            "class_id": class_id,
            "subject": subject,
            "teacher_id": teacher_id,
            "hours_per_week": hours,
            "cabinet_id": cabinet_id,
            "is_physical_education": pe,
            "is_heavy_subject": heavy,
        })

    add(101, "Математика", 1, 5, heavy=True)
    add(101, "Русский язык", 2, 4, heavy=True)
    add(101, "Физкультура", 3, 2, pe=True)
    add(101, "История", 4, 3)
    add(101, "Биология", 5, 2)
    add(102, "Математика", 1, 5, heavy=True)
    add(102, "Русский язык", 6, 4, heavy=True)
    add(102, "Физкультура", 3, 2, pe=True)
    add(102, "История", 7, 3)
    add(102, "Биология", 8, 2)
    add(201, "Математика", 9, 5, heavy=True)
    add(201, "Чтение", 10, 4)
    add(201, "Физкультура", 11, 2, pe=True)
    add(201, "Окружающий мир", 12, 3)

    return {
        "format": SCHOOL_FORMAT,
        "version": SCHOOL_VERSION,
        "school_name": "Демонстрационная школа",
        "days_per_week": 6,
        "classes": classes,
        "groups": groups,
    }


def validate_school_data(document: Any) -> dict[str, Any]:
    """Validate and normalize the versioned school JSON document."""
    if not isinstance(document, dict):
        raise ValueError("Корень файла должен быть JSON-объектом")
    if document.get("format") != SCHOOL_FORMAT:
        raise ValueError(f"Ожидался формат {SCHOOL_FORMAT!r}")
    if document.get("version") != SCHOOL_VERSION:
        raise ValueError(f"Неподдерживаемая версия данных школы: {document.get('version')!r}")
    days = document.get("days_per_week")
    if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= 7:
        raise ValueError("days_per_week должен быть целым числом от 1 до 7")
    school_name = document.get("school_name", "Школа")
    if not isinstance(school_name, str) or not school_name.strip():
        raise ValueError("school_name должен быть непустой строкой")

    raw_classes, raw_groups = document.get("classes"), document.get("groups")
    if not isinstance(raw_classes, list) or not raw_classes:
        raise ValueError("Добавьте хотя бы один класс в classes")
    if not isinstance(raw_groups, list) or not raw_groups:
        raise ValueError("Добавьте хотя бы одну учебную группу в groups")

    classes, class_ids = [], set()
    for index, row in enumerate(raw_classes):
        if not isinstance(row, dict):
            raise ValueError(f"classes[{index}] должен быть объектом")
        class_id = _positive_int(row.get("id"), f"classes[{index}].id")
        grade = _positive_int(row.get("grade"), f"classes[{index}].grade")
        if grade > 12:
            raise ValueError(f"classes[{index}].grade должен быть от 1 до 12")
        name = row.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"classes[{index}].name должен быть непустой строкой")
        if class_id in class_ids:
            raise ValueError(f"Повторяется ID класса: {class_id}")
        class_ids.add(class_id)
        classes.append({"id": class_id, "name": name.strip(), "grade": grade})

    groups, group_ids = [], set()
    for index, row in enumerate(raw_groups):
        if not isinstance(row, dict):
            raise ValueError(f"groups[{index}] должен быть объектом")
        group_id = _positive_int(row.get("id"), f"groups[{index}].id")
        class_id = _positive_int(row.get("class_id"), f"groups[{index}].class_id")
        if class_id not in class_ids:
            raise ValueError(f"groups[{index}] ссылается на отсутствующий class_id={class_id}")
        teacher_id = _positive_int(row.get("teacher_id"), f"groups[{index}].teacher_id")
        hours = row.get("hours_per_week")
        if isinstance(hours, bool) or not isinstance(hours, int) or not 1 <= hours <= 60:
            raise ValueError(f"groups[{index}].hours_per_week должен быть целым числом от 1 до 60")
        subject = row.get("subject")
        if not isinstance(subject, str) or not subject.strip():
            raise ValueError(f"groups[{index}].subject должен быть непустой строкой")
        cabinet_id = row.get("cabinet_id")
        if cabinet_id is not None:
            cabinet_id = _positive_int(cabinet_id, f"groups[{index}].cabinet_id")
        for flag in ("is_physical_education", "is_heavy_subject"):
            if flag in row and not isinstance(row[flag], bool):
                raise ValueError(f"groups[{index}].{flag} должен быть true или false")
        if group_id in group_ids:
            raise ValueError(f"Повторяется ID учебной группы: {group_id}")
        group_ids.add(group_id)
        groups.append({
            "id": group_id,
            "class_id": class_id,
            "subject": subject.strip(),
            "teacher_id": teacher_id,
            "hours_per_week": hours,
            "cabinet_id": cabinet_id,
            "is_physical_education": row.get("is_physical_education", False),
            "is_heavy_subject": row.get("is_heavy_subject", False),
        })

    return {
        "format": SCHOOL_FORMAT,
        "version": SCHOOL_VERSION,
        "school_name": school_name.strip(),
        "days_per_week": days,
        "classes": classes,
        "groups": groups,
    }


def _positive_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field} должен быть положительным целым числом")
    return value


def load_school_data(path: str | Path) -> dict[str, Any]:
    """Read and validate school JSON from disk."""
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Некорректный JSON: {exc}") from exc
    return validate_school_data(document)


def build_context(data: dict[str, Any]) -> tuple[ScheduleContext, dict[int, str], dict[int, str]]:
    """Convert validated school data to algorithm input and display labels."""
    school = validate_school_data(data)
    classes_by_id = {item["id"]: item for item in school["classes"]}
    context = ScheduleContext(days_per_week=school["days_per_week"])
    subject_names = {}
    class_names = {item["id"]: item["name"] for item in school["classes"]}
    for group in school["groups"]:
        class_row = classes_by_id[group["class_id"]]
        context.groups.append(SubjectGroupInfo(
            id=group["id"],
            class_id=group["class_id"],
            grade=class_row["grade"],
            teacher_id=group["teacher_id"],
            hours_per_week=group["hours_per_week"],
            cabinet_id=group["cabinet_id"],
            is_physical_education=group["is_physical_education"],
            is_heavy_subject=group["is_heavy_subject"],
        ))
        subject_names[group["id"]] = group["subject"]
    context.build_lesson_instances()
    return context, subject_names, class_names
