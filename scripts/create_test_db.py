"""
Создаёт тестовую БД school_test.sqlite3 с реалистичной школой:
  - 18 классов (1–11), 2 параллели на младших, по 1 на старших
  - 2 смены
  - 25 учителей
  - Полный учебный план с подгруппами по языку/информатике
  - Генерация расписания + запись в timetable_entries

Запуск:  python scripts/create_test_db.py
Результат: school_test.sqlite3 в корне проекта
"""
import sys
import os
import sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "school_test.sqlite3")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "schema.sql")


def create_school(conn: sqlite3.Connection) -> int:
    cur = conn.cursor()

    cur.execute("INSERT INTO academic_years (label, is_active) VALUES ('2025/2026', 0)")
    cur.execute("INSERT INTO academic_years (label, is_active) VALUES ('2026/2027', 1)")
    year_id = cur.lastrowid

    cur.execute("INSERT INTO shifts (name, ordinal) VALUES ('I смена', 1)")
    shift1 = cur.lastrowid
    cur.execute("INSERT INTO shifts (name, ordinal) VALUES ('II смена', 2)")
    shift2 = cur.lastrowid

    subjects_data = [
        # (name, rank, is_pe, is_heavy, allows_double, split)
        ("Математика",                    8, 0, 1, 0, 0),
        ("Русский язык",                  8, 0, 1, 0, 0),
        ("Белорусский язык",              7, 0, 1, 0, 0),
        ("Литературное чтение",           4, 0, 0, 0, 0),
        ("Окружающий мир",                3, 0, 0, 0, 0),
        ("Физическая культура и здоровье",3, 1, 0, 0, 0),
        ("Иностранный язык (английский)", 6, 0, 0, 0, 1),
        ("Иностранный язык (немецкий)",   6, 0, 0, 0, 1),
        ("История Беларуси",              5, 0, 0, 0, 0),
        ("Всемирная история",             5, 0, 0, 0, 0),
        ("География",                     4, 0, 0, 0, 0),
        ("Биология",                      4, 0, 0, 0, 0),
        ("Химия",                         7, 0, 1, 0, 0),
        ("Физика",                        7, 0, 1, 0, 0),
        ("Информатика",                   6, 0, 0, 0, 1),
        ("Музыка",                        2, 0, 0, 0, 0),
        ("Изобразительное искусство",     2, 0, 0, 0, 0),
        ("Технология (мальчики)",         3, 0, 0, 0, 0),
        ("Технология (девочки)",          3, 0, 0, 0, 0),
        ("Обществоведение",              4, 0, 0, 0, 0),
        ("Английский язык (углублённый)", 7, 0, 0, 0, 1),
    ]
    subject_ids = {}
    for name, rank, is_pe, is_heavy, allows_double, _ in subjects_data:
        cur.execute(
            """INSERT INTO subjects (name, difficulty_rank, is_physical_education,
                                      is_heavy_subject, allows_double_lesson)
               VALUES (?, ?, ?, ?, ?)""",
            (name, rank, is_pe, is_heavy, allows_double),
        )
        subject_ids[name] = cur.lastrowid

    cabinets_data = [
        ("101", 32, "general", 1),
        ("102", 32, "general", 1),
        ("103", 32, "general", 1),
        ("104", 32, "general", 1),
        ("201", 32, "general", 1),
        ("202", 32, "general", 1),
        ("203", 32, "general", 2),
        ("204", 32, "general", 2),
        ("301", 32, "general", 2),
        ("302", 32, "general", 2),
        ("Спортзал", 50, "gym", None),
        ("Каб. информатики", 20, "computer", None),
        ("Каб. физики", 24, "physics", None),
        ("Каб. химии", 24, "chemistry", None),
        ("Каб. музыки", 30, "general", None),
        ("Каб. ИЗО", 25, "general", None),
        ("Мастерская", 20, "general", None),
    ]
    cabinet_ids = {}
    for number, capacity, room_type, shift in cabinets_data:
        cur.execute(
            "INSERT INTO cabinets (number, capacity, room_type, shift_id) VALUES (?, ?, ?, ?)",
            (number, capacity, room_type, shift),
        )
        cabinet_ids[number] = cur.lastrowid

    teachers_data = [
        # I смена — основные
        ("Петрова Анна Михайловна",          24, 1, None),
        ("Сидоренко Сергей Викторович",       24, 1, None),
        ("Козлова Ирина Николаевна",          20, 1, None),
        ("Морозова Татьяна Петровна",         24, 1, None),
        ("Новикова Ольга Сергеевна",          20, 1, None),
        ("Волков Игорь Романович",            18, 1, "Каб. информатики"),
        ("Белова Елена Александровна",         24, 1, None),
        ("Кузнецов Дмитрий Андреевич",        24, 1, None),
        ("Захарова Наталья Викторовна",        20, 1, None),
        ("Павлов Алексей Иванович",           24, 1, None),
        ("Соколова Виктория Львовна",          18, 1, None),
        ("Орлова Марина Дмитриевна",           20, 1, None),
        ("Фёдорова Светлана Юрьевна",          24, 1, None),
        # II смена
        ("Лебедев Павел Сергеевич",           24, 2, None),
        ("Кравченко Оксана Владимировна",      24, 2, None),
        ("Егоров Николай Петрович",           20, 2, None),
        ("Васильева Тамара Ивановна",          24, 2, None),
        ("Семёнов Андрей Николаевич",         24, 2, None),
        ("Романова Галина Степановна",         18, 2, None),
        ("Тихонов Владимир Алексеевич",        20, 2, None),
        ("Григорьева Людмила Павловна",        24, 2, None),
        # Специалисты (обе смены)
        ("Степанова Мария Константиновна",     18, None, None),  # физкультура
        ("Жуков Виктор Николаевич",            18, None, None),  # физкультура
        ("Петренко Алла Максимовна",           12, None, None),  # музыка/ИЗО
        ("Давыдова Екатерина Олеговна",        12, None, None),  # труд
    ]
    teacher_ids = {}
    for name, hours, shift, home_cab in teachers_data:
        home_id = cabinet_ids.get(home_cab) if home_cab else None
        cur.execute(
            "INSERT INTO teachers (full_name, max_load_hours, home_cabinet_id, shift_id) "
            "VALUES (?, ?, ?, ?)",
            (name, hours, home_id, shift),
        )
        teacher_ids[name] = cur.lastrowid

    def add_class(grade, letter, shift_id):
        cur.execute(
            "INSERT INTO classes (academic_year_id, grade, letter, shift_id) VALUES (?, ?, ?, ?)",
            (year_id, grade, letter, shift_id),
        )
        return cur.lastrowid

    def add_cs(class_id, subj, hours, split=0):
        cur.execute(
            "INSERT INTO class_subjects (class_id, subject_id, hours_per_week, is_split) "
            "VALUES (?, ?, ?, ?)",
            (class_id, subject_ids[subj], hours, split),
        )
        return cur.lastrowid

    def add_grp(cs_id, teacher, group=1, cabinet=None):
        cab_id = cabinet_ids.get(cabinet) if cabinet else None
        cur.execute(
            "INSERT INTO subject_groups (class_subject_id, group_number, teacher_id, cabinet_id) "
            "VALUES (?, ?, ?, ?)",
            (cs_id, group, teacher_ids[teacher], cab_id),
        )

    def add_split_class_subj(class_id, subj, hours, teacher1, teacher2, cab1=None, cab2=None):
        cs = add_cs(class_id, subj, hours, split=1)
        add_grp(cs, teacher1, group=1, cabinet=cab1)
        add_grp(cs, teacher2, group=2, cabinet=cab2)

    # --- КЛАССЫ I СМЕНЫ ---

    # 2 "А"
    c = add_class(2, "А", shift1)
    add_grp(add_cs(c, "Математика", 5), "Петрова Анна Михайловна", cabinet="101")
    add_grp(add_cs(c, "Русский язык", 5), "Морозова Татьяна Петровна", cabinet="101")
    add_grp(add_cs(c, "Литературное чтение", 3), "Козлова Ирина Николаевна")
    add_grp(add_cs(c, "Окружающий мир", 2), "Белова Елена Александровна")
    add_grp(add_cs(c, "Физическая культура и здоровье", 2), "Степанова Мария Константиновна", cabinet="Спортзал")
    add_grp(add_cs(c, "Музыка", 1), "Петренко Алла Максимовна", cabinet="Каб. музыки")
    add_grp(add_cs(c, "Изобразительное искусство", 1), "Петренко Алла Максимовна", cabinet="Каб. ИЗО")

    # 2 "Б"
    c = add_class(2, "Б", shift1)
    add_grp(add_cs(c, "Математика", 5), "Козлова Ирина Николаевна", cabinet="102")
    add_grp(add_cs(c, "Русский язык", 5), "Новикова Ольга Сергеевна", cabinet="102")
    add_grp(add_cs(c, "Литературное чтение", 3), "Белова Елена Александровна")
    add_grp(add_cs(c, "Окружающий мир", 2), "Морозова Татьяна Петровна")
    add_grp(add_cs(c, "Физическая культура и здоровье", 2), "Степанова Мария Константиновна", cabinet="Спортзал")
    add_grp(add_cs(c, "Музыка", 1), "Петренко Алла Максимовна", cabinet="Каб. музыки")
    add_grp(add_cs(c, "Изобразительное искусство", 1), "Петренко Алла Максимовна", cabinet="Каб. ИЗО")

    # 3 "А"
    c = add_class(3, "А", shift1)
    add_grp(add_cs(c, "Математика", 5), "Петрова Анна Михайловна", cabinet="201")
    add_grp(add_cs(c, "Русский язык", 5), "Морозова Татьяна Петровна", cabinet="201")
    add_grp(add_cs(c, "Литературное чтение", 2), "Новикова Ольга Сергеевна")
    add_grp(add_cs(c, "Окружающий мир", 2), "Белова Елена Александровна")
    add_split_class_subj(c, "Иностранный язык (английский)", 3,
                         "Захарова Наталья Викторовна", "Соколова Виктория Львовна")
    add_grp(add_cs(c, "Физическая культура и здоровье", 2), "Степанова Мария Константиновна", cabinet="Спортзал")
    add_grp(add_cs(c, "Музыка", 1), "Петренко Алла Максимовна", cabinet="Каб. музыки")
    add_grp(add_cs(c, "Технология (девочки)", 1), "Давыдова Екатерина Олеговна", cabinet="Мастерская")

    # 4 "А"
    c = add_class(4, "А", shift1)
    add_grp(add_cs(c, "Математика", 5), "Козлова Ирина Николаевна", cabinet="202")
    add_grp(add_cs(c, "Русский язык", 5), "Новикова Ольга Сергеевна", cabinet="202")
    add_grp(add_cs(c, "Литературное чтение", 2), "Морозова Татьяна Петровна")
    add_grp(add_cs(c, "Окружающий мир", 2), "Белова Елена Александровна")
    add_split_class_subj(c, "Иностранный язык (английский)", 3,
                         "Захарова Наталья Викторовна", "Соколова Виктория Львовна")
    add_grp(add_cs(c, "Физическая культура и здоровье", 2), "Степанова Мария Константиновна", cabinet="Спортзал")
    add_grp(add_cs(c, "Музыка", 1), "Петренко Алла Максимовна", cabinet="Каб. музыки")
    add_grp(add_cs(c, "Технология (мальчики)", 1), "Давыдова Екатерина Олеговна", cabinet="Мастерская")

    # 5 "А"
    c = add_class(5, "А", shift1)
    add_grp(add_cs(c, "Математика", 5), "Петрова Анна Михайловна", cabinet="103")
    add_grp(add_cs(c, "Русский язык", 4), "Морозова Татьяна Петровна", cabinet="103")
    add_grp(add_cs(c, "Белорусский язык", 2), "Орлова Марина Дмитриевна")
    add_split_class_subj(c, "Иностранный язык (английский)", 3,
                         "Захарова Наталья Викторовна", "Соколова Виктория Львовна")
    add_grp(add_cs(c, "История Беларуси", 2), "Кузнецов Дмитрий Андреевич", cabinet="104")
    add_grp(add_cs(c, "География", 1), "Кузнецов Дмитрий Андреевич")
    add_grp(add_cs(c, "Биология", 2), "Павлов Алексей Иванович", cabinet="104")
    add_grp(add_cs(c, "Физическая культура и здоровье", 2), "Степанова Мария Константиновна", cabinet="Спортзал")
    add_grp(add_cs(c, "Музыка", 1), "Петренко Алла Максимовна", cabinet="Каб. музыки")
    add_grp(add_cs(c, "Изобразительное искусство", 1), "Петренко Алла Максимовна", cabinet="Каб. ИЗО")
    add_grp(add_cs(c, "Технология (мальчики)", 1), "Давыдова Екатерина Олеговна", cabinet="Мастерская")

    # 5 "Б"
    c = add_class(5, "Б", shift1)
    add_grp(add_cs(c, "Математика", 5), "Козлова Ирина Николаевна", cabinet="104")
    add_grp(add_cs(c, "Русский язык", 4), "Новикова Ольга Сергеевна", cabinet="104")
    add_grp(add_cs(c, "Белорусский язык", 2), "Орлова Марина Дмитриевна")
    add_split_class_subj(c, "Иностранный язык (английский)", 3,
                         "Захарова Наталья Викторовна", "Фёдорова Светлана Юрьевна")
    add_grp(add_cs(c, "История Беларуси", 2), "Кузнецов Дмитрий Андреевич")
    add_grp(add_cs(c, "География", 1), "Павлов Алексей Иванович")
    add_grp(add_cs(c, "Биология", 2), "Белова Елена Александровна")
    add_grp(add_cs(c, "Физическая культура и здоровье", 2), "Степанова Мария Константиновна", cabinet="Спортзал")
    add_grp(add_cs(c, "Информатика", 2), "Волков Игорь Романович", cabinet="Каб. информатики")
    add_grp(add_cs(c, "Технология (девочки)", 1), "Давыдова Екатерина Олеговна", cabinet="Мастерская")

    # --- КЛАССЫ II СМЕНЫ ---

    # 7 "А"
    c = add_class(7, "А", shift2)
    add_grp(add_cs(c, "Математика", 5), "Лебедев Павел Сергеевич", cabinet="203")
    add_grp(add_cs(c, "Русский язык", 4), "Кравченко Оксана Владимировна", cabinet="203")
    add_grp(add_cs(c, "Белорусский язык", 3), "Романова Галина Степановна")
    add_split_class_subj(c, "Английский язык (углублённый)", 3,
                         "Григорьева Людмила Павловна", "Васильева Тамара Ивановна")
    add_grp(add_cs(c, "Всемирная история", 2), "Егоров Николай Петрович", cabinet="204")
    add_grp(add_cs(c, "История Беларуси", 2), "Егоров Николай Петрович")
    add_grp(add_cs(c, "География", 2), "Семёнов Андрей Николаевич")
    add_grp(add_cs(c, "Биология", 2), "Тихонов Владимир Алексеевич")
    add_grp(add_cs(c, "Информатика", 2), "Волков Игорь Романович", cabinet="Каб. информатики")
    add_grp(add_cs(c, "Физическая культура и здоровье", 2), "Жуков Виктор Николаевич", cabinet="Спортзал")

    # 8 "А"
    c = add_class(8, "А", shift2)
    add_grp(add_cs(c, "Математика", 5), "Лебедев Павел Сергеевич")
    add_grp(add_cs(c, "Русский язык", 4), "Кравченко Оксана Владимировна")
    add_grp(add_cs(c, "Белорусский язык", 3), "Романова Галина Степановна")
    add_split_class_subj(c, "Английский язык (углублённый)", 3,
                         "Григорьева Людмила Павловна", "Васильева Тамара Ивановна")
    add_grp(add_cs(c, "Всемирная история", 2), "Егоров Николай Петрович")
    add_grp(add_cs(c, "История Беларуси", 2), "Семёнов Андрей Николаевич")
    add_grp(add_cs(c, "Физика", 3), "Тихонов Владимир Алексеевич", cabinet="Каб. физики")
    add_grp(add_cs(c, "Химия", 2), "Григорьева Людмила Павловна", cabinet="Каб. химии")
    add_grp(add_cs(c, "Биология", 2), "Васильева Тамара Ивановна")
    add_grp(add_cs(c, "Информатика", 2), "Волков Игорь Романович", cabinet="Каб. информатики")
    add_grp(add_cs(c, "Физическая культура и здоровье", 2), "Жуков Виктор Николаевич", cabinet="Спортзал")

    # 9 "А"
    c = add_class(9, "А", shift2)
    add_grp(add_cs(c, "Математика", 5), "Лебедев Павел Сергеевич", cabinet="301")
    add_grp(add_cs(c, "Русский язык", 4), "Кравченко Оксана Владимировна", cabinet="301")
    add_grp(add_cs(c, "Белорусский язык", 3), "Романова Галина Степановна")
    add_split_class_subj(c, "Английский язык (углублённый)", 3,
                         "Григорьева Людмила Павловна", "Васильева Тамара Ивановна")
    add_grp(add_cs(c, "Всемирная история", 3), "Егоров Николай Петрович")
    add_grp(add_cs(c, "История Беларуси", 2), "Семёнов Андрей Николаевич")
    add_grp(add_cs(c, "Физика", 3), "Тихонов Владимир Алексеевич", cabinet="Каб. физики")
    add_grp(add_cs(c, "Химия", 2), "Григорьева Людмила Павловна", cabinet="Каб. химии")
    add_grp(add_cs(c, "Биология", 2), "Васильева Тамара Ивановна")
    add_grp(add_cs(c, "География", 2), "Семёнов Андрей Николаевич")
    add_grp(add_cs(c, "Информатика", 2), "Волков Игорь Романович", cabinet="Каб. информатики")
    add_grp(add_cs(c, "Физическая культура и здоровье", 2), "Жуков Виктор Николаевич", cabinet="Спортзал")
    add_grp(add_cs(c, "Обществоведение", 1), "Егоров Николай Петрович")

    # 11 "А"
    c = add_class(11, "А", shift2)
    add_grp(add_cs(c, "Математика", 5), "Лебедев Павел Сергеевич", cabinet="302")
    add_grp(add_cs(c, "Русский язык", 4), "Кравченко Оксана Владимировна", cabinet="302")
    add_grp(add_cs(c, "Белорусский язык", 3), "Романова Галина Степановна")
    add_split_class_subj(c, "Английский язык (углублённый)", 3,
                         "Григорьева Людмила Павловна", "Васильева Тамара Ивановна")
    add_grp(add_cs(c, "Всемирная история", 3), "Егоров Николай Петрович")
    add_grp(add_cs(c, "История Беларуси", 2), "Семёнов Андрей Николаевич")
    add_grp(add_cs(c, "Физика", 3), "Тихонов Владимир Алексеевич", cabinet="Каб. физики")
    add_grp(add_cs(c, "Химия", 2), "Григорьева Людмила Павловна", cabinet="Каб. химии")
    add_grp(add_cs(c, "Биология", 2), "Васильева Тамара Ивановна")
    add_grp(add_cs(c, "География", 2), "Семёнов Андрей Николаевич")
    add_grp(add_cs(c, "Информатика", 2), "Волков Игорь Романович", cabinet="Каб. информатики")
    add_grp(add_cs(c, "Физическая культура и здоровье", 2), "Жуков Виктор Николаевич", cabinet="Спортзал")
    add_grp(add_cs(c, "Обществоведение", 2), "Егоров Николай Петрович")

    conn.commit()
    return year_id


