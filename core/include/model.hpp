#pragma once
#include <cstdint>
#include <vector>
#include <functional>

namespace scheduler {

// Один "атом" учебного плана — подгруппа (раздел 3 ТЗ): класс/подгруппа x предмет x учитель.
// Соответствует одной строке таблицы subject_groups в БД, обогащённой метаданными,
// которые нужны ядру для проверки ограничений (иначе пришлось бы лезть в БД из C++).
struct SubjectGroupInfo {
    int64_t id;
    int64_t class_id;
    int grade;                 // 1..12, нужно для лимитов уроков/день и правил 1 класса
    int64_t teacher_id;
    int64_t cabinet_id = -1;   // -1 = кабинет не закреплён статически (динамика — вне MVP-ядра)
    int shift;                 // 1 или 2
    int hours_per_week;
    bool is_physical_education = false;  // для правила "не два дня подряд"
    bool is_heavy_subject = false;       // для правила "не первым/последним уроком"
    bool allows_double_lesson = false;
};

// Один "ген" хромосомы — одно занятие (один час) одной подгруппы.
// lesson_instances (см. ScheduleContext) и Chromosome — параллельные массивы одинаковой длины:
// chromosome[i] задаёт день/урок для lesson_instances[i].
struct LessonInstance {
    int64_t subject_group_id;
    int group_index;    // индекс в ScheduleContext::groups, для быстрого доступа к метаданным
    int occurrence;      // 0..hours_per_week-1
};

struct Gene {
    int day;             // 1..days_per_week
    int lesson_number;   // 1..max_lessons_per_day
};

using Chromosome = std::vector<Gene>;

// Контекст генерации: всё, что ядру нужно знать о школе для данного запуска.
// Строится один раз Python-слоем из данных БД (см. app/services/context_builder.py).
struct ScheduleContext {
    std::vector<SubjectGroupInfo> groups;
    std::vector<LessonInstance> lesson_instances;  // развёрнутые "часы" всех групп
    int days_per_week = 6;
    int max_lessons_per_day = 7;   // общий потолок сетки (реальный лимит по классу — в fitness)

    // Санитарные лимиты уроков/день по параллели (раздел 4.1 ТЗ), редактируемые через sanpin_rules.
    int max_lessons_for_grade(int grade) const {
        if (grade == 1) return 4;
        if (grade <= 4) return 5;
        if (grade <= 6) return 6;
        return 7;
    }

    // Дни пиковой нагрузки по параллели (раздел 4.1 ТЗ: вт/ср для I-IV, вт/ср/пт для V-XI(XII)).
    std::vector<int> peak_days_for_grade(int grade) const {
        if (grade <= 4) return {2, 3};
        return {2, 3, 5};
    }

    void build_lesson_instances() {
        lesson_instances.clear();
        for (int gi = 0; gi < static_cast<int>(groups.size()); ++gi) {
            const auto& g = groups[gi];
            for (int occ = 0; occ < g.hours_per_week; ++occ) {
                lesson_instances.push_back({g.id, gi, occ});
            }
        }
    }
};

} // namespace scheduler
