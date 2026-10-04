"""
Полный цикл: SQLite-файл по db/schema.sql -> тестовые данные ->
ScheduleContext -> генерация -> запись результата обратно в БД ->
чтение и печать готового расписания из БД (а не из памяти) —
то есть по-настоящему сквозная проверка, а не изолированный тест алгоритма.

Запуск: python3 scripts/run_from_db.py [путь_к_файлу.sqlite3]
"""
import sys
import os
import sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.seed_sample_school import seed
from app.services.db_context_builder import build_context_from_db, save_chromosome_to_db
from app.services.reference_scheduler import GAParams, run_genetic_algorithm


def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else "school.sqlite3"
    if os.path.exists(db_path):
        os.remove(db_path)  # чистый запуск для демонстрации

    schema_path = os.path.join(os.path.dirname(__file__), "..", "db", "schema.sql")
    conn = sqlite3.connect(db_path)
    with open(schema_path, encoding="utf-8") as f:
        conn.executescript(f.read())

    print(f"БД создана: {db_path}")
    year_id = seed(conn)
    print("Тестовая школа заполнена (4 класса, 2 смены, деление на подгруппы по языку)")

    ctx = build_context_from_db(conn, year_id)
    print(f"Контекст собран из БД: {len(ctx.groups)} подгрупп, "
          f"{len(ctx.lesson_instances)} уроков-часов в неделю")

    params = GAParams(population_size=80, max_generations=400, mutation_rate=0.1)
    print("\nЗапуск генерации...")

    def on_progress(gen, fitness, hard):
        if gen % 100 == 0:
            print(f"  поколение {gen:4d}  hard_conflicts={hard:3d}  fitness={fitness:.1f}")

    result = run_genetic_algorithm(ctx, params, on_progress)
    print(f"\nИтог: hard_conflicts={result.best_fitness.hard_conflicts}  "
          f"soft_penalty={result.best_fitness.soft_penalty:.1f}")

    save_chromosome_to_db(conn, ctx, result.best)
    print(f"Результат записан в timetable_entries ({db_path})")

    # Читаем расписание ОБРАТНО из БД — проверяем, что персист реально сработал.
    print("\nРасписание, прочитанное из БД (класс 5А, все предметы):")
    rows = conn.execute("""
        SELECT c.grade, c.letter, s.name AS subject, t.full_name AS teacher,
               te.day_of_week, te.lesson_number
        FROM timetable_entries te
        JOIN subject_groups sg ON sg.id = te.subject_group_id
        JOIN class_subjects cs ON cs.id = sg.class_subject_id
        JOIN classes c ON c.id = cs.class_id
        JOIN subjects s ON s.id = cs.subject_id
        JOIN teachers t ON t.id = sg.teacher_id
        WHERE c.grade = 5 AND c.letter = 'А'
        ORDER BY te.day_of_week, te.lesson_number
    """).fetchall()

    day_names = ["", "Пн", "Вт", "Ср", "Чт", "Пт", "Сб"]
    for grade, letter, subject, teacher, day, lesson in rows:
        print(f"  {day_names[day]}, урок {lesson}: {subject} ({teacher})")

    conn.close()
    print(f"\nГотово. Файл БД с результатом: {os.path.abspath(db_path)}")


if __name__ == "__main__":
    main()
