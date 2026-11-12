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

    def test_export_import_round_trip(self):
        self.store.save("Résumé", "Keep accents ✓", "Personal", "important", True)
        backup = Path(self.temp.name) / "backup.json"
        self.store.export_data(backup)
        target_dir = Path(self.temp.name) / "target"
        target_db = target_dir / "prompts.db"
        with patch.object(promptbox, "DATA_DIR", target_dir), patch.object(promptbox, "DB_PATH", target_db):
            target = promptbox.PromptStore()
        try:
            count = target.import_data(backup)
            self.assertEqual(count, 1)
            imported = target.all()[0]
            self.assertEqual(imported["title"], "Résumé")
            self.assertEqual(imported["content"], "Keep accents ✓")
            self.assertEqual(imported["tags"], "important")
            self.assertEqual(imported["is_favorite"], 1)
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
