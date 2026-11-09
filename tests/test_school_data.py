"""Tests for the importable school data format."""
import unittest

from app.services.school_data import (
    SCHOOL_FORMAT,
    build_context,
    sample_school_data,
    validate_school_data,
)


class SchoolDataTests(unittest.TestCase):
    def test_sample_data_builds_scheduler_context(self):
        school = validate_school_data(sample_school_data())
        context, subjects, classes = build_context(school)
        self.assertEqual(len(context.groups), 14)
        self.assertEqual(len(context.lesson_instances), 46)
        self.assertEqual(subjects[1], "Математика")
        self.assertEqual(classes[101], "5А")

    def test_rejects_unknown_format(self):
        document = sample_school_data()
        document["format"] = "other"
        with self.assertRaisesRegex(ValueError, "Ожидался формат"):
            validate_school_data(document)

    def test_rejects_duplicate_group_ids(self):
        document = sample_school_data()
        document["groups"][1]["id"] = document["groups"][0]["id"]
        with self.assertRaisesRegex(ValueError, "Повторяется ID учебной группы"):
            validate_school_data(document)

    def test_rejects_unknown_class_reference(self):
        document = sample_school_data()
        document["groups"][0]["class_id"] = 9999
        with self.assertRaisesRegex(ValueError, "отсутствующий class_id"):
            validate_school_data(document)

    def test_rejects_bool_for_integer_id(self):
        document = sample_school_data()
        document["classes"][0]["id"] = True
        with self.assertRaisesRegex(ValueError, "положительным целым"):
            validate_school_data(document)

    def test_format_identifier_is_versioned(self):
        self.assertEqual(validate_school_data(sample_school_data())["format"], SCHOOL_FORMAT)


if __name__ == "__main__":
    unittest.main()
