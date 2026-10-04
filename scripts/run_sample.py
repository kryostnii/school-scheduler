"""
Демонстрационный запуск reference-планировщика на тестовой школе.
Та же тестовая школа, что и в core/tests/smoke_test.cpp — удобно сверять
поведение Python-реализации и C++-ядра на одинаковых входных данных.

Запуск: python3 scripts/run_sample.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.reference_scheduler import (
    ScheduleContext, SubjectGroupInfo, GAParams, run_genetic_algorithm, evaluate,
)
import random


def build_sample_context() -> ScheduleContext:
    ctx = ScheduleContext(days_per_week=6)
    next_id = [1]

    def add_group(class_id, grade, teacher_id, hours, is_pe=False, is_heavy=False):
        gid = next_id[0]
        next_id[0] += 1
        ctx.groups.append(SubjectGroupInfo(
            id=gid, class_id=class_id, grade=grade, teacher_id=teacher_id,
            hours_per_week=hours, is_physical_education=is_pe, is_heavy_subject=is_heavy,
        ))

    # Класс 101 (5 класс)
    add_group(101, 5, 1, 5, is_heavy=True)   # математика
    add_group(101, 5, 2, 4, is_heavy=True)   # русский язык
    add_group(101, 5, 3, 2, is_pe=True)      # физкультура
    add_group(101, 5, 4, 3)                  # история
    add_group(101, 5, 5, 2)                  # биология

    # Класс 102 (5 класс) — частично те же учителя
    add_group(102, 5, 1, 5, is_heavy=True)
    add_group(102, 5, 6, 4, is_heavy=True)
    add_group(102, 5, 3, 2, is_pe=True)
    add_group(102, 5, 7, 3)
    add_group(102, 5, 8, 2)

    # Класс 201 (2 класс) — проверка лимита уроков/день
    add_group(201, 2, 9, 5, is_heavy=True)
    add_group(201, 2, 10, 4)
    add_group(201, 2, 11, 2, is_pe=True)
    add_group(201, 2, 12, 3)

    ctx.build_lesson_instances()
    return ctx


def print_schedule_grid(ctx, chromosome, class_id):
    """Печатает сетку день x урок для одного класса — удобно для визуальной отладки."""
    grid = {}
    max_lesson = 0
    for i, li in enumerate(ctx.lesson_instances):
        g = ctx.groups[li.group_index]
        if g.class_id != class_id:
            continue
        gene = chromosome[i]
        grid[(gene.day, gene.lesson_number)] = g
        max_lesson = max(max_lesson, gene.lesson_number)

    days = list(range(1, ctx.days_per_week + 1))
    day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб"]
    print(f"\nРасписание класса {class_id}:")
    header = "Урок | " + " | ".join(f"{day_names[d-1]:^12}" for d in days)
    print(header)
    print("-" * len(header))
    for lesson in range(1, max_lesson + 1):
        row = [f"{lesson:^4}"]
        for d in days:
            g = grid.get((d, lesson))
            if g:
                label = f"пр.{g.id}"
                if g.is_physical_education:
                    label = "физра"
                row.append(f"{label:^12}")
            else:
                row.append(f"{'—':^12}")
        print(" | ".join(row))


def main():
    ctx = build_sample_context()
    print(f"Тестовая школа: {len(ctx.groups)} подгрупп, "
          f"{len(ctx.lesson_instances)} уроков-часов в неделю")

    rng = random.Random(1)
    random_chromosome = []
    for li in ctx.lesson_instances:
        g = ctx.groups[li.group_index]
        limit = ctx.max_lessons_for_grade(g.grade)
        from app.services.reference_scheduler import Gene
        random_chromosome.append(Gene(rng.randint(1, ctx.days_per_week), rng.randint(1, limit)))
    baseline = evaluate(random_chromosome, ctx)
    print(f"Случайное расписание:  hard_conflicts={baseline.hard_conflicts}  "
          f"soft_penalty={baseline.soft_penalty:.1f}  total={baseline.total():.1f}")

    params = GAParams(population_size=60, max_generations=300, mutation_rate=0.1)

    print("\nЗапуск генетического алгоритма (Python reference)...")
    last_printed = [-1]

    def on_progress(gen, fitness, hard):
        if gen % 50 == 0 or (hard == 0 and last_printed[0] != 0):
            print(f"  поколение {gen:4d}  hard_conflicts={hard:3d}  fitness={fitness:.1f}")
        last_printed[0] = hard

    result = run_genetic_algorithm(ctx, params, on_progress)

    print(f"\nИтог после {result.generations_run} поколений + бэктрекинга:")
    print(f"  hard_conflicts={result.best_fitness.hard_conflicts}  "
          f"soft_penalty={result.best_fitness.soft_penalty:.1f}  "
          f"total={result.best_fitness.total():.1f}")

    if result.best_fitness.hard_conflicts == 0:
        print("\n✓ Допустимое расписание найдено (все hard-ограничения соблюдены).")
    else:
        print("\n✗ Остались hard-конфликты — увеличьте max_generations/population_size.")

    print_schedule_grid(ctx, result.best, class_id=101)
    print_schedule_grid(ctx, result.best, class_id=201)


if __name__ == "__main__":
    main()
