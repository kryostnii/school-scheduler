#pragma once
#include "model.hpp"
#include "fitness.hpp"
#include <functional>

namespace scheduler {

struct GAParams {
    int population_size = 80;
    int max_generations = 400;
    double mutation_rate = 0.08;
    double crossover_rate = 0.8;
    int tournament_size = 3;
    unsigned int random_seed = 42;
    // Если true — по завершении ГА на лучшую хромосому дополнительно
    // накатывается бэктрекинг для точечной доводки (раздел 3 ТЗ).
    bool refine_with_backtracking_after = true;
};

// callback(generation, best_fitness, best_hard_conflicts) — для UI прогресса (раздел 5.2 ТЗ).
using ProgressCallback = std::function<void(int, double, int)>;

struct GAResult {
    Chromosome best;
    FitnessResult best_fitness;
    int generations_run = 0;
};

GAResult run_genetic_algorithm(
    const ScheduleContext& ctx,
    const GAParams& params,
    ProgressCallback on_progress = nullptr
);

} // namespace scheduler