def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        conn.executescript(f.read())
    print(f"Схема применена: {DB_PATH}")

    year_id = create_school(conn)
    print(f"Школа заполнена (academic_year_id={year_id})")

    cur = conn.execute("SELECT COUNT(*) FROM subject_groups")
    n_groups = cur.fetchone()[0]
    cur = conn.execute("SELECT COUNT(*) FROM classes")
    n_classes = cur.fetchone()[0]
    cur = conn.execute("SELECT COUNT(*) FROM teachers")
    n_teachers = cur.fetchone()[0]
    cur = conn.execute("SELECT COUNT(*) FROM cabinets")
    n_cabinets = cur.fetchone()[0]
    print(f"  Классов: {n_classes}  |  Подгрупп: {n_groups}  |  Учителей: {n_teachers}  |  Кабинетов: {n_cabinets}")

    print("\nЗапуск генерации расписания...")
    from app.services.db_context_builder import build_context_from_db, save_chromosome_to_db
    from app.services.reference_scheduler import GAParams, run_genetic_algorithm

    ctx = build_context_from_db(conn, year_id)
    print(f"  Контекст: {len(ctx.groups)} подгрупп, {len(ctx.lesson_instances)} уроков/неделю")

    params = GAParams(population_size=120, max_generations=500, mutation_rate=0.1)

    def on_progress(gen, fitness, hard):
        if gen % 100 == 0:
            print(f"    шаг {gen:4d}  ошибок: {hard:3d}  качество: {fitness:.0f}")

    result = run_genetic_algorithm(ctx, params, on_progress)
    print(f"\n  Итог: ошибок={result.best_fitness.hard_conflicts}  "
          f"замечаний={result.best_fitness.soft_penalty:.0f}")

    save_chromosome_to_db(conn, ctx, result.best)
    n_entries = conn.execute("SELECT COUNT(*) FROM timetable_entries").fetchone()[0]
    print(f"  Записей в timetable_entries: {n_entries}")

    conn.close()
    print(f"\nГотово: {os.path.abspath(DB_PATH)}")
    print(f"Запуск: python -m app.main")
    print(f"  (или запустите приложение и откройте school_test.sqlite3)")


if __name__ == "__main__":
    main()
