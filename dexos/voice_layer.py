import logging
import subprocess
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.dexos.voice_layer")


APP_CONTEXT_MAP = {
    "chrome": {"keys": {"new_tab": "ctrl+t", "close_tab": "ctrl+w",
                         "address_bar": "ctrl+l", "find": "ctrl+f"},
                "type": "browser"},
    "notepad": {"keys": {"save": "ctrl+s", "new": "ctrl+n", "find": "ctrl+f"},
                "type": "editor"},
    "explorer": {"keys": {"new_folder": "ctrl+shift+n", "address_bar": "ctrl+l"},
                 "type": "file_manager"},
}


class VoiceLayer:
    def __init__(self, app_launcher=None) -> None:
        self._app_launcher = app_launcher
        self._active_app = None
        self._context_map: dict[str, Any] = APP_CONTEXT_MAP
        self._macro_history: list[dict[str, Any]] = []

    def focus_app(self, app_name: str) -> bool:
        if self._app_launcher:
            return self._app_launcher.launch(app_name)
        try:
            subprocess.run(["start", app_name], shell=True, capture_output=True, timeout=5)
            time.sleep(0.5)
            return True
        except Exception:
            return False

    def send_keys(self, keys: str) -> None:
        try:
            import platform
            if platform.system() == "Windows":
                script = f'''
                set WshShell = CreateObject("WScript.Shell")
                WshShell.SendKeys "{keys}"
                '''
                with open("_sendkeys.vbs", "w") as f:
                    f.write(script)
                subprocess.run(["cscript", "//nologo", "_sendkeys.vbs"],
                               capture_output=True, timeout=5)
                Path("_sendkeys.vbs").unlink(missing_ok=True)
            else:
                subprocess.run(["xdotool", "type", keys],
                               capture_output=True, timeout=5)
        except Exception as e:
            logger.warning(f"send_keys failed: {e}")

    def execute_window_command(self, app_name: str, command: str) -> str:
        app_name_lower = app_name.lower().strip()
        command_lower = command.lower().strip()

        for known_app, ctx in self._context_map.items():
            if known_app in app_name_lower or app_name_lower in known_app:
                key_action = ctx["keys"].get(command_lower)
                if key_action:
                    self.focus_app(known_app)
                    self.send_keys(key_action)
                    self._macro_history.append({
                        "app": known_app, "command": command,
                        "keys": key_action, "timestamp": time.time()
                    })
                    return f"Выполнено: {command} → {known_app} ({key_action})"

        if self._llm_available():
            return self._llm_translate(app_name, command)

        return f"Неизвестное приложение или команда: {app_name} / {command}"

    def _llm_available(self) -> bool:
        try:
            from core.llm import OllamaClient
            return True
        except ImportError:
            return False

    def _llm_translate(self, app_name: str, command: str) -> str:
        try:
            from core.llm import OllamaClient
            llm = OllamaClient()
            if llm.ready:
                prompt = (
                    f"App: '{app_name}', Command: '{command}'\n"
                    f"Suggest a keyboard shortcut for this action in this app. "
                    f"Respond as JSON: {{\"keys\": str, \"explanation\": str}}"
                )
                result = llm.generate_structured(prompt, {
                    "type": "object",
                    "properties": {
                        "keys": {"type": "string"},
                        "explanation": {"type": "string"}
                    }
                })
                if result and result.get("keys"):
                    self.send_keys(result["keys"])
                    return f"LLM: {result['keys']} ({result.get('explanation', '')})"
        except Exception:
            pass
        return "Не удалось определить команду"

    def get_layer_summary(self) -> str:
        lines = ["── Voice Layer ──"]
        for app, ctx in self._context_map.items():
            cmds = ", ".join(f"{k}" for k in ctx["keys"][:3])
            lines.append(f"  {app}: {cmds}...")
        lines.append(f"\nRecent macros: {len(self._macro_history)}")
        return "\n".join(lines)
