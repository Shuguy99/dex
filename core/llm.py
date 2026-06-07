import json
import logging
import subprocess
from typing import Any

logger = logging.getLogger("dex.llm")

MODEL_ROUTING = {
    "general": "qwen2.5:14b",
    "code": "deepseek-coder-v2",
    "vision": "llava:13b",
    "fast": "qwen2.5:7b",
}


class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434",
                 default_model: str = "qwen2.5:14b") -> None:
        self._base_url = base_url.rstrip("/")
        self._default = default_model
        self._available_models: list[str] = []
        self._cache: dict[str, Any] = {}

    def check_available(self, timeout: int = 3) -> bool:
        import os
        if os.environ.get("DEX_SKIP_LLM") == "1":
            return False
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True, text=True, timeout=timeout
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n")[1:]:
                    if line.strip():
                        self._available_models.append(line.split()[0])
                return len(self._available_models) > 0
            return False
        except FileNotFoundError:
            logger.debug("Ollama CLI not installed")
            return self._check_api()
        except subprocess.TimeoutExpired:
            logger.debug("Ollama list timed out")
            return False

    def _check_api(self) -> bool:
        try:
            import urllib.request
            req = urllib.request.Request(f"{self._base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=2) as resp:
                data = json.loads(resp.read())
                self._available_models = [m["name"] for m in data.get("models", [])]
                return len(self._available_models) > 0
        except Exception as e:
            logger.debug(f"Ollama API unavailable: {e}")
            return False

    def select_model(self, task_type: str = "general") -> str:
        preferred = MODEL_ROUTING.get(task_type, self._default)
        if preferred in self._available_models:
            return preferred
        if self._available_models:
            return self._available_models[0]
        return self._default

    def generate(self, prompt: str, model: str | None = None,
                 system: str | None = None, temperature: float = 0.3,
                 max_tokens: int = 2048) -> str:
        mdl = model or self._default
        try:
            cmd = ["ollama", "run", mdl, prompt]
            if system:
                cmd = ["ollama", "run", mdl, f"{system}\n\n{prompt}"]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120
            )
            if result.returncode == 0:
                return result.stdout.strip()
            logger.error(f"Ollama error: {result.stderr}")
            return self._generate_api(prompt, mdl, system, temperature, max_tokens)
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.warning(f"Ollama CLI failed: {e}, trying API")
            return self._generate_api(prompt, mdl, system, temperature, max_tokens)

    def _generate_api(self, prompt: str, model: str,
                      system: str | None = None, temperature: float = 0.3,
                      max_tokens: int = 2048) -> str:
        try:
            import urllib.request
            payload = {
                "model": model,
                "prompt": prompt,
                "system": system or "",
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False
            }
            req = urllib.request.Request(
                f"{self._base_url}/api/generate",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
                return data.get("response", "")
        except Exception as e:
            logger.error(f"Ollama API generation failed: {e}")
            return ""

    def chat(self, messages: list[dict[str, str]], model: str | None = None,
             temperature: float = 0.3) -> str:
        mdl = model or self._default
        try:
            import urllib.request
            payload = {
                "model": mdl,
                "messages": messages,
                "temperature": temperature,
                "stream": False
            }
            req = urllib.request.Request(
                f"{self._base_url}/api/chat",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
                return data["message"]["content"]
        except Exception as e:
            logger.error(f"Ollama chat failed: {e}")
            return ""

    def generate_structured(self, prompt: str, schema: dict[str, Any],
                            model: str | None = None) -> dict[str, Any] | None:
        system = (
            "You are a precise JSON generator. "
            "Respond ONLY with valid JSON matching the requested schema. "
            "No explanations, no markdown."
        )
        structured_prompt = (
            f"{prompt}\n\n"
            f"Required JSON schema:\n{json.dumps(schema, ensure_ascii=False, indent=2)}\n\n"
            f"Output only JSON:"
        )
        raw = self.generate(structured_prompt, model=model, system=system, temperature=0.1)
        try:
            cleaned = raw.strip().removeprefix("```json").removesuffix("```").strip()
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse structured output: {raw[:200]}")
            return None

    def pull_model(self, model_name: str, timeout: int = 600) -> bool:
        try:
            result = subprocess.run(
                ["ollama", "pull", model_name],
                capture_output=True, text=True, timeout=timeout
            )
            if result.returncode == 0:
                if model_name not in self._available_models:
                    self._available_models.append(model_name)
                return True
            logger.error(f"ollama pull failed: {result.stderr}")
            return False
        except subprocess.TimeoutExpired:
            logger.error(f"ollama pull timed out after {timeout}s")
            return False
        except FileNotFoundError:
            logger.error("ollama CLI not found")
            return False

    @property
    def models(self) -> list[str]:
        return self._available_models

    @property
    def ready(self) -> bool:
        return len(self._available_models) > 0
