"""
Математическая модель и функция приспособленности для школьного расписания.

Этот файл содержит формализацию задачи планирования как комбинаторной оптимизации,
с четким разделением жестких и мягких ограничений.
"""

from dataclasses import dataclass, field
from typing import List, Set, Tuple
import math


@dataclass
class HardConstraint:
    """
    Жесткие ограничения (Hard Constraints) - те, которые не могут быть нарушены.
    
    Эти ограничения должны быть полностью удовлетворены для допустимого решения.
    """
    # Конфликт учителя (один учитель не может быть в двух местах одновременно)
    teacher_conflict: bool = False
    
    # Конфликт кабинета (один кабинет не может быть занят двумя занятиями одновременно)
    cabinet_conflict: bool = False
    
    # Превышение максимального количества уроков в день для класса
    max_lessons_exceeded: bool = False
    
    # Нарушение расписания звонков (урок за пределами времени)
    bell_schedule_violation: bool = False
    
    # Нарушение правил СанПиН (например, 1 класс только в I смене)
    sanpin_violation: bool = False


@dataclass
class SoftConstraint:
    """
    Мягкие ограничения (Soft Constraints) - те, которые желательно соблюдать,
    но не критичные для допустимости решения.
    
    Эти ограничения оцениваются с помощью штрафов в функции приспособленности.
    """
    # Окна учителей/классов (перерывы между занятиями)
    teacher_windows: float = 0.0
    
    # Нарушение порядка предметов по трудности (по СанПиН)
    difficulty_order_violation: float = 0.0
    
    # Физкультура два дня подряд
    pe_two_days_running: float = 0.0
    
    # Тяжелые предметы первым/последним уроком
    heavy_subject_position: float = 0.0
    
    # Пиковые нагрузки (вт/ср)
    peak_load_violation: float = 0.0


@dataclass
class FitnessFunction:
    """
    Функция приспособленности для оценки качества расписания.
    
    Стратегия: жесткие конфликты имеют вес на порядки выше мягких штрафов,
    чтобы генетический алгоритм сначала находил допустимые решения.
    """
    
    # Веса для разных типов ограничений
    hard_weight: float = 10000.0  # Жесткие ограничения в 10000 раз важнее мягких
    soft_weight: float = 1.0
    
    def calculate_hard_penalty(self, constraints: HardConstraint) -> int:
        """
        Рассчитывает штраф за жесткие ограничения.
        
        Args:
            constraints: Объект с ограничениями
            
        Returns:
            int: Штраф (0 если все ограничения соблюдены)
        """
        penalty = 0
        
        # Каждое нарушение жесткого ограничения добавляет значительный штраф
        if constraints.teacher_conflict:
            penalty += self.hard_weight * 1000
        if constraints.cabinet_conflict:
            penalty += self.hard_weight * 1000
        if constraints.max_lessons_exceeded:
            penalty += self.hard_weight * 100
        if constraints.bell_schedule_violation:
            penalty += self.hard_weight * 1000
        if constraints.sanpin_violation:
            penalty += self.hard_weight * 500
            
        return penalty
    
    def calculate_soft_penalty(self, constraints: SoftConstraint) -> float:
        """
        Рассчитывает штраф за мягкие ограничения.
        
        Args:
            constraints: Объект с мягкими ограничениями
            
        Returns:
            float: Штраф (0 если все ограничения соблюдены)
        """
        penalty = 0.0
        
        # Мягкие ограничения оцениваются по весу
        penalty += constraints.teacher_windows * self.soft_weight * 10
        penalty += constraints.difficulty_order_violation * self.soft_weight * 5
        penalty += constraints.pe_two_days_running * self.soft_weight * 20
        penalty += constraints.heavy_subject_position * self.soft_weight * 15
        penalty += constraints.peak_load_violation * self.soft_weight * 10
        
        return penalty
    
    def evaluate(self, hard_constraints: HardConstraint, 
                soft_constraints: SoftConstraint) -> float:
        """
        Оценивает качество расписания по функции приспособленности.
        
        Args:
            hard_constraints: Жесткие ограничения
            soft_constraints: Мягкие ограничения
            
        Returns:
            float: Общая оценка (чем меньше, тем лучше)
        """
        hard_penalty = self.calculate_hard_penalty(hard_constraints)
        soft_penalty = self.calculate_soft_penalty(soft_constraints)
        
        # Жесткие конфликты имеют приоритет
        if hard_penalty > 0:
            return hard_penalty + soft_penalty * 100  # Увеличиваем вес мягких штрафов при наличии жестких
        
        return soft_penalty


@dataclass
class ScheduleSolution:
    """
    Представление решения задачи планирования.
    
    Хромосома в генетическом алгоритме - это расписание для всех подгрупп.
    """
    # Индекс подгруппы в контексте
    subject_group_id: int
    
    # День недели (1-6)
    day_of_week: int
    
    # Номер урока (1-8 обычно)
    lesson_number: int
    
    # Кабинет (если известен)
    cabinet_id: int = None


