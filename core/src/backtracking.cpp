#include "backtracking.hpp"
#include <random>
#include <algorithm>

namespace scheduler {

Chromosome refine_with_backtracking(
    const Chromosome& chromosome,
    const ScheduleContext& ctx,
    const BacktrackParams& params
) {
    Chromosome current = chromosome;
    FitnessResult current_fitness = evaluate(current, ctx);
    if (current_fitness.hard_conflicts == 0) return current;

    std::mt19937 rng(1234);

    for (int iter = 0; iter < params.max_iterations && current_fitness.hard_conflicts > 0; ++iter) {
        if (current_fitness.conflicting_gene_indices.empty()) break;

        // Берём один из конфликтующих генов и пробуем все допустимые слоты для него,
        // оставляя остальные гены на месте (точечный перебор, а не полный ГА-поиск).
        std::uniform_int_distribution<size_t> pick(0, current_fitness.conflicting_gene_indices.size() - 1);
        int gene_idx = current_fitness.conflicting_gene_indices[pick(rng)];

        const auto& g = ctx.groups[ctx.lesson_instances[gene_idx].group_index];
        int limit = ctx.max_lessons_for_grade(g.grade);

        Gene original = current[gene_idx];
        Gene best_alt = original;
        FitnessResult best_alt_fitness = current_fitness;

        for (int day = 1; day <= ctx.days_per_week; ++day) {
            for (int lesson = 1; lesson <= limit; ++lesson) {
                if (day == original.day && lesson == original.lesson_number) continue;
                current[gene_idx] = Gene{day, lesson};
                FitnessResult candidate = evaluate(current, ctx);
                if (candidate.total() < best_alt_fitness.total()) {
                    best_alt = current[gene_idx];
                    best_alt_fitness = candidate;
                }
            }
        }

        current[gene_idx] = best_alt;
        current_fitness = best_alt_fitness;
    }

    return current;
}

} // namespace scheduler
