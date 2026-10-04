"""
Наполняет SQLite-файл (созданный по db/schema.sql) тестовой школой через
обычные SQL-запросы — реалистичный сценарий: 2 смены, деление на подгруппы
по иностранному языку (раздел 3 ТЗ).
"""
from __future__ import annotations
import sqlite3
from typing import List, Dict, Any


def seed(conn: sqlite3.Connection) -> int:
    """
    Наполняет базу данных тестовой школой с реалистичными данными.
    
    Returns:
        int: ID учебного года для построения контекста
    """
    cur = conn.cursor()

    cur.execute("INSERT INTO academic_years (label, is_active) VALUES ('2026/2027', 1)")
    year_id = cur.lastrowid

    cur.execute("INSERT INTO shifts (name, ordinal) VALUES ('I смена', 1)")
    shift1 = cur.lastrowid
    cur.execute("INSERT INTO shifts (name, ordinal) VALUES ('II смена', 2)")
    shift2 = cur.lastrowid

    subjects = [
        ("Математика", 8, 0, 1, 0),
        ("Русский язык", 8, 0, 1, 0),
        ("Физическая культура и здоровье", 3, 1, 0, 0),
        ("История", 5, 0, 0, 0),
        ("Биология", 5, 0, 0, 0),
        ("Иностранный язык (английский)", 6, 0, 0, 0),
        ("Информатика", 6, 0, 0, 0),
        ("Литературное чтение", 4, 0, 0, 0),
        ("Окружающий мир", 3, 0, 0, 0),
    ]
    subject_ids: Dict[str, int] = {}
    for name, rank, is_pe, is_heavy, allows_double in subjects:
        cur.execute(
            """INSERT INTO subjects (name, difficulty_rank, is_physical_education,
                                      is_heavy_subject, allows_double_lesson)
               VALUES (?, ?, ?, ?, ?)""",
            (name, rank, is_pe, is_heavy, allows_double),
        )
        subject_ids[name] = cur.lastrowid

    cabinets = [("101", 30, "general"), ("102", 30, "general"),
                ("Спортзал", 40, "gym"), ("Каб. информатики", 15, "computer")]
    cabinet_ids: Dict[str, int] = {}
    for number, capacity, room_type in cabinets:
        cur.execute("INSERT INTO cabinets (number, capacity, room_type) VALUES (?, ?, ?)",
                    (number, capacity, room_type))
        cabinet_ids[number] = cur.lastrowid

    teacher_names = [
        "Иванова А.П.", "Петров С.И.", "Сидорова М.В.", "Кузнецов Д.А.",
        "Смирнова Е.Н.", "Новикова О.С.", "Волков И.Р.", "Морозова Т.К.",
        "Соколов В.Л.", "Егорова Н.Ю.",
    ]
    teacher_ids: Dict[str, int] = {}
    for name in teacher_names:
        cur.execute("INSERT INTO teachers (full_name, max_load_hours) VALUES (?, 24)", (name,))
        teacher_ids[name] = cur.lastrowid

    def add_class(grade: int, letter: str, shift_id: int) -> int:
        """
        Добавляет класс в базу данных.
        
        Args:
            grade: Номер класса (1-12)
            letter: Буква класса
            shift_id: ID смены
            
        Returns:
            int: ID добавленного класса
        """
        cur.execute(
            "INSERT INTO classes (academic_year_id, grade, letter, shift_id) VALUES (?, ?, ?, ?)",
            (year_id, grade, letter, shift_id),
        )
        return cur.lastrowid

    def add_class_subject(class_id: int, subject_name: str, hours: int, is_split: int = 0) -> int:
        """
        Добавляет предмет в учебный план класса.
        
        Args:
            class_id: ID класса
            subject_name: Название предмета
            hours: Количество часов в неделю
            is_split: Признак деления на подгруппы
            
        Returns:
            int: ID добавленного предмета класса
        """
        cur.execute(
            "INSERT INTO class_subjects (class_id, subject_id, hours_per_week, is_split) VALUES (?, ?, ?, ?)",
            (class_id, subject_ids[subject_name], hours, is_split),
        )
        return cur.lastrowid

    def add_group(class_subject_id: int, teacher_name: str, group_number: int = 1, cabinet: str = None) -> None:
        """
        Добавляет подгруппу в базу данных.
        
        Args:
            class_subject_id: ID предмета класса
            teacher_name: ФИО учителя
            group_number: Номер подгруппы (1 или 2)
            cabinet: Номер кабинета (если указан)
        """
        cur.execute(
            """INSERT INTO subject_groups (class_subject_id, group_number, teacher_id, cabinet_id)
               VALUES (?, ?, ?, ?)""",
            (class_subject_id, group_number, teacher_ids[teacher_name],
             cabinet_ids[cabinet] if cabinet else None),
        )

    # 5 "А" — I смена, обычный учебный план с делением на подгруппы по языку
    c5a = add_class(5, "А", shift1)
    cs = add_class_subject(c5a, "Математика", 5)
    add_group(cs, "Иванова А.П.", cabinet="101")
    cs = add_class_subject(c5a, "Русский язык", 4)
    add_group(cs, "Петров С.И.", cabinet="101")
    cs = add_class_subject(c5a, "Физическая культура и здоровье", 2)
    add_group(cs, "Сидорова М.В.", cabinet="Спортзал")
    cs = add_class_subject(c5a, "История", 2)
    add_group(cs, "Кузнецов Д.А.", cabinet="102")
    cs = add_class_subject(c5a, "Биология", 2)
    add_group(cs, "Смирнова Е.Н.", cabinet="102")
    cs = add_class_subject(c5a, "Информатика", 2)
    add_group(cs, "Волков И.Р.", cabinet="Каб. информатики")
    cs = add_class_subject(c5a, "Иностранный язык (английский)", 3, is_split=1)
    add_group(cs, "Новикова О.С.", group_number=1)
    add_group(cs, "Морозова Т.К.", group_number=2)

    # 5 "Б" — I смена, частично те же учителя (проверка конфликтов между классами)
    c5b = add_class(5, "Б", shift1)
    cs = add_class_subject(c5b, "Математика", 5)
    add_group(cs, "Иванова А.П.", cabinet="101")   # тот же учитель математики
    cs = add_class_subject(c5b, "Русский язык", 4)
    add_group(cs, "Соколов В.Л.", cabinet="101")
    cs = add_class_subject(c5b, "Физическая культура и здоровье", 2)
    add_group(cs, "Сидорова М.В.", cabinet="Спортзал")  # тот же физкультурник
    cs = add_class_subject(c5b, "История", 2)
    add_group(cs, "Кузнецов Д.А.", cabinet="102")
    cs = add_class_subject(c5b, "Иностранный язык (английский)", 3, is_split=1)
    add_group(cs, "Новикова О.С.", group_number=1)  # та же учительница, что и в 5А
    add_group(cs, "Егорова Н.Ю.", group_number=2)

    # 2 "А" — тоже I смена (1-4 классы не ставятся во II смену по нашим sanpin_rules),
    # проверка лимита уроков/день для младшей параллели
    c2a = add_class(2, "А", shift1)
    cs = add_class_subject(c2a, "Математика", 5)
    add_group(cs, "Иванова А.П.")
    cs = add_class_subject(c2a, "Литературное чтение", 4)
    add_group(cs, "Новикова О.С.")
    cs = add_class_subject(c2a, "Окружающий мир", 2)
    add_group(cs, "Смирнова Е.Н.")
    cs = add_class_subject(c2a, "Физическая культура и здоровье", 2)
    add_group(cs, "Сидорова М.В.", cabinet="Спортзал")

    # 7 "А" — II смена
    c7a = add_class(7, "А", shift2)
    cs = add_class_subject(c7a, "Математика", 5)
    add_group(cs, "Петров С.И.")
    cs = add_class_subject(c7a, "История", 3)
    add_group(cs, "Кузнецов Д.А.")
    cs = add_class_subject(c7a, "Информатика", 2)
    add_group(cs, "Волков И.Р.", cabinet="Каб. информатики")
    cs = add_class_subject(c7a, "Физическая культура и здоровье", 2)
    add_group(cs, "Сидорова М.В.", cabinet="Спортзал")

    conn.commit()
    return year_id
