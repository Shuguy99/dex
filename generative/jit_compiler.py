import json
import logging
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.generative.jit")


class JITCompiler:
    def __init__(self, llm_client=None, sandbox=None, plugin_system=None) -> None:
        self._llm = llm_client
        self._sandbox = sandbox
        self._plugin_system = plugin_system
        self._agent_dir = Path("data/jit_agents")
        self._agent_dir.mkdir(parents=True, exist_ok=True)
        self._registry_path = self._agent_dir / "registry.json"
        self._registry: dict[str, dict[str, Any]] = self._load_registry()

    def _load_registry(self) -> dict[str, Any]:
        if self._registry_path.exists():
            try:
                with open(self._registry_path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_registry(self):
        with open(self._registry_path, "w", encoding="utf-8") as f:
            json.dump(self._registry, f, ensure_ascii=False, indent=2)

    def compile_agent(self, description: str) -> dict[str, Any]:
        script = self._generate_script(description)
        if not script:
            return {"success": False, "reason": "Script generation failed"}

        test_result = self._test_script(script, description)
        if not test_result["passed"]:
            for attempt in range(2):
                logger.info(f"Re-generating script (attempt {attempt + 2})...")
                script = self._generate_script(description, error_hint=test_result.get("error", ""))
                if not script:
                    break
                test_result = self._test_script(script, description)
                if test_result["passed"]:
                    break

        agent_id = f"jit_{int(time.time())}"
        agent_path = self._agent_dir / f"{agent_id}.py"
        with open(agent_path, "w", encoding="utf-8") as f:
            f.write(script)

        manifest = {
            "id": agent_id,
            "description": description[:200],
            "path": str(agent_path),
            "created": datetime.now().isoformat(),
            "test_passed": test_result["passed"],
            "test_output": test_result.get("output", "")[:300],
            "invocations": 0
        }
        self._registry[agent_id] = manifest
        self._save_registry()

        if test_result["passed"] and self._plugin_system:
            self._register_as_plugin(agent_id, description, script)

        return {
            "success": test_result["passed"],
            "agent_id": agent_id,
            "path": str(agent_path),
            "test_output": test_result.get("output", "")[:500],
            "error": test_result.get("error", "")
        }

    def _generate_script(self, description: str, error_hint: str = "") -> str | None:
        if self._llm:
            hint = f"\nPrevious error to fix: {error_hint}" if error_hint else ""
            prompt = (
                f"Write a Python script that: {description}\n"
                f"Requirements:\n"
                f"- Define a main() function that returns a result string\n"
                f"- Use only standard library or already imported modules\n"
                f"- Handle errors gracefully\n"
                f"- Be self-contained{hint}\n\n"
                f"Print the script as raw Python code, no markdown fences."
            )
            return self._llm.generate(prompt, temperature=0.2)
        return None

    def _test_script(self, script: str, description: str) -> dict[str, Any]:
        if self._sandbox:
            try:
                result = self._sandbox.run_code(script, timeout=15)
                return {
                    "passed": not result.get("error"),
                    "output": result.get("output", ""),
                    "error": result.get("error", "")
                }
            except Exception as e:
                return {"passed": False, "error": str(e), "output": ""}

        try:
            import tempfile
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py",
                                              delete=False, encoding="utf-8") as f:
                f.write(script)
                f.flush()
                result = subprocess.run(
                    ["python", f.name], capture_output=True, text=True, timeout=15
                )
            os.unlink(f.name)
            return {
                "passed": result.returncode == 0,
                "output": result.stdout[:500],
                "error": result.stderr[:500] if result.returncode != 0 else ""
            }
        except subprocess.TimeoutExpired:
            return {"passed": False, "error": "Timeout", "output": ""}
        except Exception as e:
            return {"passed": False, "error": str(e), "output": ""}

    def _register_as_plugin(self, agent_id: str, description: str, script: str):
        if not self._plugin_system:
            return
        plugin_manifest = {
            "name": f"jit_{agent_id}",
            "version": "1.0.0",
            "description": description,
            "entry": f"data/jit_agents/{agent_id}.py",
            "type": "generated"
        }
        try:
            manifest_path = self._agent_dir / f"{agent_id}_manifest.json"
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(plugin_manifest, f, ensure_ascii=False, indent=2)
            logger.info(f"JIT agent registered as plugin: {agent_id}")
        except Exception as e:
            logger.warning(f"Failed to register JIT agent as plugin: {e}")

    def invoke_agent(self, agent_id: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        manifest = self._registry.get(agent_id)
        if not manifest:
            return {"success": False, "error": f"Agent {agent_id} not found"}

        path = Path(manifest["path"])
        if not path.exists():
            return {"success": False, "error": "Agent file not found"}

        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(agent_id, str(path))
            if not spec or not spec.loader:
                return {"success": False, "error": "Could not load agent module"}
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, "main"):
                result = module.main(**(params or {}))
            elif hasattr(module, "run"):
                result = module.run(**(params or {}))
            else:
                result = "Agent loaded (no main/run function)"

            manifest["invocations"] += 1
            self._save_registry()
            return {"success": True, "result": str(result)[:1000]}
        except Exception as e:
            logger.exception(f"Agent {agent_id} execution failed")
            return {"success": False, "error": str(e)}

    def get_agents_summary(self) -> str:
        if not self._registry:
            return "Нет JIT-агентов."
        lines = ["── JIT Agents ──"]
        for aid, m in sorted(self._registry.items(), key=lambda x: -x[1]["invocations"]):
            status = "✓" if m["test_passed"] else "✗"
            lines.append(f"  {status} {aid[:12]}: {m['description'][:60]}")
            lines.append(f"     invocations: {m['invocations']}, created: {m['created'][:10]}")
        return "\n".join(lines)
