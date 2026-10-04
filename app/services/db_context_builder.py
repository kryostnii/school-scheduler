"""
Мост между БД (db/schema.sql) и алгоритмом (reference_scheduler.py / будущий scheduler_core).

Сознательно использует только встроенный модуль sqlite3, а не SQLAlchemy
(app/data/models.py) — чтобы этот слой можно было тестировать и гонять
без установки зависимостей (в частности, в среде без интернета).
На данных, взятых через SQLAlchemy-сессию, этот же контекст можно собрать
аналогично: см. build_context_from_rows(), который принимает уже готовые
списки строк и не зависит от способа, которым они получены.
"""
from __future__ import annotations

import sqlite3
from typing import List, Dict, Any
from app.services.reference_scheduler import ScheduleContext, SubjectGroupInfo


def _dict_rows(conn: sqlite3.Connection, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """Извлекает строки из БД и преобразует их в список словарей."""
    cur = conn.execute(query, params)
    columns = [desc[0] for desc in cur.description]
    return [dict(zip(columns, row)) for row in cur.fetchall()]


def build_context_from_db(conn: sqlite3.Connection, academic_year_id: int) -> ScheduleContext:
    """
    Собирает ScheduleContext для одного учебного года из живой SQLite-БД
    (раздел 3 ТЗ: атомарная единица планирования — subject_groups).
    
    Args:
        conn: Подключение к SQLite базе данных
        academic_year_id: ID учебного года для построения контекста
        
    Returns:
        ScheduleContext: Структура данных для алгоритма планирования
    """
    rows = _dict_rows(conn, """
        SELECT
            sg.id                AS group_id,
            c.id                 AS class_id,
            c.grade              AS grade,
            sh.ordinal            AS shift,
            sg.teacher_id        AS teacher_id,
            sg.cabinet_id        AS cabinet_id,
            cs.hours_per_week    AS hours_per_week,
            s.is_physical_education AS is_pe,
            s.is_heavy_subject   AS is_heavy,
            s.allows_double_lesson AS allows_double
        FROM subject_groups sg
        JOIN class_subjects cs ON cs.id = sg.class_subject_id
        JOIN classes c         ON c.id = cs.class_id
        JOIN shifts sh         ON sh.id = c.shift_id
        JOIN subjects s        ON s.id = cs.subject_id
        WHERE c.academic_year_id = ?
    """, (academic_year_id,))

    ctx = ScheduleContext(days_per_week=6)
    for row in rows:
        ctx.groups.append(SubjectGroupInfo(
            id=row["group_id"],
            class_id=row["class_id"],
            grade=row["grade"],
            teacher_id=row["teacher_id"],
            cabinet_id=row["cabinet_id"],
            shift=row["shift"],
            hours_per_week=row["hours_per_week"],
            is_physical_education=bool(row["is_pe"]),
            is_heavy_subject=bool(row["is_heavy"]),
            allows_double_lesson=bool(row["allows_double"]),
        ))
    ctx.build_lesson_instances()
    return ctx


def save_chromosome_to_db(conn: sqlite3.Connection, ctx: ScheduleContext, chromosome) -> None:
    """
    Записывает результат генерации в timetable_entries (раздел 5.3 ТЗ:
    "модуль интерактивного расписания" читает готовое расписание из этой таблицы).
    Перед записью удаляет старые записи для тех же subject_group_id, чтобы
    повторный запуск генерации не плодил дубликаты.
    
    Args:
        conn: Подключение к SQLite базе данных
        ctx: Контекст расписания с метаданными
        chromosome: Хромосома (расписание) для сохранения
    """
    group_ids = {g.id for g in ctx.groups}
    conn.executemany(
        "DELETE FROM timetable_entries WHERE subject_group_id = ?",
        [(gid,) for gid in group_ids],
    )
    rows_to_insert = []
    for i, li in enumerate(ctx.lesson_instances):
        gene = chromosome[i]
        g = ctx.groups[li.group_index]
        rows_to_insert.append((li.subject_group_id, gene.day, gene.lesson_number, g.cabinet_id))
    conn.executemany(
        """INSERT INTO timetable_entries (subject_group_id, day_of_week, lesson_number, cabinet_id)
           VALUES (?, ?, ?, ?)""",
        rows_to_insert,
    )
    conn.commit()
