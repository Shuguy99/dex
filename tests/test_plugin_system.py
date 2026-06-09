import importlib
import json
from pathlib import Path

import pytest

from core.plugin_system import Plugin, PluginSystem


SAMPLE_PLUGIN_CODE = '''
class SamplePlugin:
    def execute(self, command: str, **kwargs) -> str:
        if command.startswith("hello"):
            return f"Hello, {kwargs.get('name', 'world')}!"
        if command.startswith("echo"):
            return f"Echo: {command}"
        return f"Unknown: {command}"
'''


def make_plugin_dir(tmp_path: Path, name: str = "test_plugin",
                    commands: dict | None = None) -> Path:
    pdir = tmp_path / "plugins"
    pdir.mkdir(exist_ok=True)
    py_file = pdir / f"{name}.py"
    py_file.write_text(SAMPLE_PLUGIN_CODE, encoding="utf-8")
    if commands is not None:
        manifest = {
            "name": name,
            "version": "1.0.0",
            "description": "Test plugin",
            "commands": commands
        }
        json_file = pdir / "plugin.json"
        json_file.write_text(json.dumps(manifest), encoding="utf-8")
    return pdir


class TestPlugin:
    def test_create(self) -> None:
        p = Plugin("p1", "1.0", "desc", "/dev/null", {"cmd1": "does x"})
        assert p.name == "p1"
        assert p.version == "1.0"
        assert p.description == "desc"
        assert p.commands == {"cmd1": "does x"}
        assert p.enabled is True
        assert p._module is None
        assert p._instance is None

    def test_create_default_commands(self) -> None:
        p = Plugin("p1", "1.0", "desc", "/dev/null")
        assert p.commands == {}

    def test_load_with_real_file(self, tmp_path: Path) -> None:
        py_file = tmp_path / "plugin.py"
        py_file.write_text(SAMPLE_PLUGIN_CODE, encoding="utf-8")
        p = Plugin("test", "1.0", "desc", str(py_file))
        ok = p.load()
        assert ok is True
        assert p._instance is not None
        result = p.execute("hello world")
        assert "Hello" in result

    def test_load_file_not_found(self) -> None:
        p = Plugin("noexist", "1.0", "desc", "/nonexistent/plugin.py")
        ok = p.load()
        assert ok is False
        assert p._instance is None

    def test_execute_no_instance(self) -> None:
        p = Plugin("p1", "1.0", "desc", "/dev/null")
        assert p.execute("cmd") == "Plugin not loaded"

    def test_execute_with_real_plugin(self, tmp_path: Path) -> None:
        py_file = tmp_path / "plugin.py"
        py_file.write_text(SAMPLE_PLUGIN_CODE, encoding="utf-8")
        p = Plugin("test", "1.0", "desc", str(py_file))
        p.load()
        result = p.execute("echo test123")
        assert result == "Echo: echo test123"
        result = p.execute("hello world")
        assert result == "Hello, world!"


