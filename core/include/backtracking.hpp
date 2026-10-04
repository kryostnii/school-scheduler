#pragma once
#include "model.hpp"
#include "fitness.hpp"

namespace scheduler {

struct BacktrackParams {
    int max_iterations = 2000;
};

// Точечная доводка: перебирает альтернативные слоты для генов, участвующих
// в hard-конфликтах, пытаясь их устранить без ухудшения остальных (раздел 3 ТЗ:
// "если генетический алгоритм застревает в локальном оптимуме, бэктрекинг
// точечно перебирает комбинации для устранения единичных жёстких конфликтов").
Chromosome refine_with_backtracking(
    const Chromosome& chromosome,
    const ScheduleContext& ctx,
    const BacktrackParams& params = {}
);

} // namespace scheduler
