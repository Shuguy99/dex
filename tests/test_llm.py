import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ["DEX_SKIP_LLM"] = "1"

from core.llm import OllamaClient


class TestOllamaClient(unittest.TestCase):
    def setUp(self):
        self.client = OllamaClient(base_url="http://test:11434")

    @patch.dict(os.environ, {"DEX_SKIP_LLM": "1"})
    def test_check_available_skip_llm(self):
        result = self.client.check_available(timeout=1)
        self.assertFalse(result)

    @patch.dict(os.environ, {}, clear=True)
    @patch("core.llm.subprocess.run")
    def test_check_available_cli_success(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="NAME\tID\nqwen2.5:14b\tabc123\nllava:13b\tdef456\n",
            stderr=""
        )
        os.environ.pop("DEX_SKIP_LLM", None)
        result = self.client.check_available(timeout=1)
        self.assertTrue(result)
        self.assertIn("qwen2.5:14b", self.client._available_models)

    @patch.dict(os.environ, {}, clear=True)
    @patch("core.llm.subprocess.run")
    def test_check_available_cli_no_models(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="NAME\tID\n", stderr="")
        os.environ.pop("DEX_SKIP_LLM", None)
        result = self.client.check_available(timeout=1)
        self.assertFalse(result)

    @patch.dict(os.environ, {}, clear=True)
    @patch("core.llm.subprocess.run")
    def test_check_available_cli_fail(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        os.environ.pop("DEX_SKIP_LLM", None)
        result = self.client.check_available(timeout=1)
        self.assertFalse(result)

    @patch.dict(os.environ, {}, clear=True)
    @patch("core.llm.subprocess.run", side_effect=FileNotFoundError)
    @patch("core.llm.OllamaClient._check_api")
    def test_check_available_cli_not_found(self, mock_check_api, mock_run):
        mock_check_api.return_value = True
        os.environ.pop("DEX_SKIP_LLM", None)
        result = self.client.check_available(timeout=1)
        self.assertTrue(result)

    @patch.dict(os.environ, {}, clear=True)
    @patch("core.llm.subprocess.run", side_effect=subprocess.TimeoutExpired(["ollama"], 1))
    def test_check_available_cli_timeout(self, mock_run):
        os.environ.pop("DEX_SKIP_LLM", None)
        result = self.client.check_available(timeout=1)
        self.assertFalse(result)

    @patch("urllib.request.urlopen")
    def test_check_api_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "models": [{"name": "qwen2.5:14b"}, {"name": "llava:13b"}]
        }).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_resp
        result = self.client._check_api()
        self.assertTrue(result)
        self.assertIn("qwen2.5:14b", self.client._available_models)

    @patch("urllib.request.urlopen", side_effect=Exception("fail"))
    def test_check_api_fail(self, mock_urlopen):
        result = self.client._check_api()
        self.assertFalse(result)

    def test_select_model_preferred_available(self):
        self.client._available_models = ["qwen2.5:14b", "llava:13b"]
        model = self.client.select_model("general")
        self.assertEqual(model, "qwen2.5:14b")

    def test_select_model_preferred_not_available(self):
        self.client._available_models = ["llava:13b"]
        model = self.client.select_model("general")
        self.assertEqual(model, "llava:13b")

    def test_select_model_no_available(self):
        self.client._available_models = []
        model = self.client.select_model("general")
        self.assertEqual(model, "qwen2.5:14b")

    def test_select_model_custom_task(self):
        self.client._available_models = ["deepseek-coder-v2"]
        model = self.client.select_model("code")
        self.assertEqual(model, "deepseek-coder-v2")

    @patch("core.llm.subprocess.run")
    def test_generate_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="Hello!", stderr="")
        result = self.client.generate("test prompt")
        self.assertEqual(result, "Hello!")

    @patch("core.llm.subprocess.run")
    def test_generate_with_system(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="System response", stderr="")
        result = self.client.generate("prompt", system="Be helpful")
        self.assertEqual(result, "System response")

    @patch("core.llm.subprocess.run")
    def test_generate_success_with_custom_model(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="Custom!", stderr="")
        result = self.client.generate("test", model="llava:13b")
        self.assertEqual(result, "Custom!")

    @patch("core.llm.subprocess.run")
    @patch("core.llm.OllamaClient._generate_api")
    def test_generate_cli_fail_fallback_api(self, mock_generate_api, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        mock_generate_api.return_value = "api response"
        result = self.client.generate("test")
        self.assertEqual(result, "api response")

    @patch("core.llm.subprocess.run", side_effect=FileNotFoundError)
    @patch("core.llm.OllamaClient._generate_api")
    def test_generate_cli_not_found_fallback(self, mock_generate_api, mock_run):
        mock_generate_api.return_value = "api fallback"
        result = self.client.generate("test")
        self.assertEqual(result, "api fallback")

    @patch("urllib.request.urlopen")
    def test_generate_api_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"response": "api hello"}).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_resp
        result = self.client._generate_api("prompt", "test-model")
        self.assertEqual(result, "api hello")

    @patch("urllib.request.urlopen", side_effect=Exception("api fail"))
    def test_generate_api_fail(self, mock_urlopen):
        result = self.client._generate_api("prompt", "test-model")
        self.assertEqual(result, "")

    @patch("urllib.request.urlopen")
    def test_chat_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"message": {"content": "chat reply"}}).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_resp
        messages = [{"role": "user", "content": "hello"}]
        result = self.client.chat(messages)
        self.assertEqual(result, "chat reply")

    @patch("urllib.request.urlopen", side_effect=Exception("chat fail"))
    def test_chat_fail(self, mock_urlopen):
        messages = [{"role": "user", "content": "hello"}]
        result = self.client.chat(messages)
        self.assertEqual(result, "")

    @patch("core.llm.OllamaClient.generate")
    def test_generate_structured_success(self, mock_generate):
        mock_generate.return_value = '{"steps": [{"action": "open_file"}]}'
        schema = {"type": "object", "properties": {"steps": {"type": "array"}}}
        result = self.client.generate_structured("do something", schema)
        self.assertEqual(result, {"steps": [{"action": "open_file"}]})

    @patch("core.llm.OllamaClient.generate")
    def test_generate_structured_json_decode_error(self, mock_generate):
        mock_generate.return_value = "not json at all"
        schema = {"type": "object"}
        result = self.client.generate_structured("do something", schema)
        self.assertIsNone(result)

    @patch("core.llm.OllamaClient.generate")
    def test_generate_structured_cleaned(self, mock_generate):
        mock_generate.return_value = "```json\n{\"key\": \"value\"}\n```"
        schema = {"type": "object"}
        result = self.client.generate_structured("do something", schema)
        self.assertEqual(result, {"key": "value"})

    @patch("core.llm.subprocess.run")
    def test_pull_model_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="pulled", stderr="")
        result = self.client.pull_model("qwen2.5:14b")
        self.assertTrue(result)
        self.assertIn("qwen2.5:14b", self.client._available_models)

    @patch("core.llm.subprocess.run")
    def test_pull_model_fail(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="not found")
        result = self.client.pull_model("nonexistent")
        self.assertFalse(result)

    @patch("core.llm.subprocess.run", side_effect=subprocess.TimeoutExpired(["ollama"], 1))
    def test_pull_model_timeout(self, mock_run):
        result = self.client.pull_model("qwen2.5:14b", timeout=1)
        self.assertFalse(result)

    @patch("core.llm.subprocess.run", side_effect=FileNotFoundError)
    def test_pull_model_not_found(self, mock_run):
        result = self.client.pull_model("qwen2.5:14b")
        self.assertFalse(result)

    def test_models_property(self):
        self.client._available_models = ["a", "b"]
        self.assertEqual(self.client.models, ["a", "b"])

    def test_ready_property(self):
        self.client._available_models = ["a"]
        self.assertTrue(self.client.ready)
        self.client._available_models = []
        self.assertFalse(self.client.ready)


if __name__ == "__main__":
    unittest.main()