class TestPluginSystem:
    def test_create(self, tmp_path: Path) -> None:
        ps = PluginSystem(tmp_path / "plugins")
        assert ps._plugins == {}
        assert ps._plugins_dir.exists()

    def test_discover_by_py_file(self, tmp_path: Path) -> None:
        pdir = tmp_path / "plugins"
        pdir.mkdir()
        (pdir / "mypyplugin.py").write_text(SAMPLE_PLUGIN_CODE, encoding="utf-8")
        ps = PluginSystem(str(pdir))
        ps.discover()
        assert "mypyplugin" in ps._plugins
        p = ps._plugins["mypyplugin"]
        assert p.name == "mypyplugin"
        assert p.version == "0.1.0"

    def test_discover_by_json(self, tmp_path: Path) -> None:
        pdir = tmp_path / "plugins"
        pdir.mkdir()
        py_file = pdir / "greeter.py"
        py_file.write_text(SAMPLE_PLUGIN_CODE, encoding="utf-8")
        manifest = {
            "name": "greeter",
            "version": "2.0.0",
            "description": "A greeter plugin",
            "entry": "greeter.py",
            "commands": {"hello": "Say hello"}
        }
        (pdir / "plugin.json").write_text(json.dumps(manifest), encoding="utf-8")
        ps = PluginSystem(str(pdir))
        ps.discover()
        assert "greeter" in ps._plugins
        p = ps._plugins["greeter"]
        assert p.version == "2.0.0"
        assert p.description == "A greeter plugin"
        assert p.commands == {"hello": "Say hello"}

    def test_load_plugin(self, tmp_path: Path) -> None:
        pdir = make_plugin_dir(tmp_path)
        ps = PluginSystem(str(pdir))
        ps.discover()
        ok = ps.load_plugin("test_plugin")
        assert ok is True
        p = ps.get_plugin("test_plugin")
        assert p is not None
        assert p._instance is not None

    def test_load_plugin_not_found(self) -> None:
        ps = PluginSystem("/nonexistent")
        ok = ps.load_plugin("nope")
        assert ok is False

    def test_load_all(self, tmp_path: Path) -> None:
        pdir = make_plugin_dir(tmp_path, "p1")
        py2 = pdir / "p2.py"
        py2.write_text(SAMPLE_PLUGIN_CODE, encoding="utf-8")
        ps = PluginSystem(str(pdir))
        ps.discover()
        ps.load_all()
        assert ps.get_plugin("p1") is not None
        assert ps.get_plugin("p1")._instance is not None
        assert ps.get_plugin("p2") is not None
        assert ps.get_plugin("p2")._instance is not None

    def test_execute(self, tmp_path: Path) -> None:
        pdir = make_plugin_dir(tmp_path, "echo_plugin",
                               commands={"echo": "Echo back"})
        ps = PluginSystem(str(pdir))
        ps.discover()
        ps.load_all()
        result = ps.execute("echo hello world")
        assert result is not None
        assert "Echo: echo hello world" in result

    def test_execute_disabled_plugin(self, tmp_path: Path) -> None:
        pdir = make_plugin_dir(tmp_path, "echo_plugin",
                               commands={"echo": "Echo back"})
        ps = PluginSystem(str(pdir))
        ps.discover()
        ps.load_all()
        ps.disable_plugin("echo_plugin")
        result = ps.execute("echo hello")
        assert result is None

    def test_execute_no_match(self, tmp_path: Path) -> None:
        pdir = make_plugin_dir(tmp_path, "echo_plugin",
                               commands={"echo": "Echo back"})
        ps = PluginSystem(str(pdir))
        ps.discover()
        ps.load_all()
        result = ps.execute("nonexistent cmd")
        assert result is None

    def test_execute_not_loaded(self, tmp_path: Path) -> None:
        pdir = make_plugin_dir(tmp_path, "echo_plugin",
                               commands={"echo": "Echo back"})
        ps = PluginSystem(str(pdir))
        ps.discover()
        result = ps.execute("echo hello")
        assert result is None

    def test_get_plugin(self, tmp_path: Path) -> None:
        pdir = make_plugin_dir(tmp_path)
        ps = PluginSystem(str(pdir))
        ps.discover()
        p = ps.get_plugin("test_plugin")
        assert p is not None
        assert p.name == "test_plugin"
        assert ps.get_plugin("nonexistent") is None

    def test_list_plugins(self, tmp_path: Path) -> None:
        pdir = make_plugin_dir(tmp_path, commands={"cmd": "do"})
        ps = PluginSystem(str(pdir))
        ps.discover()
        result = ps.list_plugins()
        assert len(result) == 1
        entry = result[0]
        assert entry["name"] == "test_plugin"
        assert entry["version"] == "1.0.0"
        assert entry["enabled"] is True
        assert entry["loaded"] is False

    def test_list_plugins_after_load(self, tmp_path: Path) -> None:
        pdir = make_plugin_dir(tmp_path)
        ps = PluginSystem(str(pdir))
        ps.discover()
        ps.load_all()
        result = ps.list_plugins()
        assert result[0]["loaded"] is True

    def test_enable_plugin(self, tmp_path: Path) -> None:
        pdir = make_plugin_dir(tmp_path)
        ps = PluginSystem(str(pdir))
        ps.discover()
        ps.disable_plugin("test_plugin")
        assert ps.get_plugin("test_plugin").enabled is False
        ok = ps.enable_plugin("test_plugin")
        assert ok is True
        assert ps.get_plugin("test_plugin").enabled is True

    def test_enable_plugin_not_found(self) -> None:
        ps = PluginSystem("/nonexistent")
        ok = ps.enable_plugin("nope")
        assert ok is False

    def test_disable_plugin(self, tmp_path: Path) -> None:
        pdir = make_plugin_dir(tmp_path)
        ps = PluginSystem(str(pdir))
        ps.discover()
        ok = ps.disable_plugin("test_plugin")
        assert ok is True
        assert ps.get_plugin("test_plugin").enabled is False

    def test_disable_plugin_not_found(self) -> None:
        ps = PluginSystem("/nonexistent")
        ok = ps.disable_plugin("nope")
        assert ok is False

    def test_get_command_prefixes(self, tmp_path: Path) -> None:
        pdir = tmp_path / "plugins"
        pdir.mkdir()
        # Plugin 1 in subdir
        p1 = pdir / "p1"
        p1.mkdir()
        (p1 / "plugin.py").write_text(SAMPLE_PLUGIN_CODE, encoding="utf-8")
        (p1 / "plugin.json").write_text(json.dumps({
            "name": "p1", "version": "1.0", "description": "",
            "entry": "plugin.py",
            "commands": {"hello": "Say hi", "greet": "Greet"}
        }), encoding="utf-8")
        # Plugin 2 in subdir
        p2 = pdir / "p2"
        p2.mkdir()
        (p2 / "plugin.py").write_text(SAMPLE_PLUGIN_CODE, encoding="utf-8")
        (p2 / "plugin.json").write_text(json.dumps({
            "name": "p2", "version": "1.0", "description": "",
            "entry": "plugin.py",
            "commands": {"echo": "Echo"}
        }), encoding="utf-8")
        ps = PluginSystem(str(pdir))
        ps.discover()
        prefixes = ps.get_command_prefixes()
        assert prefixes == {"hello": "p1", "greet": "p1", "echo": "p2"}

    def test_get_command_prefixes_disabled(self, tmp_path: Path) -> None:
        pdir = make_plugin_dir(tmp_path, "p1", commands={"hello": "Hi"})
        ps = PluginSystem(str(pdir))
        ps.discover()
        ps.disable_plugin("p1")
        prefixes = ps.get_command_prefixes()
        assert prefixes == {}

    def test_empty_plugins_dir(self, tmp_path: Path) -> None:
        ps = PluginSystem(str(tmp_path / "empty"))
        ps.discover()
        assert ps.list_plugins() == []

    def test_pyi_not_imported(self, tmp_path: Path) -> None:
        pdir = tmp_path / "plugins"
        pdir.mkdir()
        (pdir / "mymod.pyi").write_text("", encoding="utf-8")
        ps = PluginSystem(str(pdir))
        ps.discover()
        assert ps.list_plugins() == []

    def test_re_discover_preserves_enable_state(self, tmp_path: Path) -> None:
        pdir = make_plugin_dir(tmp_path, "p1", commands={"cmd": "do"})
        ps = PluginSystem(str(pdir))
        ps.discover()
        ps.disable_plugin("p1")
        ps.discover()
        p = ps.get_plugin("p1")
        assert p is not None
        assert p.enabled is True

    def test_plugin_execute_kwargs(self, tmp_path: Path) -> None:
        code = '''
class KwargPlugin:
    def execute(self, command: str, **kwargs) -> str:
        return f"got {len(kwargs)} kwargs"
'''
        pdir = tmp_path / "plugins"
        pdir.mkdir()
        py_file = pdir / "kwarg_plugin.py"
        py_file.write_text(code, encoding="utf-8")
        (pdir / "plugin.json").write_text(json.dumps({
            "name": "kwarg_plugin", "version": "1.0", "description": "",
            "entry": "kwarg_plugin.py",
            "commands": {"cmd": "test"}
        }), encoding="utf-8")
        ps = PluginSystem(str(pdir))
        ps.discover()
        ps.load_all()
        result = ps.execute("cmd", extra="val", num=42)
        assert result == "got 2 kwargs"


