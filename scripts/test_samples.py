"""Focused tests for privacy, repeat imports and malformed source data."""
import csv
import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path
from analyze_samples import ROOT, analyze


class ImportTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "artifacts").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / "artifacts")
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.db = self.root / "result.db"
        self.key = self.root / "key"

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, headers, rows):
        path = self.source / name
        with path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(headers)
            writer.writerows(rows)
        return path

    def test_repeat_import_preserves_sources_and_removes_direct_identifiers(self):
        path = self.write("18_rewards.csv", ["user_id", "username", "reward_name", "timestamp"], [["private-user-123", "private-person@example.test", "local reward", "2026/11/09 10:00:00"]] * 2)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        first = analyze(self.source, self.db, self.key)
        second = analyze(self.source, self.db, self.key)
        self.assertEqual(first["files"][0]["duplicate_rows"], 1)
        self.assertEqual(second["files"][0]["inserted"], 0)
        self.assertEqual(second["stored_records"]["reward"], 1)
        self.assertEqual(digest, hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertNotIn(b"private-user", self.db.read_bytes())
        self.assertNotIn(b"private-person", self.db.read_bytes())

    def test_invalid_rows_and_missing_schema_do_not_become_records(self):
        self.write("18_rewards.csv", ["user_id", "reward_name", "timestamp"], [["u1", "reward", "not-a-date"], ["", "reward", "2026-11-09"], ["u2", "", "2026-11-09"]])
        self.write("13_users.csv", ["wrong"], [["private"]])
        report = analyze(self.source, self.db, self.key)
        self.assertEqual(report["stored_records"], {})
        self.assertEqual(report["files"][0]["status"], "rejected_schema")
        metrics = report["files"][1]
        self.assertEqual((metrics["invalid_time"], metrics["missing_user"], metrics["missing_subject"]), (1, 1, 1))

    def test_foreign_users_and_key_loss_are_reported(self):
        self.write("18_rewards.csv", ["user_id", "reward_name", "timestamp"], [["u1", "reward", "2026-11-09"]])
        report = analyze(self.source, self.db, self.key)
        self.assertEqual(report["unmatched_users"], 1)
        self.key.unlink()
        with self.assertRaises(ValueError):
            analyze(self.source, self.db, self.key)

    def test_output_must_remain_inside_project(self):
        with self.assertRaises(ValueError):
            analyze(self.source, ROOT.parent / "outside.db", self.key)

    def test_person_name_correction_does_not_duplicate_event(self):
        headers = ["user_id", "username", "reward_name", "timestamp", "prize_name"]
        self.write("18_rewards.csv", headers, [["u1", "old name", "r", "2026/11/09 10:00:00", "prize"]])
        analyze(self.source, self.db, self.key)
        self.write("18_rewards.csv", headers, [["u1", "corrected name", "r", "2026-11-09 10:00:00", "prize"]])
        report = analyze(self.source, self.db, self.key)
        self.assertEqual(report["stored_records"], {"reward":1})
        self.assertEqual(report["files"][0]["already_present"], 1)


if __name__ == "__main__":
    unittest.main()
