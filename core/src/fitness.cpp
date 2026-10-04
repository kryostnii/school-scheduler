#include "fitness.hpp"
#include <map>
#include <set>
#include <algorithm>

namespace scheduler {

namespace {

// Ключ временного слота: (день, номер урока).
using SlotKey = int;  // day * 100 + lesson_number, компактно и без коллизий при lesson<100

inline SlotKey make_slot(int day, int lesson) { return day * 100 + lesson; }

} // namespace

FitnessResult evaluate(const Chromosome& chromosome, const ScheduleContext& ctx) {
    FitnessResult result;
    const size_t n = chromosome.size();
    std::set<int> conflicting;

    // --- 1. HARD: учитель не может вести два урока одновременно ---
    // slot -> список индексов генов, занимающих этот слот данным учителем
    std::map<int64_t, std::map<SlotKey, std::vector<int>>> teacher_slots;
    // --- 2. HARD: класс не может быть на двух уроках одновременно ---
    std::map<int64_t, std::map<SlotKey, std::vector<int>>> class_slots;
    // --- 3. HARD: кабинет не может быть занят дважды одновременно (если закреплён статически) ---
    std::map<int64_t, std::map<SlotKey, std::vector<int>>> cabinet_slots;
    // --- для лимита уроков/день и правила физкультуры: class -> day -> lessons/subjects ---
    std::map<int64_t, std::map<int, std::vector<int>>> class_day_lessons; // class -> day -> gene idx list
    // --- для окон учителя/класса ---
    std::map<int64_t, std::map<int, std::vector<int>>> teacher_day_lessons;

    for (size_t i = 0; i < n; ++i) {
        const auto& gene = chromosome[i];
        const auto& li = ctx.lesson_instances[i];
        const auto& g = ctx.groups[li.group_index];
        SlotKey slot = make_slot(gene.day, gene.lesson_number);

        teacher_slots[g.teacher_id][slot].push_back(static_cast<int>(i));
        class_slots[g.class_id][slot].push_back(static_cast<int>(i));
        if (g.cabinet_id >= 0) {
            cabinet_slots[g.cabinet_id][slot].push_back(static_cast<int>(i));
        }
        class_day_lessons[g.class_id][gene.day].push_back(static_cast<int>(i));
        teacher_day_lessons[g.teacher_id][gene.day].push_back(static_cast<int>(i));
    }

    auto count_clashes = [&](std::map<int64_t, std::map<SlotKey, std::vector<int>>>& m) {
        for (auto& [_, slots] : m) {
            for (auto& [__, idxs] : slots) {
                if (idxs.size() > 1) {
                    result.hard_conflicts += static_cast<int>(idxs.size() - 1);
                    for (int idx : idxs) conflicting.insert(idx);
                }
            }
        }
    };
    count_clashes(teacher_slots);
    count_clashes(class_slots);
    count_clashes(cabinet_slots);

    // --- 4. HARD: лимит уроков в день по параллели (раздел 4.1) ---
    for (auto& [class_id, day_map] : class_day_lessons) {
        for (auto& [day, idxs] : day_map) {
            if (idxs.empty()) continue;
            int grade = ctx.groups[ctx.lesson_instances[idxs[0]].group_index].grade;
            int limit = ctx.max_lessons_for_grade(grade);
            if (static_cast<int>(idxs.size()) > limit) {
                int excess = static_cast<int>(idxs.size()) - limit;
                result.hard_conflicts += excess;
                for (int idx : idxs) conflicting.insert(idx);
            }
        }
    }

    // --- 5. HARD: физкультура не два дня подряд в одном классе ---
    for (auto& [class_id, day_map] : class_day_lessons) {
        std::set<int> pe_days;
        for (auto& [day, idxs] : day_map) {
            for (int idx : idxs) {
                const auto& g = ctx.groups[ctx.lesson_instances[idx].group_index];
                if (g.is_physical_education) pe_days.insert(day);
            }
        }
        for (int d : pe_days) {
            if (pe_days.count(d + 1)) {
                result.hard_conflicts += 1;
                // помечаем оба дня как конфликтные гены физкультуры этого класса
                for (int dd : {d, d + 1}) {
                    auto it = day_map.find(dd);
                    if (it == day_map.end()) continue;
                    for (int idx : it->second) {
                        if (ctx.groups[ctx.lesson_instances[idx].group_index].is_physical_education)
                            conflicting.insert(idx);
                    }
                }
            }
        }
    }

    // --- 6. SOFT: окна в расписании учеников (класс) и учителей ---
    auto count_windows = [&](std::map<int64_t, std::map<int, std::vector<int>>>& m) -> int {
        int windows = 0;
        for (auto& [_, day_map] : m) {
            for (auto& [__, idxs] : day_map) {
                if (idxs.empty()) continue;
                std::vector<int> lessons;
                lessons.reserve(idxs.size());
                for (int idx : idxs) lessons.push_back(chromosome[idx].lesson_number);
                std::sort(lessons.begin(), lessons.end());
                lessons.erase(std::unique(lessons.begin(), lessons.end()), lessons.end());
                for (size_t k = 1; k < lessons.size(); ++k) {
                    int gap = lessons[k] - lessons[k - 1] - 1;
                    if (gap > 0) windows += gap;
                }
            }
        }
        return windows;
    };
    int class_windows = count_windows(class_day_lessons);
    int teacher_windows = count_windows(teacher_day_lessons);
    result.soft_penalty += class_windows * 3.0;    // окна у учеников штрафуются сильнее
    result.soft_penalty += teacher_windows * 1.0;

    // --- 7. SOFT: тяжёлые предметы не первым/последним уроком ---
    for (size_t i = 0; i < n; ++i) {
        const auto& gene = chromosome[i];
        const auto& g = ctx.groups[ctx.lesson_instances[i].group_index];
        if (g.is_heavy_subject) {
            int limit = ctx.max_lessons_for_grade(g.grade);
            if (gene.lesson_number == 1 || gene.lesson_number == limit) {
                result.soft_penalty += 2.0;
            }
        }
    }

    // --- 8. SOFT: пик нагрузки должен приходиться на дни наибольшей работоспособности ---
    for (auto& [class_id, day_map] : class_day_lessons) {
        if (day_map.empty()) continue;
        int grade = ctx.groups[ctx.lesson_instances[day_map.begin()->second[0]].group_index].grade;
        auto peak_days = ctx.peak_days_for_grade(grade);
        std::set<int> peak_set(peak_days.begin(), peak_days.end());

        double peak_avg = 0, other_avg = 0;
        int peak_days_count = 0, other_days_count = 0;
        for (auto& [day, idxs] : day_map) {
            if (peak_set.count(day)) { peak_avg += idxs.size(); peak_days_count++; }
            else { other_avg += idxs.size(); other_days_count++; }
        }
        if (peak_days_count > 0) peak_avg /= peak_days_count;
        if (other_days_count > 0) other_avg /= other_days_count;
        // Если непиковые дни в среднем нагруженнее пиковых — штраф (нагрузка распределена неверно).
        if (other_avg > peak_avg) {
            result.soft_penalty += (other_avg - peak_avg) * 1.5;
        }
    }

    result.conflicting_gene_indices.assign(conflicting.begin(), conflicting.end());
    return result;
}

} // namespace scheduler
