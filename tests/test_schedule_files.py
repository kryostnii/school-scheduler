"""Tests for validated portable schedule files."""
import unittest

from app.services.schedule_files import load_schedule_document, make_schedule_document
from app.services.school_data import build_context, sample_school_data
from app.services.reference_scheduler import Gene


class ScheduleFileTests(unittest.TestCase):
    def setUp(self):
        self.school = sample_school_data()
        self.context, _, _ = build_context(self.school)
        self.chromosome = [Gene(day=1 + (i % 6), lesson_number=1) for i in self.context.lesson_instances]

    def test_round_trip_includes_school_and_all_lessons(self):
        document = make_schedule_document(self.school, self.context, self.chromosome)
        loaded_school, context, subjects, classes, chromosome = load_schedule_document(document)
        self.assertEqual(loaded_school, self.school)
        self.assertEqual(len(context.lesson_instances), len(self.chromosome))
        self.assertEqual([(g.day, g.lesson_number) for g in chromosome],
                         [(g.day, g.lesson_number) for g in self.chromosome])
        self.assertEqual(subjects[1], "Математика")
        self.assertEqual(classes[101], "5А")

    def test_rejects_duplicate_hours(self):
        document = make_schedule_document(self.school, self.context, self.chromosome)
        document["schedule"][1] = dict(document["schedule"][0])
        with self.assertRaisesRegex(ValueError, "повторно"):
            load_schedule_document(document)

    def test_rejects_boolean_day(self):
        document = make_schedule_document(self.school, self.context, self.chromosome)
        document["schedule"][0]["day"] = True
        with self.assertRaisesRegex(ValueError, "Некорректный день"):
            load_schedule_document(document)

    def test_rejects_missing_hours(self):
        document = make_schedule_document(self.school, self.context, self.chromosome)
        document["schedule"].pop()
        with self.assertRaisesRegex(ValueError, "ровно по одной записи"):
            load_schedule_document(document)


if __name__ == "__main__":
    unittest.main()
