-- ============================================================
-- Schema: School Scheduler (SQLite)
-- Согласно ТЗ v2: расписание общего среднего образования (РБ)
-- Атомарная единица планирования — subject_groups (класс/подгруппа)
-- ============================================================

PRAGMA foreign_keys = ON;

-- Учебный год (для переноса данных между годами, раздел 5.4 ТЗ)
CREATE TABLE academic_years (
    id                INTEGER PRIMARY KEY,
    label             TEXT NOT NULL,                 -- "2026/2027"
    is_active         INTEGER NOT NULL DEFAULT 0 CHECK (is_active IN (0,1))
);

-- Смены обучения (раздел 3 ТЗ)
CREATE TABLE shifts (
    id                INTEGER PRIMARY KEY,
    name              TEXT NOT NULL,                 -- "I смена", "II смена"
    ordinal           INTEGER NOT NULL UNIQUE         -- 1, 2
);

-- Расписание звонков — своё для каждой смены
CREATE TABLE bell_schedule (
    id                INTEGER PRIMARY KEY,
    shift_id          INTEGER NOT NULL REFERENCES shifts(id) ON DELETE CASCADE,
    lesson_number     INTEGER NOT NULL,
    start_time        TEXT NOT NULL,                 -- "08:00"
    end_time          TEXT NOT NULL,
    UNIQUE(shift_id, lesson_number)
);

-- Кабинетный фонд
CREATE TABLE cabinets (
    id                INTEGER PRIMARY KEY,
    number            TEXT NOT NULL UNIQUE,
    capacity          INTEGER,
    room_type         TEXT NOT NULL DEFAULT 'general', -- general, gym, computer, chemistry, physics, ...
    shift_id          INTEGER REFERENCES shifts(id)    -- NULL = доступен в обе смены
);

-- Предметы + редактируемая ранговая шкала трудности (Минздрав РБ, раздел 3 ТЗ)
CREATE TABLE subjects (
    id                    INTEGER PRIMARY KEY,
    name                  TEXT NOT NULL UNIQUE,
    difficulty_rank       INTEGER NOT NULL DEFAULT 5,   -- выше = сложнее
    is_physical_education INTEGER NOT NULL DEFAULT 0 CHECK (is_physical_education IN (0,1)),
    is_heavy_subject      INTEGER NOT NULL DEFAULT 0 CHECK (is_heavy_subject IN (0,1)),
    allows_double_lesson  INTEGER NOT NULL DEFAULT 0 CHECK (allows_double_lesson IN (0,1))
);

-- Учителя
CREATE TABLE teachers (
    id                INTEGER PRIMARY KEY,
    full_name         TEXT NOT NULL,
    max_load_hours    INTEGER NOT NULL,
    home_cabinet_id   INTEGER REFERENCES cabinets(id),
    shift_id          INTEGER REFERENCES shifts(id)     -- NULL = работает в обе смены
);

-- Пожелания учителей (мягкие ограничения, раздел 4.2 ТЗ)
CREATE TABLE teacher_wishes (
    id                INTEGER PRIMARY KEY,
    teacher_id        INTEGER NOT NULL REFERENCES teachers(id) ON DELETE CASCADE,
    wish_type         TEXT NOT NULL,   -- 'day_off' | 'preferred_lesson' | 'avoid_lesson' | 'method_day'
    day_of_week       INTEGER,         -- 1..6, NULL если не привязано ко дню
    lesson_number     INTEGER,         -- NULL если не привязано к уроку
    weight            INTEGER NOT NULL DEFAULT 1
);

-- Классы
CREATE TABLE classes (
    id                INTEGER PRIMARY KEY,
    academic_year_id  INTEGER NOT NULL REFERENCES academic_years(id),
    grade             INTEGER NOT NULL CHECK (grade BETWEEN 1 AND 12),
    letter            TEXT NOT NULL,                 -- "А", "Б", ...
    shift_id          INTEGER NOT NULL REFERENCES shifts(id),
    UNIQUE(academic_year_id, grade, letter)
);

