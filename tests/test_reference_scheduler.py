import unittest

from app.services.reference_scheduler import (
    GAParams,
    Gene,
    ScheduleContext,
    SubjectGroupInfo,
    evaluate,
    run_genetic_algorithm,
)


class ReferenceSchedulerTests(unittest.TestCase):
    def make_context(self):
        context = ScheduleContext(days_per_week=5)
        context.groups = [
            SubjectGroupInfo(id=1, class_id=10, grade=5, teacher_id=1, hours_per_week=2),
            SubjectGroupInfo(id=2, class_id=11, grade=5, teacher_id=1, hours_per_week=2),
        ]
        context.build_lesson_instances()
        return context

    def test_evaluate_rejects_mismatched_chromosome(self):
        context = self.make_context()
        with self.assertRaisesRegex(ValueError, "Длина расписания"):
            evaluate([], context)

    def test_empty_context_returns_empty_result(self):
        context = ScheduleContext()
        result = run_genetic_algorithm(context, GAParams())
        self.assertEqual(result.best, [])
        self.assertEqual(result.generations_run, 0)
        self.assertEqual(result.best_fitness.hard_conflicts, 0)

    def test_algorithm_is_reproducible_with_same_seed(self):
        context = self.make_context()
        params = GAParams(
            population_size=12,
            max_generations=20,
            random_seed=7,
            refine_with_backtracking_after=False,
        )
        first = run_genetic_algorithm(context, params)
        second = run_genetic_algorithm(context, params)
        self.assertEqual(
            [(gene.day, gene.lesson_number) for gene in first.best],
            [(gene.day, gene.lesson_number) for gene in second.best],
        )
        self.assertEqual(first.best_fitness.total(), second.best_fitness.total())
        self.assertEqual(len(first.best), len(context.lesson_instances))

    def test_impossible_parameters_are_reported(self):
        with self.assertRaisesRegex(ValueError, "Размер популяции"):
            run_genetic_algorithm(self.make_context(), GAParams(population_size=0))

    def test_valid_chromosome_can_be_evaluated(self):
        context = self.make_context()
        chromosome = [Gene(day=1, lesson_number=i + 1) for i in range(4)]
        result = evaluate(chromosome, context)
        self.assertGreaterEqual(result.hard_conflicts, 0)
        self.assertGreaterEqual(result.soft_penalty, 0)


if __name__ == "__main__":
    unittest.main()
