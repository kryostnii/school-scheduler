"""
Reference-реализация алгоритма генерации расписания на чистом Python
(без внешних зависимостей — только стандартная библиотека).

Назначение:
  1. Работающий end-to-end пример для отладки логики (hard/soft ограничения
     раздела 4 ТЗ) без необходимости собирать C++ ядро с pybind11.
  2. Эталон для сверки результатов C++-ядра (core/) при его дальнейшей доводке —
     обе реализации используют одинаковую модель данных и одинаковые формулы
     штрафов, поэтому на одном и том же наборе данных должны давать
     сопоставимые по качеству (не обязательно идентичные) расписания.

Как только core/ будет собран с pybind11 (см. README проекта), эта реализация
может быть заменена вызовом `scheduler_core.run_genetic_algorithm(...)`
без изменения остального Python-кода — сигнатуры специально сделаны похожими.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable, Optional


# ---------------------------------------------------------------------------
# Модель данных (зеркалит core/include/model.hpp)
# ---------------------------------------------------------------------------

@dataclass
class SubjectGroupInfo:
    id: int
    class_id: int
    grade: int
    teacher_id: int
    hours_per_week: int
    cabinet_id: Optional[int] = None
    shift: int = 1
    is_physical_education: bool = False
    is_heavy_subject: bool = False
    allows_double_lesson: bool = False


@dataclass
class LessonInstance:
    subject_group_id: int
    group_index: int
    occurrence: int


@dataclass
class Gene:
    day: int
    lesson_number: int


Chromosome = list  # список Gene, длина == len(ctx.lesson_instances)


@dataclass
class ScheduleContext:
    groups: list[SubjectGroupInfo] = field(default_factory=list)
    lesson_instances: list[LessonInstance] = field(default_factory=list)
    days_per_week: int = 6

    def max_lessons_for_grade(self, grade: int) -> int:
        # Раздел 4.1 ТЗ
        if grade == 1:
            return 4
        if grade <= 4:
            return 5
        if grade <= 6:
            return 6
        return 7

    def peak_days_for_grade(self, grade: int) -> list[int]:
        # Раздел 4.1 ТЗ: вт/ср (I-IV), вт/ср/пт (V-XI(XII))
        return [2, 3] if grade <= 4 else [2, 3, 5]

    def build_lesson_instances(self) -> None:
        self.lesson_instances = []
        for gi, g in enumerate(self.groups):
            for occ in range(g.hours_per_week):
                self.lesson_instances.append(LessonInstance(g.id, gi, occ))


# ---------------------------------------------------------------------------
# Fitness (зеркалит core/src/fitness.cpp)
# ---------------------------------------------------------------------------

@dataclass
class FitnessResult:
    hard_conflicts: int = 0
    soft_penalty: float = 0.0
    conflicting_gene_indices: list[int] = field(default_factory=list)

    def total(self) -> float:
        return self.hard_conflicts * 1000.0 + self.soft_penalty


def evaluate(chromosome: Chromosome, ctx: ScheduleContext) -> FitnessResult:
    result = FitnessResult()
    conflicting: set[int] = set()

    teacher_slots: dict[tuple[int, int, int], list[int]] = {}
    class_slots: dict[tuple[int, int, int], list[int]] = {}
    cabinet_slots: dict[tuple[int, int, int], list[int]] = {}
    class_day_lessons: dict[tuple[int, int], list[int]] = {}
    teacher_day_lessons: dict[tuple[int, int], list[int]] = {}

    for i, gene in enumerate(chromosome):
        li = ctx.lesson_instances[i]
        g = ctx.groups[li.group_index]
        slot = (gene.day, gene.lesson_number)

        teacher_slots.setdefault((g.teacher_id, *slot), []).append(i)
        class_slots.setdefault((g.class_id, *slot), []).append(i)
        if g.cabinet_id is not None:
            cabinet_slots.setdefault((g.cabinet_id, *slot), []).append(i)
        class_day_lessons.setdefault((g.class_id, gene.day), []).append(i)
        teacher_day_lessons.setdefault((g.teacher_id, gene.day), []).append(i)

    def count_clashes(m: dict) -> None:
        for idxs in m.values():
            if len(idxs) > 1:
                result.hard_conflicts += len(idxs) - 1
                conflicting.update(idxs)

    count_clashes(teacher_slots)
    count_clashes(class_slots)
    count_clashes(cabinet_slots)

    # Лимит уроков/день по параллели
    for (class_id, day), idxs in class_day_lessons.items():
        grade = ctx.groups[ctx.lesson_instances[idxs[0]].group_index].grade
        limit = ctx.max_lessons_for_grade(grade)
        if len(idxs) > limit:
            result.hard_conflicts += len(idxs) - limit
            conflicting.update(idxs)

    # Физкультура не два дня подряд
    class_pe_days: dict[int, set[int]] = {}
    for (class_id, day), idxs in class_day_lessons.items():
        for idx in idxs:
            g = ctx.groups[ctx.lesson_instances[idx].group_index]
            if g.is_physical_education:
                class_pe_days.setdefault(class_id, set()).add(day)
    for class_id, days in class_pe_days.items():
        for d in days:
            if (d + 1) in days:
                result.hard_conflicts += 1
                for dd in (d, d + 1):
                    for idx in class_day_lessons.get((class_id, dd), []):
                        g = ctx.groups[ctx.lesson_instances[idx].group_index]
                        if g.is_physical_education:
                            conflicting.add(idx)

    # Окна (soft)
    def count_windows(m: dict) -> int:
        windows = 0
        for idxs in m.values():
            lessons = sorted({chromosome[i].lesson_number for i in idxs})
            for k in range(1, len(lessons)):
                gap = lessons[k] - lessons[k - 1] - 1
                if gap > 0:
                    windows += gap
        return windows

    result.soft_penalty += count_windows(class_day_lessons) * 3.0
    result.soft_penalty += count_windows(teacher_day_lessons) * 1.0

    # Тяжёлые предметы не первым/последним уроком (soft)
    for i, gene in enumerate(chromosome):
        g = ctx.groups[ctx.lesson_instances[i].group_index]
        if g.is_heavy_subject:
            limit = ctx.max_lessons_for_grade(g.grade)
            if gene.lesson_number in (1, limit):
                result.soft_penalty += 2.0

    # Пик нагрузки на дни наибольшей работоспособности (soft)
    classes_seen = {ctx.groups[li.group_index].class_id for li in ctx.lesson_instances}
    for class_id in classes_seen:
        days_for_class = {d for (cid, d) in class_day_lessons if cid == class_id}
        if not days_for_class:
            continue
        sample_idx = class_day_lessons[(class_id, next(iter(days_for_class)))][0]
        grade = ctx.groups[ctx.lesson_instances[sample_idx].group_index].grade
        peak = set(ctx.peak_days_for_grade(grade))

        peak_counts = [len(class_day_lessons[(class_id, d)]) for d in days_for_class if d in peak]
        other_counts = [len(class_day_lessons[(class_id, d)]) for d in days_for_class if d not in peak]
        peak_avg = sum(peak_counts) / len(peak_counts) if peak_counts else 0
        other_avg = sum(other_counts) / len(other_counts) if other_counts else 0
        if other_avg > peak_avg:
            result.soft_penalty += (other_avg - peak_avg) * 1.5

    result.conflicting_gene_indices = sorted(conflicting)
    return result


# ---------------------------------------------------------------------------
# Генетический алгоритм (зеркалит core/src/genetic_algorithm.cpp)
# ---------------------------------------------------------------------------

@dataclass
class GAParams:
    population_size: int = 60
    max_generations: int = 300
    mutation_rate: float = 0.1
    crossover_rate: float = 0.8
    tournament_size: int = 3
    random_seed: int = 42
    refine_with_backtracking_after: bool = True


@dataclass
class GAResult:
    best: Chromosome
    best_fitness: FitnessResult
    generations_run: int = 0


def _random_chromosome(ctx: ScheduleContext, rng: random.Random) -> Chromosome:
    c = []
    for li in ctx.lesson_instances:
        g = ctx.groups[li.group_index]
        limit = ctx.max_lessons_for_grade(g.grade)
        c.append(Gene(rng.randint(1, ctx.days_per_week), rng.randint(1, limit)))
    return c


def _tournament(fitnesses: list[float], size: int, rng: random.Random) -> int:
    best = rng.randrange(len(fitnesses))
    for _ in range(size - 1):
        challenger = rng.randrange(len(fitnesses))
        if fitnesses[challenger] < fitnesses[best]:
            best = challenger
    return best


def _crossover(a: Chromosome, b: Chromosome, rng: random.Random) -> Chromosome:
    if not a:
        return []
    point = rng.randrange(len(a))
    return [a[i] if i < point else b[i] for i in range(len(a))]


def _mutate(c: Chromosome, ctx: ScheduleContext, rate: float, rng: random.Random) -> None:
    for i, li in enumerate(ctx.lesson_instances):
        if rng.random() < rate:
            g = ctx.groups[li.group_index]
            limit = ctx.max_lessons_for_grade(g.grade)
            c[i] = Gene(rng.randint(1, ctx.days_per_week), rng.randint(1, limit))


def run_genetic_algorithm(
    ctx: ScheduleContext,
    params: GAParams = GAParams(),
    on_progress: Optional[Callable[[int, float, int], None]] = None,
) -> GAResult:
    rng = random.Random(params.random_seed)
    population = [_random_chromosome(ctx, rng) for _ in range(params.population_size)]

    best: Optional[Chromosome] = None
    best_fitness: Optional[FitnessResult] = None
    generations_run = 0

    for gen in range(params.max_generations):
        fits = [evaluate(ind, ctx) for ind in population]
        totals = [f.total() for f in fits]

        best_idx = min(range(len(totals)), key=lambda i: totals[i])
        if best_fitness is None or fits[best_idx].total() < best_fitness.total():
            best = population[best_idx]
            best_fitness = fits[best_idx]

        generations_run = gen + 1
        if on_progress:
            on_progress(gen + 1, best_fitness.total(), best_fitness.hard_conflicts)

        next_gen = [best]
        while len(next_gen) < params.population_size:
            pa = _tournament(totals, params.tournament_size, rng)
            pb = _tournament(totals, params.tournament_size, rng)
            child = (_crossover(population[pa], population[pb], rng)
                     if rng.random() < params.crossover_rate else list(population[pa]))
            _mutate(child, ctx, params.mutation_rate, rng)
            next_gen.append(child)
        population = next_gen

    if params.refine_with_backtracking_after and best_fitness.hard_conflicts > 0:
        refined = refine_with_backtracking(best, ctx)
        refined_fitness = evaluate(refined, ctx)
        if refined_fitness.total() < best_fitness.total():
            best, best_fitness = refined, refined_fitness

    return GAResult(best=best, best_fitness=best_fitness, generations_run=generations_run)


# ---------------------------------------------------------------------------
# Бэктрекинг (зеркалит core/src/backtracking.cpp)
# ---------------------------------------------------------------------------

def refine_with_backtracking(
    chromosome: Chromosome, ctx: ScheduleContext, max_iterations: int = 2000
) -> Chromosome:
    current = list(chromosome)
    current_fitness = evaluate(current, ctx)
    if current_fitness.hard_conflicts == 0:
        return current

    rng = random.Random(1234)

    for _ in range(max_iterations):
        if current_fitness.hard_conflicts == 0 or not current_fitness.conflicting_gene_indices:
            break

        gene_idx = rng.choice(current_fitness.conflicting_gene_indices)
        g = ctx.groups[ctx.lesson_instances[gene_idx].group_index]
        limit = ctx.max_lessons_for_grade(g.grade)

        original = current[gene_idx]
        best_alt = original
        best_alt_fitness = current_fitness

        for day in range(1, ctx.days_per_week + 1):
            for lesson in range(1, limit + 1):
                if day == original.day and lesson == original.lesson_number:
                    continue
                current[gene_idx] = Gene(day, lesson)
                candidate = evaluate(current, ctx)
                if candidate.total() < best_alt_fitness.total():
                    best_alt = current[gene_idx]
                    best_alt_fitness = candidate

        current[gene_idx] = best_alt
        current_fitness = best_alt_fitness

    return current