class TestPluginAssistantIntegration:
    """Test that plugin commands bridge correctly into DexAssistant."""

    def test_plugin_handler_registration(self, tmp_path: Path, monkeypatch) -> None:
        make_plugin_dir(tmp_path, "greeter",
                        commands={"hello": "Say hello",
                                  "greet": "Say greet"})
        monkeypatch.setattr("config.CONFIG.DATA_DIR", tmp_path)
        from core.assistant import DexAssistant
        assistant = DexAssistant()
        assistant.initialize()
        assert "hello" in assistant._command_handlers
        assert "greet" in assistant._command_handlers
        result = assistant._command_handlers["hello"]("world")
        assert "Hello" in result

    def test_plugin_does_not_override_builtin(self, tmp_path: Path,
                                               monkeypatch) -> None:
        make_plugin_dir(tmp_path, "evil",
                        commands={"статус": "Override status"})
        monkeypatch.setattr("config.CONFIG.DATA_DIR", tmp_path)
        from core.assistant import DexAssistant
        assistant = DexAssistant()
        assistant.initialize()
        result = assistant._command_handlers["статус"]("")
        assert "Override" not in result
        assert "Статус системы" in result

    def test_plugin_command_prefixes_from_assistant(self, tmp_path: Path,
                                                    monkeypatch) -> None:
        make_plugin_dir(tmp_path, "mover",
                        commands={"move": "Move files"})
        monkeypatch.setattr("config.CONFIG.DATA_DIR", tmp_path)
        from core.assistant import DexAssistant
        assistant = DexAssistant()
        assistant.initialize()
        prefixes = assistant.plugins.get_command_prefixes()
        assert "move" in prefixes

    def test_plugin_list_command(self, tmp_path: Path, monkeypatch) -> None:
        make_plugin_dir(tmp_path, "mover",
                        commands={"move": "Move files"})
        monkeypatch.setattr("config.CONFIG.DATA_DIR", tmp_path)
        from core.assistant import DexAssistant
        assistant = DexAssistant()
        assistant.initialize()
        result = assistant._cmd_plugin("list")
        assert "mover" in result
        assert "1.0.0" in result

    def test_plugin_enable_disable(self, tmp_path: Path, monkeypatch) -> None:
        make_plugin_dir(tmp_path, "mover",
                        commands={"move": "Move files"})
        monkeypatch.setattr("config.CONFIG.DATA_DIR", tmp_path)
        from core.assistant import DexAssistant
        assistant = DexAssistant()
        assistant.initialize()
        result = assistant._cmd_plugin("disable mover")
        assert "отключён" in result
        result = assistant._cmd_plugin("enable mover")
        assert "включён" in result
        result = assistant._cmd_plugin("info mover")
        assert "mover" in result
        assert "1.0.0" in result

    def test_plugin_info_not_found(self, tmp_path: Path, monkeypatch) -> None:
        make_plugin_dir(tmp_path, "mover",
                        commands={"move": "Move files"})
        monkeypatch.setattr("config.CONFIG.DATA_DIR", tmp_path)
        from core.assistant import DexAssistant
        assistant = DexAssistant()
        assistant.initialize()
        result = assistant._cmd_plugin("info nonexistent")
        assert "не найден" in result
