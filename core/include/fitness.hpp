#pragma once
#include "model.hpp"
#include <vector>

namespace scheduler {

// Результат оценки хромосомы: жёсткие конфликты считаются отдельно от
// штрафа за мягкие ограничения, чтобы ГА мог сначала давить hard-конфликты
// (раздел 4 ТЗ: hard = критический штраф, soft = умеренный/низкий).
struct FitnessResult {
    int hard_conflicts = 0;
    double soft_penalty = 0.0;
    // Индексы генов (в Chromosome), которые участвуют хотя бы в одном hard-конфликте.
    // Используется бэктрекингом для точечного исправления (раздел 3 ТЗ).
    std::vector<int> conflicting_gene_indices;

    double total() const {
        // Жёсткие конфликты весят на порядки больше мягких штрафов,
        // чтобы ГА в первую очередь искал допустимое (без конфликтов) решение.
        return hard_conflicts * 1000.0 + soft_penalty;
    }
};

// Полная оценка хромосомы по всем hard- и soft-ограничениям раздела 4 ТЗ.
FitnessResult evaluate(const Chromosome& chromosome, const ScheduleContext& ctx);

} // namespace scheduler
