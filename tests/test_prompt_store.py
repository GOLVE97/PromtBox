import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as promptbox


class PromptStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.data_dir = root / "PromptBox"
        self.db_path = self.data_dir / "prompts.db"
        self.settings_path = self.data_dir / "settings.json"
        self.patches = [
            patch.object(promptbox, "DATA_DIR", self.data_dir),
            patch.object(promptbox, "DB_PATH", self.db_path),
            patch.object(promptbox, "SETTINGS_PATH", self.settings_path),
        ]
        for item in self.patches:
            item.start()
        self.store = promptbox.PromptStore()

    def tearDown(self):
        self.store.conn.close()
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def test_create_search_and_favorite(self):
        self.store.save("Python helper", "Write a Python function", "Development", "python,code", True)
        rows = self.store.all(search="python")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "Python helper")
        self.assertEqual(rows[0]["is_favorite"], 1)
        self.assertEqual(self.store.all(favorites_only=True)[0]["title"], "Python helper")

    def test_update_preserves_original_creation_timestamp(self):
        self.store.save("First", "Body", "General")
        row = self.store.all()[0]
        created = row["created_at"]
        self.store.save("Changed", "New body", "Work", "tag", True, prompt_id=row["id"])
        changed = self.store.get(row["id"])
        self.assertEqual(changed["created_at"], created)
        self.assertEqual(changed["title"], "Changed")
        self.assertEqual(changed["category"], "Work")

    def test_delete_category_moves_prompts_to_general(self):
        self.store.save("Task", "Do it", "Temporary")
        self.store.delete_category("Temporary")
        self.assertEqual(self.store.all()[0]["category"], "General")

    def test_category_names_are_normalized_and_case_insensitive(self):
        self.store.save("First", "Body", "Work")
        self.store.save("Second", "Body", " work ")
        rows = self.store.all()
        self.assertEqual({row["category"] for row in rows}, {"Work"})
        self.assertEqual(promptbox.validate_category_name(" Ideas ", ["Work"]), "Ideas")
        with self.assertRaises(ValueError):
            promptbox.validate_category_name(" ideas ", ["Ideas"])

    def test_rename_rejects_existing_category_case_insensitively(self):
        self.store.save("One", "Body", "Work")
        self.store.save("Two", "Body", "Ideas")
        with self.assertRaises(ValueError):
            self.store.rename_category("Ideas", "work")
        self.assertEqual({row["category"] for row in self.store.all()}, {"Work", "Ideas"})

    def test_hidden_default_categories_can_be_removed_and_recreated(self):
        visible = self.store.categories(hidden_categories=["Trabajo"])
        self.assertNotIn("Trabajo", visible)
        recreated = self.store.categories(custom_categories=["Trabajo"], hidden_categories=["Trabajo"])
        self.assertIn("Trabajo", recreated)

    def test_empty_categories_are_included_in_backups(self):
        backup = Path(self.temp.name) / "empty-category-backup.json"
        self.store.export_data(backup, custom_categories=["Ideas"])
        target_dir = Path(self.temp.name) / "empty-target"
        with patch.object(promptbox, "DATA_DIR", target_dir), patch.object(promptbox, "DB_PATH", target_dir / "prompts.db"):
            target = promptbox.PromptStore()
        try:
            count, categories = target.import_data(backup)
            self.assertEqual(count, 0)
            self.assertIn("Ideas", categories)
        finally:
            target.conn.close()

    def test_export_import_round_trip(self):
        self.store.save("Résumé", "Keep accents ✓", "Personal", "important", True)
        backup = Path(self.temp.name) / "backup.json"
        self.store.export_data(backup, custom_categories=["Empty category"])
        target_dir = Path(self.temp.name) / "target"
        target_db = target_dir / "prompts.db"
        with patch.object(promptbox, "DATA_DIR", target_dir), patch.object(promptbox, "DB_PATH", target_db):
            target = promptbox.PromptStore()
        try:
            count, categories = target.import_data(backup)
            self.assertEqual(count, 1)
            imported = target.all()[0]
            self.assertEqual(imported["title"], "Résumé")
            self.assertEqual(imported["content"], "Keep accents ✓")
            self.assertEqual(imported["tags"], "important")
            self.assertEqual(imported["is_favorite"], 1)
            self.assertIn("Personal", categories)
            self.assertIn("Empty category", categories)
        finally:
            target.conn.close()

    def test_invalid_backup_does_not_change_database(self):
        self.store.save("Existing", "Keep me", "General")
        before = self.store.stats()[0]
        bad = Path(self.temp.name) / "bad.json"
        bad.write_text(json.dumps({"not_prompts": []}), encoding="utf-8")
        with self.assertRaises(ValueError):
            self.store.import_data(bad)
        self.assertEqual(self.store.stats()[0], before)

    def test_non_object_backup_is_rejected_without_changing_database(self):
        self.store.save("Existing", "Keep me", "General")
        before = self.store.stats()[0]
        bad = Path(self.temp.name) / "array.json"
        bad.write_text(json.dumps([{"title": "Wrong root"}]), encoding="utf-8")
        with self.assertRaises(ValueError):
            self.store.import_data(bad)
        self.assertEqual(self.store.stats()[0], before)

    def test_invalid_json_does_not_change_database(self):
        self.store.save("Existing", "Keep me", "General")
        before = self.store.stats()[0]
        bad = Path(self.temp.name) / "broken.json"
        bad.write_text("{not json", encoding="utf-8")
        with self.assertRaises(json.JSONDecodeError):
            self.store.import_data(bad)
        self.assertEqual(self.store.stats()[0], before)

    def test_malformed_prompt_fields_are_skipped_and_false_strings_are_not_favorites(self):
        backup = Path(self.temp.name) / "partially-invalid.json"
        backup.write_text(json.dumps({"prompts": [
            {"title": None, "content": "Not a prompt"},
            {"title": "Valid", "content": "Body", "category": "general", "is_favorite": "false"},
        ]}), encoding="utf-8")
        count, _categories = self.store.import_data(backup)
        self.assertEqual(count, 1)
        row = self.store.all()[0]
        self.assertEqual(row["category"], "General")
        self.assertEqual(row["is_favorite"], 0)

    def test_legacy_v2_backup_without_category_list_remains_supported(self):
        backup = Path(self.temp.name) / "legacy-v2.json"
        backup.write_text(json.dumps({
            "app": "PromptBox",
            "version": 2,
            "prompts": [{
                "title": "Legacy",
                "content": "Keep this prompt",
                "category": "Legacy category",
                "tags": "old,backup",
                "is_favorite": 1,
            }],
        }), encoding="utf-8")
        count, categories = self.store.import_data(backup)
        self.assertEqual(count, 1)
        self.assertEqual(categories, ["Legacy category"])
        self.assertEqual(self.store.all()[0]["is_favorite"], 1)

    def test_interrupted_json_write_preserves_previous_file(self):
        destination = Path(self.temp.name) / "settings.json"
        destination.write_text("original", encoding="utf-8")
        with patch.object(promptbox.os, "replace", side_effect=OSError("simulated replace failure")):
            with self.assertRaises(OSError):
                promptbox.write_json_atomically(destination, {"theme": "light"})
        self.assertEqual(destination.read_text(encoding="utf-8"), "original")
        self.assertEqual(list(Path(self.temp.name).glob(".settings.json.*.tmp")), [])

    def test_settings_are_sanitized_and_custom_categories_persist(self):
        settings_path = Path(self.temp.name) / "settings.json"
        promptbox.write_json_atomically(settings_path, {
            "theme": ["light"],
            "confirm_delete": "false",
            "custom_categories": ["Ideas", " ideas ", ""],
            "hidden_categories": ["TRABAJO", "GENERAL", "not a default"],
        })
        settings = promptbox.load_settings(settings_path)
        self.assertEqual(settings["theme"], "dark")
        self.assertIs(settings["confirm_delete"], True)
        self.assertEqual(settings["custom_categories"], ["Ideas"])
        self.assertEqual(settings["hidden_categories"], ["Trabajo"])
        promptbox.write_json_atomically(settings_path, settings)
        self.assertEqual(promptbox.load_settings(settings_path), settings)

    def test_corrupted_settings_use_safe_defaults(self):
        settings_path = Path(self.temp.name) / "corrupt-settings.json"
        settings_path.write_text("[invalid settings shape]", encoding="utf-8")
        settings = promptbox.load_settings(settings_path)
        self.assertEqual(settings["theme"], "dark")
        self.assertIs(settings["confirm_delete"], True)
        self.assertEqual(settings["custom_categories"], [])
        self.assertEqual(settings["hidden_categories"], [])

    def test_legacy_database_migrates_without_losing_rows(self):
        self.store.conn.close()
        self.db_path.unlink()
        import sqlite3
        connection = sqlite3.connect(self.db_path)
        connection.execute("""CREATE TABLE prompts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL, content TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'General',
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""")
        connection.execute(
            "INSERT INTO prompts(title, content, category, created_at, updated_at) VALUES(?,?,?,?,?)",
            ("Legacy", "Old content", "General", "2025-01-01", "2025-01-01")
        )
        connection.commit()
        connection.close()
        self.store = promptbox.PromptStore()
        row = self.store.all()[0]
        self.assertEqual(row["title"], "Legacy")
        self.assertEqual(row["is_favorite"], 0)
        self.assertEqual(row["tags"], "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
