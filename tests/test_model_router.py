import os
import sys
import unittest
from pathlib import Path

os.environ["DEX_SKIP_LLM"] = "1"
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.model_router import PURPOSES, ModelRouter


class FakeLLM:
    ready = True
    models = ["qwen2.5:14b", "llama3.2:3b"]
    last_model = None

    def generate(self, prompt, model=None, **kwargs):
        self.last_model = model
        return f"response to: {prompt[:20]}"

    def generate_structured(self, prompt, schema, model=None, **kwargs):
        self.last_model = model
        return {"result": "ok"}


class TestModelRouter(unittest.TestCase):
    def setUp(self):
        self.llm = FakeLLM()
        self.router = ModelRouter(self.llm, {
            "chat": "qwen2.5:14b",
            "code": "deepseek-coder-v2",
        })

    def test_purposes_list(self):
        self.assertIn("chat", PURPOSES)
        self.assertIn("code", PURPOSES)
        self.assertIn("rag", PURPOSES)
        self.assertEqual(len(PURPOSES), 12)

    def test_get_model(self):
        self.assertEqual(self.router.get_model("chat"), "qwen2.5:14b")
        self.assertEqual(self.router.get_model("code"), "deepseek-coder-v2")
        self.assertIsNone(self.router.get_model("rag"))

    def test_set_purpose_model(self):
        self.router.set_purpose_model("rag", "llama3.2:3b")
        self.assertEqual(self.router.get_model("rag"), "llama3.2:3b")

    def test_generate_routes(self):
        self.router.generate("hello", purpose="chat")
        self.assertEqual(self.llm.last_model, "qwen2.5:14b")

    def test_generate_no_purpose(self):
        self.router.generate("hello")
        self.assertIsNone(self.llm.last_model)

    def test_generate_structured_routes(self):
        self.router.generate_structured("hello", {}, purpose="code")
        self.assertEqual(self.llm.last_model, "deepseek-coder-v2")

    def test_purpose_map_property(self):
        pm = self.router.purpose_map
        self.assertEqual(pm["chat"], "qwen2.5:14b")
        self.assertEqual(pm["code"], "deepseek-coder-v2")

    def test_is_ready(self):
        self.assertTrue(self.router.is_ready)


if __name__ == "__main__":
    unittest.main()
