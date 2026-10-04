#include "genetic_algorithm.hpp"
#include "backtracking.hpp"
#include <random>
#include <algorithm>
#include <vector>

namespace scheduler {

namespace {

Chromosome random_chromosome(const ScheduleContext& ctx, std::mt19937& rng) {
    Chromosome c(ctx.lesson_instances.size());
    std::uniform_int_distribution<int> day_dist(1, ctx.days_per_week);
    for (size_t i = 0; i < c.size(); ++i) {
        const auto& g = ctx.groups[ctx.lesson_instances[i].group_index];
        int limit = ctx.max_lessons_for_grade(g.grade);
        std::uniform_int_distribution<int> lesson_dist(1, limit);
        c[i] = Gene{day_dist(rng), lesson_dist(rng)};
    }
    return c;
}

int tournament_select(const std::vector<double>& fitnesses, int size, std::mt19937& rng) {
    std::uniform_int_distribution<int> idx_dist(0, static_cast<int>(fitnesses.size()) - 1);
    int best = idx_dist(rng);
    for (int i = 1; i < size; ++i) {
        int challenger = idx_dist(rng);
        if (fitnesses[challenger] < fitnesses[best]) best = challenger;
    }
    return best;
}

Chromosome crossover(const Chromosome& a, const Chromosome& b, std::mt19937& rng) {
    if (a.empty()) return a;
    std::uniform_int_distribution<size_t> point_dist(0, a.size() - 1);
    size_t point = point_dist(rng);
    Chromosome child(a.size());
    for (size_t i = 0; i < a.size(); ++i) child[i] = (i < point) ? a[i] : b[i];
    return child;
}

void mutate(Chromosome& c, const ScheduleContext& ctx, double rate, std::mt19937& rng) {
    std::uniform_real_distribution<double> prob(0.0, 1.0);
    std::uniform_int_distribution<int> day_dist(1, ctx.days_per_week);
    for (size_t i = 0; i < c.size(); ++i) {
        if (prob(rng) < rate) {
            const auto& g = ctx.groups[ctx.lesson_instances[i].group_index];
            int limit = ctx.max_lessons_for_grade(g.grade);
            std::uniform_int_distribution<int> lesson_dist(1, limit);
            c[i] = Gene{day_dist(rng), lesson_dist(rng)};
        }
    }
}

} // namespace

GAResult run_genetic_algorithm(
    const ScheduleContext& ctx,
    const GAParams& params,
    ProgressCallback on_progress
) {
    std::mt19937 rng(params.random_seed);

    std::vector<Chromosome> population;
    population.reserve(params.population_size);
    for (int i = 0; i < params.population_size; ++i) {
        population.push_back(random_chromosome(ctx, rng));
    }

    GAResult result;
    result.best_fitness.hard_conflicts = -1; // ещё не оценивали

    for (int gen = 0; gen < params.max_generations; ++gen) {
        std::vector<FitnessResult> fits(population.size());
        std::vector<double> totals(population.size());
        for (size_t i = 0; i < population.size(); ++i) {
            fits[i] = evaluate(population[i], ctx);
            totals[i] = fits[i].total();
        }

        // Отслеживаем лучшую особь за всё время (элитизм между поколениями).
        auto best_it = std::min_element(totals.begin(), totals.end());
        size_t best_idx = std::distance(totals.begin(), best_it);
        if (result.best_fitness.hard_conflicts == -1 ||
            fits[best_idx].total() < result.best_fitness.total()) {
            result.best = population[best_idx];
            result.best_fitness = fits[best_idx];
        }

        result.generations_run = gen + 1;
        if (on_progress) {
            on_progress(gen + 1, result.best_fitness.total(), result.best_fitness.hard_conflicts);
        }

        if (result.best_fitness.hard_conflicts == 0 && gen > 10) {
            // Жёстких конфликтов нет — дальше можно полировать soft-штрафы,
            // но для MVP останавливаемся раньше, если конфликтов давно нет.
        }

        // Новое поколение: элита + турнирный отбор + кроссовер + мутация.
        std::vector<Chromosome> next_gen;
        next_gen.reserve(population.size());
        next_gen.push_back(result.best); // элитизм: лучший всегда выживает

        std::uniform_real_distribution<double> prob(0.0, 1.0);
        while (next_gen.size() < population.size()) {
            int pa = tournament_select(totals, params.tournament_size, rng);
            int pb = tournament_select(totals, params.tournament_size, rng);
            Chromosome child = (prob(rng) < params.crossover_rate)
                ? crossover(population[pa], population[pb], rng)
                : population[pa];
            mutate(child, ctx, params.mutation_rate, rng);
            next_gen.push_back(std::move(child));
        }
        population = std::move(next_gen);
    }

    if (params.refine_with_backtracking_after && result.best_fitness.hard_conflicts > 0) {
        BacktrackParams bp;
        Chromosome refined = refine_with_backtracking(result.best, ctx, bp);
        FitnessResult refined_fitness = evaluate(refined, ctx);
        if (refined_fitness.total() < result.best_fitness.total()) {
            result.best = refined;
            result.best_fitness = refined_fitness;
        }
    }

    return result;
}

} // namespace scheduler
