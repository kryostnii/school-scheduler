// Автономный смоук-тест ядра БЕЗ pybind11 — собирается напрямую g++,
// чтобы можно было отлаживать алгоритм ещё до настройки Python-биндингов.
// Собрать: g++ -std=c++20 -O2 -I../include smoke_test.cpp ../src/fitness.cpp
//              ../src/genetic_algorithm.cpp ../src/backtracking.cpp -o smoke_test
#include "../include/model.hpp"
#include "../include/fitness.hpp"
#include "../include/genetic_algorithm.hpp"
#include "../include/backtracking.hpp"
#include <iostream>
#include <iomanip>
#include <cassert>
#include <random>

using namespace scheduler;

// Небольшая тестовая школа: 3 класса, часть предметов с делением на подгруппы.
ScheduleContext build_sample_context() {
    ScheduleContext ctx;
    ctx.days_per_week = 6;

    int64_t next_id = 1;

    auto add_group = [&](int64_t class_id, int grade, int64_t teacher_id, int hours,
                          bool is_pe = false, bool is_heavy = false) {
        SubjectGroupInfo g;
        g.id = next_id++;
        g.class_id = class_id;
        g.grade = grade;
        g.teacher_id = teacher_id;
        g.cabinet_id = -1;
        g.shift = 1;
        g.hours_per_week = hours;
        g.is_physical_education = is_pe;
        g.is_heavy_subject = is_heavy;
        ctx.groups.push_back(g);
    };

    // Класс 101 (5 класс), учителя 1..5
    add_group(/*class*/101, /*grade*/5, /*teacher*/1, /*hours*/5, false, true);  // математика
    add_group(101, 5, 2, 4, false, true);   // русский язык
    add_group(101, 5, 3, 2, true, false);   // физкультура
    add_group(101, 5, 4, 3, false, false);  // история
    add_group(101, 5, 5, 2, false, false);  // биология

    // Класс 102 (5 класс), частично те же учителя (проверяем конфликты учителей между классами)
    add_group(102, 5, 1, 5, false, true);   // тот же учитель математики что и в 101
    add_group(102, 5, 6, 4, false, true);
    add_group(102, 5, 3, 2, true, false);   // тот же физкультурник
    add_group(102, 5, 7, 3, false, false);
    add_group(102, 5, 8, 2, false, false);

    // Класс 201 (2 класс) — проверяем лимит уроков/день (не более 5)
    add_group(201, 2, 9, 5, false, true);
    add_group(201, 2, 10, 4, false, false);
    add_group(201, 2, 11, 2, true, false);
    add_group(201, 2, 12, 3, false, false);

    ctx.build_lesson_instances();
    return ctx;
}

int main() {
    ScheduleContext ctx = build_sample_context();
    std::cout << "Тестовая школа: " << ctx.groups.size() << " подгрупп, "
              << ctx.lesson_instances.size() << " уроков-часов в неделю\n";

    // Оценка случайной (заведомо конфликтной) хромосомы — baseline.
    {
        std::mt19937 rng(1);
        Chromosome random_c(ctx.lesson_instances.size());
        std::uniform_int_distribution<int> day_dist(1, ctx.days_per_week);
        std::uniform_int_distribution<int> lesson_dist(1, 7);
        for (auto& gene : random_c) gene = Gene{day_dist(rng), lesson_dist(rng)};
        FitnessResult baseline = evaluate(random_c, ctx);
        std::cout << "Случайное расписание:  hard_conflicts=" << baseline.hard_conflicts
                  << "  soft_penalty=" << std::fixed << std::setprecision(1) << baseline.soft_penalty
                  << "  total=" << baseline.total() << "\n";
    }

    // Запуск ГА.
    GAParams params;
    params.population_size = 60;
    params.max_generations = 300;
    params.mutation_rate = 0.1;

    std::cout << "\nЗапуск генетического алгоритма...\n";
    GAResult result = run_genetic_algorithm(ctx, params, [](int gen, double fitness, int hard) {
        if (gen % 50 == 0 || hard == 0) {
            std::cout << "  поколение " << std::setw(4) << gen
                      << "  hard_conflicts=" << std::setw(3) << hard
                      << "  fitness=" << std::fixed << std::setprecision(1) << fitness << "\n";
        }
    });

    std::cout << "\nИтог после " << result.generations_run << " поколений + бэктрекинга:\n";
    std::cout << "  hard_conflicts=" << result.best_fitness.hard_conflicts
              << "  soft_penalty=" << result.best_fitness.soft_penalty
              << "  total=" << result.best_fitness.total() << "\n";

    if (result.best_fitness.hard_conflicts == 0) {
        std::cout << "\n✓ Допустимое расписание найдено (все hard-ограничения соблюдены).\n";
    } else {
        std::cout << "\n✗ Остались hard-конфликты — увеличьте max_generations/population_size.\n";
    }

    // Печать фрагмента расписания класса 101 для визуальной проверки.
    std::cout << "\nРасписание класса 101 (день:урок -> group_id):\n";
    for (size_t i = 0; i < ctx.lesson_instances.size(); ++i) {
        const auto& li = ctx.lesson_instances[i];
        const auto& g = ctx.groups[li.group_index];
        if (g.class_id == 101) {
            std::cout << "  день " << result.best[i].day
                      << ", урок " << result.best[i].lesson_number
                      << "  <- group_id=" << g.id
                      << (g.is_physical_education ? " (физкультура)" : "") << "\n";
        }
    }

    assert(result.best.size() == ctx.lesson_instances.size());
    std::cout << "\nСмоук-тест пройден.\n";
    return result.best_fitness.hard_conflicts == 0 ? 0 : 1;
}