@dataclass
class ScheduleContext:
    """
    Контекст задачи планирования - данные о школе и ограничениях.
    
    Этот контекст используется как входные данные для алгоритма.
    """
    # Подгруппы (атомарные единицы планирования)
    subject_groups: List[dict] = field(default_factory=list)
    
    # Учителя
    teachers: List[dict] = field(default_factory=list)
    
    # Кабинеты
    cabinets: List[dict] = field(default_factory=list)
    
    # СанПиН правила
    sanpin_rules: List[dict] = field(default_factory=list)
    
    # Расписание звонков
    bell_schedule: List[dict] = field(default_factory=list)
    
    # Максимальное количество уроков в день по классам
    max_lessons_per_grade: dict = field(default_factory=dict)
    
    # Пиковые дни нагрузки по классам
    peak_days_per_grade: dict = field(default_factory=dict)


def explain_hybrid_approach():
    """
    Объяснение необходимости гибридного подхода (ГА + Бэктрекинг).
    
    В теории информатики и комбинаторной оптимизации:
    
    1. Чисто графовые алгоритмы (например, раскраска вершин) не могут эффективно 
       учитывать мягкие ограничения и сложные зависимости между элементами.
       
    2. Генетический алгоритм эффективен для глобального поиска в пространстве решений,
       но может "застревать" в локальных оптимумах при наличии множества мягких ограничений.
       
    3. Бэктрекинг (локальный поиск) позволяет точечно устранять конфликты, 
       которые ГА не смог найти в глобальном поиске.
       
    4. Смешанная стратегия обеспечивает:
       - Быстрое нахождение близких к оптимальному решений (ГА)
       - Точное устранение конфликтов (Бэктрекинг)
       - Эффективность вычислений при больших масштабах
    """
    
    explanation = """
    Математическое обоснование гибридного подхода:

    1. NP-трудность задачи планирования:
       - Задача планирования расписания является NP-трудной комбинаторной оптимизацией
       - Существует экспоненциальное количество возможных расписаний
       - Жесткие ограничения создают жесткие ограничения на допустимые решения

    2. Ограничения в задаче:
       - Жесткие ограничения: конфликты учителей, кабинетов, лимиты уроков
       - Мягкие ограничения: СанПиН, окна, предпочтения

    3. Почему чистые методы не работают:
       - Графовые алгоритмы (раскраска) не учитывают мягкие ограничения
       - Чистый ГА застревает в локальных оптимумах при сложных мягких ограничениях
       - Прямой перебор невозможен из-за экспоненциального роста

    4. Преимущества гибридного подхода:
       - ГА для глобального поиска (поиск хорошего начального решения)
       - Бэктрекинг для устранения оставшихся конфликтов
       - Эффективное использование ресурсов вычислений
       - Устойчивость к различным типам ограничений

    5. Математическая модель:
       F(solution) = HardConstraints + SoftConstraints * Weight
       
       где HardConstraints >> SoftConstraints (обычно на порядки)
    """
    
    return explanation


def analyze_complexity():
    """
    Анализ сложности задачи планирования.
    
    Сложность задачи определяется:
    1. Количеством подгрупп (N)
    2. Количеством дней и уроков (D * L)
    3. Количеством ограничений (C)
    
    Общее количество возможных расписаний: (D * L) ^ N
    """
    
    complexity_analysis = """
    Сложность задачи планирования:
    
    1. Временная сложность:
       - Генетический алгоритм: O(PopulationSize * Generations * N)
       - Бэктрекинг: O(N * D * L) в худшем случае
       
    2. Пространственная сложность:
       - Хранение популяции: O(PopulationSize * N)
       - Хранение контекста: O(N + T + C + D * L)
       
    3. Сложность ограничений:
       - Жесткие ограничения: O(1) проверка
       - Мягкие ограничения: O(N) для оценки
       
    4. Эффективность гибридного подхода:
       - ГА быстро находит хорошие решения (но не оптимальные)
       - Бэктрекинг устраняет конфликты с высокой точностью
       - Общая эффективность: O(N * D * L) в среднем случае
    """
    
    return complexity_analysis


if __name__ == "__main__":
    # Пример использования
    fitness = FitnessFunction()
    
    # Пример жестких ограничений
    hard_constraints = HardConstraint(
        teacher_conflict=True,
        cabinet_conflict=False,
        max_lessons_exceeded=False,
        bell_schedule_violation=False,
        sanpin_violation=False
    )
    
    # Пример мягких ограничений
    soft_constraints = SoftConstraint(
        teacher_windows=2.0,
        difficulty_order_violation=1.0,
        pe_two_days_running=0.5,
        heavy_subject_position=0.3,
        peak_load_violation=1.2
    )
    
    # Оценка качества решения
    score = fitness.evaluate(hard_constraints, soft_constraints)
    print(f"Оценка решения: {score}")