-- Учебный план класса: предмет + часы/неделю (+ признак деления на подгруппы)
CREATE TABLE class_subjects (
    id                INTEGER PRIMARY KEY,
    class_id          INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    subject_id        INTEGER NOT NULL REFERENCES subjects(id),
    hours_per_week    INTEGER NOT NULL,
    is_split          INTEGER NOT NULL DEFAULT 0 CHECK (is_split IN (0,1)),
    UNIQUE(class_id, subject_id)
);

-- Подгруппы — атомарная единица планирования (раздел 3 ТЗ).
-- is_split=0 -> одна запись, group_number=1 (весь класс).
-- is_split=1 -> обычно 2 записи, group_number=1 и 2, разные учителя/кабинеты.
CREATE TABLE subject_groups (
    id                  INTEGER PRIMARY KEY,
    class_subject_id    INTEGER NOT NULL REFERENCES class_subjects(id) ON DELETE CASCADE,
    group_number        INTEGER NOT NULL DEFAULT 1,
    teacher_id          INTEGER NOT NULL REFERENCES teachers(id),
    cabinet_id          INTEGER REFERENCES cabinets(id),   -- NULL = подбирается динамически ядром
    UNIQUE(class_subject_id, group_number)
);

-- Санитарные нормы с возможностью ручного отключения (раздел 4.1 ТЗ)
CREATE TABLE sanpin_rules (
    id                INTEGER PRIMARY KEY,
    code              TEXT NOT NULL UNIQUE,   -- 'no_pe_two_days_running', 'max_lessons_grade_1', ...
    description       TEXT NOT NULL,
    is_enabled        INTEGER NOT NULL DEFAULT 1 CHECK (is_enabled IN (0,1))
);

-- Итоговое расписание (результат генерации / ручных правок)
CREATE TABLE timetable_entries (
    id                  INTEGER PRIMARY KEY,
    subject_group_id    INTEGER NOT NULL REFERENCES subject_groups(id) ON DELETE CASCADE,
    day_of_week         INTEGER NOT NULL CHECK (day_of_week BETWEEN 1 AND 6),
    lesson_number       INTEGER NOT NULL,
    cabinet_id          INTEGER REFERENCES cabinets(id),
    paired_entry_id      INTEGER REFERENCES timetable_entries(id),  -- сдвоенные уроки (X-XI)
    UNIQUE(subject_group_id, day_of_week, lesson_number)
);

-- История запусков генерации (для UI прогресса и отладки)
CREATE TABLE generation_runs (
    id                INTEGER PRIMARY KEY,
    started_at        TEXT NOT NULL,
    finished_at       TEXT,
    fitness_score     REAL,
    hard_conflicts    INTEGER,
    status            TEXT NOT NULL DEFAULT 'running'  -- running | stopped | completed
);

CREATE INDEX idx_timetable_day_lesson   ON timetable_entries(day_of_week, lesson_number);
CREATE INDEX idx_subject_groups_teacher ON subject_groups(teacher_id);
CREATE INDEX idx_classes_year           ON classes(academic_year_id);

-- ============================================================
-- Базовые санитарные правила РБ (seed) — раздел 4.1 ТЗ
-- ============================================================
INSERT INTO sanpin_rules (code, description, is_enabled) VALUES
 ('no_pe_two_days_running', 'Физическая культура не может стоять два дня подряд в одном классе', 1),
 ('max_lessons_grade_1', '1 класс: не более 4 уроков в день (1 раз в неделю — 5 за счёт физкультуры)', 1),
 ('max_lessons_grade_2_4', '2-4 классы: не более 5 уроков в день (1 раз в неделю — 6 за счёт физкультуры)', 1),
 ('max_lessons_grade_5_6', '5-6 классы: не более 6 уроков в день', 1),
 ('max_lessons_grade_7_11', '7-11(12) классы: не более 7 уроков в день', 1),
 ('grade_1_first_shift_only', '1 класс — только первая смена, 5-дневная неделя', 1),
 ('grade_5_no_second_shift', '5 класс не ставится во вторую смену', 1),
 ('final_grade_no_second_shift', 'Выпускные классы не ставятся во вторую смену', 1),
 ('heavy_subject_not_first_last', 'Предметы большого умственного напряжения — не чаще раза в неделю первым/последним уроком', 1),
 ('peak_load_days', 'Макс. нагрузка: вт/ср (I-IV), вт/ср/пт (V-XI(XII))', 1);
