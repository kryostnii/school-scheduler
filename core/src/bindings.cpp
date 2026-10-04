#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/functional.h>
#include "model.hpp"
#include "genetic_algorithm.hpp"
#include "backtracking.hpp"
#include "fitness.hpp"

namespace py = pybind11;
using namespace scheduler;

PYBIND11_MODULE(scheduler_core, m) {
    m.doc() = "C++ ядро генерации школьного расписания (ГА + бэктрекинг), раздел 2-3 ТЗ";

    py::class_<SubjectGroupInfo>(m, "SubjectGroupInfo")
        .def(py::init<>())
        .def_readwrite("id", &SubjectGroupInfo::id)
        .def_readwrite("class_id", &SubjectGroupInfo::class_id)
        .def_readwrite("grade", &SubjectGroupInfo::grade)
        .def_readwrite("teacher_id", &SubjectGroupInfo::teacher_id)
        .def_readwrite("cabinet_id", &SubjectGroupInfo::cabinet_id)
        .def_readwrite("shift", &SubjectGroupInfo::shift)
        .def_readwrite("hours_per_week", &SubjectGroupInfo::hours_per_week)
        .def_readwrite("is_physical_education", &SubjectGroupInfo::is_physical_education)
        .def_readwrite("is_heavy_subject", &SubjectGroupInfo::is_heavy_subject)
        .def_readwrite("allows_double_lesson", &SubjectGroupInfo::allows_double_lesson);

    py::class_<Gene>(m, "Gene")
        .def(py::init<>())
        .def_readwrite("day", &Gene::day)
        .def_readwrite("lesson_number", &Gene::lesson_number);

    py::class_<ScheduleContext>(m, "ScheduleContext")
        .def(py::init<>())
        .def_readwrite("groups", &ScheduleContext::groups)
        .def_readwrite("days_per_week", &ScheduleContext::days_per_week)
        .def_readwrite("max_lessons_per_day", &ScheduleContext::max_lessons_per_day)
        .def("build_lesson_instances", &ScheduleContext::build_lesson_instances);

    py::class_<FitnessResult>(m, "FitnessResult")
        .def_readonly("hard_conflicts", &FitnessResult::hard_conflicts)
        .def_readonly("soft_penalty", &FitnessResult::soft_penalty)
        .def_readonly("conflicting_gene_indices", &FitnessResult::conflicting_gene_indices)
        .def("total", &FitnessResult::total);

    py::class_<GAParams>(m, "GAParams")
        .def(py::init<>())
        .def_readwrite("population_size", &GAParams::population_size)
        .def_readwrite("max_generations", &GAParams::max_generations)
        .def_readwrite("mutation_rate", &GAParams::mutation_rate)
        .def_readwrite("crossover_rate", &GAParams::crossover_rate)
        .def_readwrite("tournament_size", &GAParams::tournament_size)
        .def_readwrite("random_seed", &GAParams::random_seed)
        .def_readwrite("refine_with_backtracking_after", &GAParams::refine_with_backtracking_after);

    py::class_<GAResult>(m, "GAResult")
        .def_readonly("best", &GAResult::best)
        .def_readonly("best_fitness", &GAResult::best_fitness)
        .def_readonly("generations_run", &GAResult::generations_run);

    m.def("evaluate", &evaluate, "Оценить хромосому по hard/soft ограничениям",
          py::arg("chromosome"), py::arg("context"));

    m.def("run_genetic_algorithm", &run_genetic_algorithm,
          "Запустить генетический алгоритм генерации расписания",
          py::arg("context"), py::arg("params"), py::arg("on_progress") = nullptr);

    m.def("refine_with_backtracking", &refine_with_backtracking,
          "Точечно устранить hard-конфликты бэктрекингом",
          py::arg("chromosome"), py::arg("context"), py::arg("params") = BacktrackParams{});
}
