import shlex
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CommandDef:
    name: str
    handler: Callable[[str], str]
    category: str = "general"
    description: str = ""
    aliases: list[str] = field(default_factory=list)
    usage: str = ""
    examples: list[str] = field(default_factory=list)
    natural_prefixes: list[str] = field(default_factory=list)


def parse_args(text: str) -> dict[str, Any]:
    args: dict[str, Any] = {}
    positionals: list[str] = []
    parts = shlex.split(text) if text else []
    i = 0
    while i < len(parts):
        part = parts[i]
        if part.startswith("--"):
            key = part[2:]
            if "=" in key:
                k, v = key.split("=", 1)
                args[k] = v
            elif i + 1 < len(parts) and not parts[i + 1].startswith("-"):
                args[key] = parts[i + 1]
                i += 1
            else:
                args[key] = True
        elif part.startswith("-") and len(part) == 2:
            key = part[1]
            if i + 1 < len(parts) and not parts[i + 1].startswith("-"):
                args[key] = parts[i + 1]
                i += 1
            else:
                args[key] = True
        else:
            positionals.append(part)
        i += 1
    if positionals:
        args["_positional"] = positionals
    return args


class CommandRegistry:
    def __init__(self) -> None:
        self._commands: dict[str, CommandDef] = {}
        self._natural_handlers: dict[str, str] = {}
        self._categories: dict[str, list[str]] = {}

    def register(self, cmd: CommandDef) -> None:
        self._commands[cmd.name] = cmd
        for alias in cmd.aliases:
            self._commands[alias] = cmd
        for prefix in cmd.natural_prefixes:
            self._natural_handlers[prefix] = cmd.name
        self._categories.setdefault(cmd.category, []).append(cmd.name)

    def get(self, name: str) -> CommandDef | None:
        return self._commands.get(name)

    def by_category(self, category: str) -> list[CommandDef]:
        names = self._categories.get(category, [])
        seen: set[str] = set()
        result: list[CommandDef] = []
        for n in names:
            if n not in seen:
                cmd = self._commands.get(n)
                if cmd is not None:
                    result.append(cmd)
                    seen.add(n)
        return result

    def categories(self) -> dict[str, list[CommandDef]]:
        result: dict[str, list[CommandDef]] = {}
        for cat in sorted(self._categories):
            result[cat] = self.by_category(cat)
        return result

    def generate_help(self, topic: str = "") -> str:
        if not topic:
            lines = ["Доступные категории команд:\n"]
            for cat, cmds in self.categories().items():
                lines.append(f"  {cat} ({len(cmds)} команд)")
            lines.append("\nНапиши 'help <категория>' для списка команд в категории.")
            lines.append("Напиши 'help <команда>' для подробной информации.")
            lines.append("Используй /команда для структурированного синтаксиса.")
            return "\n".join(lines)

        cats = self.by_category(topic)
        if cats:
            lines = [f"Категория: {topic}\n"]
            for cmd in sorted(cats, key=lambda c: c.name):
                aliases_str = f" ({', '.join(cmd.aliases)})" if cmd.aliases else ""
                lines.append(f"  /{cmd.name}{aliases_str} — {cmd.description}")
            return "\n".join(lines)

        cmd_def = self.get(topic)
        if cmd_def:
            lines = [f"/{cmd_def.name} — {cmd_def.description}"]
            if cmd_def.usage:
                lines.append(f"  Использование: {cmd_def.usage}")
            if cmd_def.aliases:
                lines.append(f"  Синонимы: {', '.join(cmd_def.aliases)}")
            if cmd_def.natural_prefixes:
                lines.append(f"  Естественный язык: {', '.join(cmd_def.natural_prefixes)}")
            if cmd_def.examples:
                lines.append("  Примеры:")
                for ex in cmd_def.examples:
                    lines.append(f"    • {ex}")
            return "\n".join(lines)

        return f"Неизвестная команда или категория: {topic}"

    def parse_structured(self, text: str) -> tuple[str | None, str]:
        text = text.strip()
        if text.startswith("/") or text.startswith("\\"):
            text = text[1:]
        parts = text.split(maxsplit=1)
        if not parts:
            return None, text
        name = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        if name in self._commands:
            return self._commands[name].name, args
        return None, text

    def match_natural(self, text: str) -> tuple[str | None, str]:
        sorted_prefixes = sorted(self._natural_handlers.keys(), key=len, reverse=True)
        for prefix in sorted_prefixes:
            if text.startswith(prefix):
                args = text[len(prefix):].strip()
                return self._natural_handlers[prefix], args
        return None, text

    @property
    def commands(self) -> dict[str, CommandDef]:
        return self._commands

    @property
    def command_names(self) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for cmd in self._commands.values():
            if cmd.name not in seen:
                result.append(cmd.name)
                seen.add(cmd.name)
        return result
