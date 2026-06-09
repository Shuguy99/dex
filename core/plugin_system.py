import importlib
import inspect
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.plugins")


class Plugin:
    def __init__(self, name: str, version: str, description: str,
                 module_path: str, commands: dict[str, str] | None = None,
                 sandbox: Any = None) -> None:
        self.name = name
        self.version = version
        self.description = description
        self.module_path = module_path
        self.commands = commands or {}
        self._module = None
        self._instance = None
        self.enabled = True
        self._sandbox = sandbox

    def load(self) -> bool:
        if self._sandbox is not None:
            try:
                self._sandbox.check_read(self.module_path)
            except PermissionError:
                logger.warning(f"Plugin load blocked by sandbox: {self.module_path}")
                return False
        try:
            spec = importlib.util.spec_from_file_location(self.name, self.module_path)  # type: ignore[attr-defined]
            if spec and spec.loader:
                self._module = importlib.util.module_from_spec(spec)  # type: ignore[attr-defined]
                spec.loader.exec_module(self._module)
                for _name, obj in inspect.getmembers(self._module):
                    if inspect.isclass(obj) and hasattr(obj, "execute"):
                        self._instance = obj()
                        break
                logger.info(f"Plugin loaded: {self.name} v{self.version}")
                return True
        except Exception as e:
            logger.error(f"Failed to load plugin {self.name}: {e}")
        return False

    def execute(self, command: str, **kwargs) -> str:
        if not self._instance:
            return "Plugin not loaded"
        if hasattr(self._instance, "execute"):
            return self._instance.execute(command, **kwargs)
        return "No execute method"


class PluginSystem:
    def __init__(self, plugins_dir: str | Path, sandbox: Any = None) -> None:
        self._plugins_dir = Path(plugins_dir)
        self._plugins_dir.mkdir(parents=True, exist_ok=True)
        self._plugins: dict[str, Plugin] = {}
        self._manifest_path = self._plugins_dir / "manifest.json"
        self._sandbox = sandbox

    def discover(self) -> None:
        for f_path in self._plugins_dir.rglob("*.py"):
            if f_path.name == "__init__.py":
                continue
            manifest = self._load_manifest(f_path)
            if manifest:
                plugin = Plugin(
                    name=manifest.get("name", f_path.stem),
                    version=manifest.get("version", "0.1.0"),
                    description=manifest.get("description", ""),
                    module_path=str(f_path),
                    commands=manifest.get("commands", {}),
                    sandbox=self._sandbox
                )
            else:
                plugin = Plugin(
                    name=f_path.stem,
                    version="0.1.0",
                    description="",
                    module_path=str(f_path),
                    commands={},
                    sandbox=self._sandbox
                )
            self._plugins[plugin.name] = plugin

        for f_path in self._plugins_dir.rglob("plugin.json"):
            manifest = json.loads(f_path.read_text(encoding="utf-8"))
            py_path = f_path.parent / manifest.get("entry", f_path.stem + ".py")
            if py_path.exists():
                plugin = Plugin(
                    name=manifest.get("name", f_path.parent.name),
                    version=manifest.get("version", "0.1.0"),
                    description=manifest.get("description", ""),
                    module_path=str(py_path),
                    commands=manifest.get("commands", {}),
                    sandbox=self._sandbox
                )
                self._plugins[plugin.name] = plugin

        logger.info(f"Discovered {len(self._plugins)} plugins")

    def _load_manifest(self, py_path: Path) -> dict[str, Any] | None:
        plugin_json = py_path.parent / "plugin.json"
        if plugin_json.exists():
            return json.loads(plugin_json.read_text(encoding="utf-8"))
        return None

    def load_plugin(self, name: str) -> bool:
        if name in self._plugins:
            return self._plugins[name].load()
        return False

    def load_all(self) -> None:
        for name in self._plugins:
            self._plugins[name].load()

    def execute(self, command: str, **kwargs) -> str | None:
        for _name, plugin in self._plugins.items():
            if not plugin.enabled or not plugin._instance:
                continue
            for cmd_prefix in plugin.commands:
                if command.startswith(cmd_prefix):
                    return plugin.execute(command, **kwargs)
        return None

    def get_plugin(self, name: str) -> Plugin | None:
        return self._plugins.get(name)

    def enable_plugin(self, name: str) -> bool:
        plugin = self._plugins.get(name)
        if plugin:
            plugin.enabled = True
            logger.info(f"Plugin enabled: {name}")
            return True
        return False

    def disable_plugin(self, name: str) -> bool:
        plugin = self._plugins.get(name)
        if plugin:
            plugin.enabled = False
            logger.info(f"Plugin disabled: {name}")
            return True
        return False

    def get_command_prefixes(self) -> dict[str, str]:
        prefixes: dict[str, str] = {}
        for plugin in self._plugins.values():
            if plugin.enabled:
                for cmd in plugin.commands:
                    prefixes[cmd] = plugin.name
        return prefixes

    def list_plugins(self) -> list[dict[str, Any]]:
        return [
            {
                "name": p.name,
                "version": p.version,
                "description": p.description,
                "enabled": p.enabled,
                "loaded": p._instance is not None
            }
            for p in self._plugins.values()
        ]
