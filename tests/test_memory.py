import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from memory.encryptor import SecureMemory
from memory.validator import MemoryValidator


class TestSecureMemory(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = str(Path(self.tmpdir) / "test_secure.db")
        self.memory = SecureMemory(self.db_path, key="test-key-12345")

    def test_initialize(self):
        self.memory.initialize()
        self.assertTrue(self.memory.ready)

    def test_store_and_retrieve(self):
        self.memory.initialize()
        self.memory.store("credentials", "test_key", "test_value")
        value = self.memory.retrieve("test_key")
        self.assertEqual(value, "test_value")

    def test_delete(self):
        self.memory.initialize()
        self.memory.store("test", "del_key", "del_value")
        self.memory.delete("del_key")
        value = self.memory.retrieve("del_key")
        self.assertIsNone(value)

    def test_sensitive_detection(self):
        self.assertTrue(SecureMemory.is_sensitive("мой пароль 12345"))
        self.assertTrue(SecureMemory.is_sensitive("credit card number"))
        self.assertFalse(SecureMemory.is_sensitive("погода сегодня хорошая"))


class TestMemoryValidator(unittest.TestCase):
    def test_no_conflict(self):
        validator = MemoryValidator()
        self.assertTrue(validator.validate_new_fact("сегодня хорошая погода"))

    def test_sensitive_detection(self):
        validator = MemoryValidator()
        self.assertTrue(validator.requires_confirmation("мой пароль секрет"))
        self.assertFalse(validator.requires_confirmation("сегодня вторник"))


if __name__ == "__main__":
    unittest.main()
