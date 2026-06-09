import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.base_llm_module import BaseLLMModule


class ConcreteModule(BaseLLMModule):
    def __init__(self, llm_client=None, data_dir=None, filename="data.json"):
        self._filename = filename
        super().__init__(llm_client, data_dir)

    @property
    def _data_path(self) -> Path:
        return self._data_dir / self._filename

    def get_summary(self) -> str:
        return "Test summary from concrete module"


class TestBaseLLMModule(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_cannot_instantiate_abstract(self):
        with self.assertRaises(TypeError):
            BaseLLMModule()

    def test_concrete_instantiation(self):
        mod = ConcreteModule(data_dir=str(self.tmpdir))
        self.assertIsNotNone(mod)
        self.assertEqual(mod.get_summary(), "Test summary from concrete module")

    def test_save_and_load(self):
        mod = ConcreteModule(data_dir=str(self.tmpdir))
        data = {"key": "value", "number": 42}
        mod._save(data)
        loaded = mod._load()
        self.assertEqual(loaded, data)

    def test_load_empty_when_no_file(self):
        mod = ConcreteModule(data_dir=str(self.tmpdir))
        loaded = mod._load()
        self.assertEqual(loaded, {})

    def test_load_corrupt_json(self):
        mod = ConcreteModule(data_dir=str(self.tmpdir))
        mod._data_path.write_text("not valid json", encoding="utf-8")
        loaded = mod._load()
        self.assertEqual(loaded, {})

    def test_data_dir_created(self):
        subdir = self.tmpdir / "nested" / "subdir"
        ConcreteModule(data_dir=str(subdir))
        self.assertTrue(subdir.exists())
        self.assertTrue(subdir.is_dir())

    def test_generate_llm_no_client(self):
        mod = ConcreteModule(data_dir=str(self.tmpdir), llm_client=None)
        result = mod.generate_llm("hello")
        self.assertIsNone(result)

    def test_generate_llm_without_schema(self):
        mock_llm = MagicMock()
        mock_llm.generate.return_value = "generated text"
        mod = ConcreteModule(data_dir=str(self.tmpdir), llm_client=mock_llm)
        result = mod.generate_llm("hello")
        self.assertEqual(result, "generated text")
        mock_llm.generate.assert_called_once_with("hello")

    def test_generate_llm_with_schema(self):
        mock_llm = MagicMock()
        mock_llm.generate_structured.return_value = {"result": "parsed"}
        mod = ConcreteModule(data_dir=str(self.tmpdir), llm_client=mock_llm)
        schema = {"type": "object", "properties": {"result": {"type": "string"}}}
        result = mod.generate_llm("parse this", schema=schema)
        self.assertEqual(result, {"result": "parsed"})
        mock_llm.generate_structured.assert_called_once_with("parse this", schema)

    def test_save_ensure_ascii_false(self):
        mod = ConcreteModule(data_dir=str(self.tmpdir))
        data = {"text": "привет мир"}
        mod._save(data)
        content = mod._data_path.read_text(encoding="utf-8")
        self.assertIn("привет", content)

    def test_save_indent(self):
        mod = ConcreteModule(data_dir=str(self.tmpdir))
        data = {"a": 1}
        mod._save(data)
        content = mod._data_path.read_text(encoding="utf-8")
        self.assertIn('  "a"', content)

    def test_default_data_dir(self):
        mod = ConcreteModule()
        expected = Path("data/base_llm_module")
        self.assertEqual(mod._data_dir, expected)

    def test_custom_filename(self):
        mod = ConcreteModule(data_dir=str(self.tmpdir), filename="custom.json")
        self.assertEqual(mod._data_path.name, "custom.json")
        mod._save({"x": 1})
        loaded = mod._load()
        self.assertEqual(loaded, {"x": 1})


if __name__ == "__main__":
    unittest.main()
