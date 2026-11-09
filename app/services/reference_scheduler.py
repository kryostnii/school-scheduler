"""Reference-реализация алгоритма генерации расписания на чистом Python.

Содержит проверяемый end-to-end пример и эталонную модель для будущего C++-ядра.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable, Optional


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


Chromosome = list


@dataclass
class ScheduleContext:
    groups: list[SubjectGroupInfo] = field(default_factory=list)
    lesson_instances: list[LessonInstance] = field(default_factory=list)
    days_per_week: int = 6

    def max_lessons_for_grade(self, grade: int) -> int:
        if grade == 1:
            return 4
        if grade <= 4:
            return 5
        if grade <= 6:
            return 6
        return 7

    def peak_days_for_grade(self, grade: int) -> list[int]:
        return [2, 3] if grade <= 4 else [2, 3, 5]

    def build_lesson_instances(self) -> None:
        if self.days_per_week < 1:
            raise ValueError("В неделе должен быть хотя бы один учебный день")
        self.lesson_instances = []
        for gi, group in enumerate(self.groups):
            if group.hours_per_week < 0:
                raise ValueError(f"Часы в неделю не могут быть отрицательными (группа {group.id})")
            for occurrence in range(group.hours_per_week):
                self.lesson_instances.append(LessonInstance(group.id, gi, occurrence))


@dataclass
class FitnessResult:
    hard_conflicts: int = 0
    soft_penalty: float = 0.0
    conflicting_gene_indices: list[int] = field(default_factory=list)

    def total(self) -> float:
        return self.hard_conflicts * 1000.0 + self.soft_penalty


def evaluate(chromosome: Chromosome, ctx: ScheduleContext) -> FitnessResult:
    if len(chromosome) != len(ctx.lesson_instances):
        raise ValueError(
            f"Длина расписания ({len(chromosome)}) не совпадает с числом уроков "
            f"({len(ctx.lesson_instances)})"
        )
    result = FitnessResult()
    conflicting: set[int] = set()

    teacher_slots: dict[tuple[int, int, int], list[int]] = {}
    class_slots: dict[tuple[int, int, int], list[int]] = {}
    cabinet_slots: dict[tuple[int, int, int], list[int]] = {}
    class_day_lessons: dict[tuple[int, int], list[int]] = {}
    teacher_day_lessons: dict[tuple[int, int], list[int]] = {}

    for i, gene in enumerate(chromosome):
        li = ctx.lesson_instances[i]
        group = ctx.groups[li.group_index]
        slot = (gene.day, gene.lesson_number)
        teacher_slots.setdefault((group.teacher_id, *slot), []).append(i)
        class_slots.setdefault((group.class_id, *slot), []).append(i)
        if group.cabinet_id is not None:
            cabinet_slots.setdefault((group.cabinet_id, *slot), []).append(i)
        class_day_lessons.setdefault((group.class_id, gene.day), []).append(i)
        teacher_day_lessons.setdefault((group.teacher_id, gene.day), []).append(i)

    def count_clashes(slots: dict) -> None:
        for indices in slots.values():
            if len(indices) > 1:
                result.hard_conflicts += len(indices) - 1
                conflicting.update(indices)

    count_clashes(teacher_slots)
    count_clashes(class_slots)
    count_clashes(cabinet_slots)

    for (class_id, day), indices in class_day_lessons.items():
        grade = ctx.groups[ctx.lesson_instances[indices[0]].group_index].grade
        limit = ctx.max_lessons_for_grade(grade)
        if len(indices) > limit:
            result.hard_conflicts += len(indices) - limit
            conflicting.update(indices)

    class_pe_days: dict[int, set[int]] = {}
    for (class_id, day), indices in class_day_lessons.items():
        for index in indices:
            group = ctx.groups[ctx.lesson_instances[index].group_index]
            if group.is_physical_education:
                class_pe_days.setdefault(class_id, set()).add(day)
    for class_id, days in class_pe_days.items():
        for day in days:
            if day + 1 in days:
                result.hard_conflicts += 1
                for adjacent_day in (day, day + 1):
                    for index in class_day_lessons.get((class_id, adjacent_day), []):
                        group = ctx.groups[ctx.lesson_instances[index].group_index]
                        if group.is_physical_education:
                            conflicting.add(index)

    def count_windows(slots: dict) -> int:
        windows = 0
        for indices in slots.values():
            lessons = sorted({chromosome[i].lesson_number for i in indices})
            for i in range(1, len(lessons)):
                gap = lessons[i] - lessons[i - 1] - 1
                if gap > 0:
                    windows += gap
        return windows

    result.soft_penalty += count_windows(class_day_lessons) * 3.0
    result.soft_penalty += count_windows(teacher_day_lessons)

    for i, gene in enumerate(chromosome):
        group = ctx.groups[ctx.lesson_instances[i].group_index]
        if group.is_heavy_subject and gene.lesson_number in (
            1, ctx.max_lessons_for_grade(group.grade)
        ):
            result.soft_penalty += 2.0

    classes_seen = {ctx.groups[li.group_index].class_id for li in ctx.lesson_instances}
    for class_id in classes_seen:
        days_for_class = {day for cid, day in class_day_lessons if cid == class_id}
        if not days_for_class:
            continue
        sample_index = class_day_lessons[(class_id, next(iter(days_for_class)))][0]
        grade = ctx.groups[ctx.lesson_instances[sample_index].group_index].grade
        peak = set(ctx.peak_days_for_grade(grade))
        peak_counts = [len(class_day_lessons[(class_id, day)]) for day in days_for_class if day in peak]
        other_counts = [len(class_day_lessons[(class_id, day)]) for day in days_for_class if day not in peak]
        peak_avg = sum(peak_counts) / len(peak_counts) if peak_counts else 0
        other_avg = sum(other_counts) / len(other_counts) if other_counts else 0
        if other_avg > peak_avg:
            result.soft_penalty += (other_avg - peak_avg) * 1.5

    result.conflicting_gene_indices = sorted(conflicting)
    return result


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
    chromosome = []
    for instance in ctx.lesson_instances:
        group = ctx.groups[instance.group_index]
        limit = ctx.max_lessons_for_grade(group.grade)
        chromosome.append(Gene(rng.randint(1, ctx.days_per_week), rng.randint(1, limit)))
    return chromosome


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


def _mutate(chromosome: Chromosome, ctx: ScheduleContext, rate: float, rng: random.Random) -> None:
    for i, instance in enumerate(ctx.lesson_instances):
        if rng.random() < rate:
            group = ctx.groups[instance.group_index]
            limit = ctx.max_lessons_for_grade(group.grade)
            chromosome[i] = Gene(rng.randint(1, ctx.days_per_week), rng.randint(1, limit))


def run_genetic_algorithm(
    ctx: ScheduleContext,
    params: GAParams = GAParams(),
    on_progress: Optional[Callable[[int, float, int], None]] = None,
) -> GAResult:
    if params.population_size < 1:
        raise ValueError("Размер популяции должен быть не меньше 1")
    if params.max_generations < 1:
        raise ValueError("Число поколений должно быть не меньше 1")
    if params.tournament_size < 1:
        raise ValueError("Размер турнира должен быть не меньше 1")
    if not 0.0 <= params.mutation_rate <= 1.0:
        raise ValueError("Вероятность мутации должна быть от 0 до 1")
    if not 0.0 <= params.crossover_rate <= 1.0:
        raise ValueError("Вероятность скрещивания должна быть от 0 до 1")
    if not ctx.lesson_instances:
        return GAResult(best=[], best_fitness=evaluate([], ctx), generations_run=0)

    rng = random.Random(params.random_seed)
    population = [_random_chromosome(ctx, rng) for _ in range(params.population_size)]
    best: Optional[Chromosome] = None
    best_fitness: Optional[FitnessResult] = None
    generations_run = 0

    for gen in range(params.max_generations):
        fitnesses = [evaluate(individual, ctx) for individual in population]
        totals = [fitness.total() for fitness in fitnesses]
        best_idx = min(range(len(totals)), key=totals.__getitem__)
        if best_fitness is None or fitnesses[best_idx].total() < best_fitness.total():
            best = list(population[best_idx])
            best_fitness = fitnesses[best_idx]

        generations_run = gen + 1
        if on_progress:
            on_progress(gen + 1, best_fitness.total(), best_fitness.hard_conflicts)

        next_generation = [list(best)]
        while len(next_generation) < params.population_size:
            parent_a = _tournament(totals, params.tournament_size, rng)
            parent_b = _tournament(totals, params.tournament_size, rng)
            child = (
                _crossover(population[parent_a], population[parent_b], rng)
                if rng.random() < params.crossover_rate
                else list(population[parent_a])
            )
            _mutate(child, ctx, params.mutation_rate, rng)
            next_generation.append(child)
        population = next_generation

    if params.refine_with_backtracking_after and best_fitness.hard_conflicts > 0:
        refined = refine_with_backtracking(best, ctx)
        refined_fitness = evaluate(refined, ctx)
        if refined_fitness.total() < best_fitness.total():
            best, best_fitness = refined, refined_fitness

    return GAResult(best=best, best_fitness=best_fitness, generations_run=generations_run)


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
        group = ctx.groups[ctx.lesson_instances[gene_idx].group_index]
        limit = ctx.max_lessons_for_grade(group.grade)
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
