"""
SQLAlchemy-модели, зеркалящие db/schema.sql.
Раздел 3 ТЗ: атомарная единица планирования — SubjectGroup (класс/подгруппа).
"""
from __future__ import annotations

from sqlalchemy import (
    create_engine, ForeignKey, UniqueConstraint, CheckConstraint
)
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column, relationship, Session
)


class Base(DeclarativeBase):
    pass


class AcademicYear(Base):
    __tablename__ = "academic_years"
    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str]
    is_active: Mapped[int] = mapped_column(default=0)


class Shift(Base):
    __tablename__ = "shifts"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    ordinal: Mapped[int] = mapped_column(unique=True)


class Cabinet(Base):
    __tablename__ = "cabinets"
    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(unique=True)
    capacity: Mapped[int | None]
    room_type: Mapped[str] = mapped_column(default="general")
    shift_id: Mapped[int | None] = mapped_column(ForeignKey("shifts.id"))


class Subject(Base):
    __tablename__ = "subjects"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    difficulty_rank: Mapped[int] = mapped_column(default=5)
    is_physical_education: Mapped[int] = mapped_column(default=0)
    is_heavy_subject: Mapped[int] = mapped_column(default=0)
    allows_double_lesson: Mapped[int] = mapped_column(default=0)


class Teacher(Base):
    __tablename__ = "teachers"
    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str]
    max_load_hours: Mapped[int]
    home_cabinet_id: Mapped[int | None] = mapped_column(ForeignKey("cabinets.id"))
    shift_id: Mapped[int | None] = mapped_column(ForeignKey("shifts.id"))


class TeacherWish(Base):
    __tablename__ = "teacher_wishes"
    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id", ondelete="CASCADE"))
    wish_type: Mapped[str]
    day_of_week: Mapped[int | None]
    lesson_number: Mapped[int | None]
    weight: Mapped[int] = mapped_column(default=1)


class SchoolClass(Base):
    __tablename__ = "classes"
    id: Mapped[int] = mapped_column(primary_key=True)
    academic_year_id: Mapped[int] = mapped_column(ForeignKey("academic_years.id"))
    grade: Mapped[int]
    letter: Mapped[str]
    shift_id: Mapped[int] = mapped_column(ForeignKey("shifts.id"))

    __table_args__ = (UniqueConstraint("academic_year_id", "grade", "letter"),)


class ClassSubject(Base):
    __tablename__ = "class_subjects"
    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"))
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"))
    hours_per_week: Mapped[int]
    is_split: Mapped[int] = mapped_column(default=0)
    profile_id: Mapped[int | None] = mapped_column(default=None)

    __table_args__ = (UniqueConstraint("class_id", "subject_id"),)


class SubjectGroup(Base):
    """Раздел 3 ТЗ: атомарная единица планирования (класс/подгруппа)."""
    __tablename__ = "subject_groups"
    id: Mapped[int] = mapped_column(primary_key=True)
    class_subject_id: Mapped[int] = mapped_column(ForeignKey("class_subjects.id", ondelete="CASCADE"))
    group_number: Mapped[int] = mapped_column(default=1)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id"))
    cabinet_id: Mapped[int | None] = mapped_column(ForeignKey("cabinets.id"))

    __table_args__ = (UniqueConstraint("class_subject_id", "group_number"),)


class SanpinRule(Base):
    __tablename__ = "sanpin_rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str]
    is_enabled: Mapped[int] = mapped_column(default=1)


class TimetableEntry(Base):
    __tablename__ = "timetable_entries"
    id: Mapped[int] = mapped_column(primary_key=True)
    subject_group_id: Mapped[int] = mapped_column(ForeignKey("subject_groups.id", ondelete="CASCADE"))
    day_of_week: Mapped[int]
    lesson_number: Mapped[int]
    cabinet_id: Mapped[int | None] = mapped_column(ForeignKey("cabinets.id"))
    paired_entry_id: Mapped[int | None] = mapped_column(ForeignKey("timetable_entries.id"))

    __table_args__ = (UniqueConstraint("subject_group_id", "day_of_week", "lesson_number"),)


def make_engine(path: str = "sqlite:///school.sqlite3"):
    """Открыть/создать файл БД проекта школы (раздел 2 ТЗ: локальный SQLite-файл)."""
    engine = create_engine(path)
    Base.metadata.create_all(engine)
    return engine


def make_session(engine) -> Session:
    return Session(engine)
