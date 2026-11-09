"""Validated schedule JSON files, including the school data they depend on."""
from __future__ import annotations

from typing import Any

from app.services.reference_scheduler import Gene, ScheduleContext
from app.services.school_data import (
    SCHOOL_FORMAT,
    build_context,
    validate_school_data,
)

SCHEDULE_FORMAT = "school-scheduler-schedule"
SCHEDULE_VERSION = 1


def make_schedule_document(school_data: dict[str, Any], context: ScheduleContext, chromosome) -> dict[str, Any]:
    """Create a portable schedule document with its source school definition."""
    school = validate_school_data(school_data)
    if len(chromosome) != len(context.lesson_instances):
        raise ValueError("Длина расписания не соответствует учебному плану")
    checked_context, _, _ = build_context(school)
    if len(checked_context.lesson_instances) != len(context.lesson_instances):
        raise ValueError("Данные школы не соответствуют контексту расписания")
    entries = []
    for index, instance in enumerate(context.lesson_instances):
        gene = chromosome[index]
        entries.append({
            "group_id": instance.subject_group_id,
            "occurrence": instance.occurrence,
            "day": gene.day,
            "lesson": gene.lesson_number,
        })
    return {
        "format": SCHEDULE_FORMAT,
        "version": SCHEDULE_VERSION,
        "school": school,
        "schedule": entries,
    }


def load_schedule_document(document: Any):
    """Validate schedule file and return school data, model, labels and chromosome."""
    if not isinstance(document, dict):
        raise ValueError("Корень файла расписания должен быть JSON-объектом")
    if document.get("format") != SCHEDULE_FORMAT:
        raise ValueError("Это не файл расписания School Scheduler")
    if document.get("version") != SCHEDULE_VERSION:
        raise ValueError(f"Неподдерживаемая версия расписания: {document.get('version')!r}")

    school = validate_school_data(document.get("school"))
    context, subjects, classes = build_context(school)
    entries = document.get("schedule")
    if not isinstance(entries, list) or len(entries) != len(context.lesson_instances):
        raise ValueError("В файле должно быть ровно по одной записи на каждый учебный час")

    expected = {
        (instance.subject_group_id, instance.occurrence): index
        for index, instance in enumerate(context.lesson_instances)
    }
    chromosome: list[Gene | None] = [None] * len(context.lesson_instances)
    for entry_index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"schedule[{entry_index}] должен быть объектом")
        key = (entry.get("group_id"), entry.get("occurrence"))
        if key not in expected:
            raise ValueError(f"Неизвестный или некорректный учебный час: {key}")
        index = expected[key]
        if chromosome[index] is not None:
            raise ValueError(f"Учебный час {key} встречается в файле повторно")
        day = entry.get("day")
        lesson = entry.get("lesson")
        group = context.groups[context.lesson_instances[index].group_index]
        if isinstance(day, bool) or not isinstance(day, int) or not 1 <= day <= context.days_per_week:
            raise ValueError(f"Некорректный день для учебного часа {key}: {day!r}")
        max_lesson = context.max_lessons_for_grade(group.grade)
        if isinstance(lesson, bool) or not isinstance(lesson, int) or not 1 <= lesson <= max_lesson:
            raise ValueError(f"Некорректный номер урока для учебного часа {key}: {lesson!r}")
        chromosome[index] = Gene(day, lesson)

    if any(gene is None for gene in chromosome):
        raise ValueError("В файле отсутствуют некоторые учебные часы")
    return school, context, subjects, classes, chromosome
