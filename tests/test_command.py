import unittest

from core.command import CommandDef, CommandRegistry, parse_args


class TestCommandDef(unittest.TestCase):
    def test_basic(self):
        def handler(args: str) -> str: return "ok"
        cmd = CommandDef(name="test", handler=handler, category="core",
                         description="test cmd", aliases=["t", "test-alias"],
                         natural_prefixes=["тест", "test"])
        self.assertEqual(cmd.name, "test")
        self.assertIn("t", cmd.aliases)

class TestParseArgs(unittest.TestCase):
    def test_empty(self): self.assertEqual(parse_args(""), {})
    def test_positional(self): self.assertEqual(parse_args("foo bar"), {"_positional": ["foo", "bar"]})
    def test_flag(self): self.assertEqual(parse_args("--verbose"), {"verbose": True})
    def test_key_value(self): self.assertEqual(parse_args("--name=dex"), {"name": "dex"})
    def test_key_value_space(self): self.assertEqual(parse_args("--name dex"), {"name": "dex"})
    def test_short_flag(self): self.assertEqual(parse_args("-v"), {"v": True})
    def test_short_value(self): self.assertEqual(parse_args("-n dex"), {"n": "dex"})
    def test_mixed(self):
        r = parse_args("--model qwen --verbose 5 --temp=0.7")
        self.assertEqual(r.get("model"), "qwen")
        self.assertEqual(r.get("verbose"), "5")
        self.assertEqual(r.get("temp"), "0.7")

class TestCommandRegistry(unittest.TestCase):
    def setUp(self):
        self.reg = CommandRegistry()
        self.handler_called: list[str] = []
        def h(args: str) -> str:
            self.handler_called.append(args)
            return f"handled: {args}"
        def h2(args: str) -> str:
            return f"h2: {args}"
        self.h = h
        self.reg.register(CommandDef("greet", h, "core",
                                     description="Say hello",
                                     aliases=["hello"],
                                     natural_prefixes=["привет", "здравствуй"]))
        self.reg.register(CommandDef("bye", h2, "core",
                                     description="Say bye",
                                     natural_prefixes=["пока"]))

    def test_get(self):
        cmd = self.reg.get("greet")
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd.name, "greet")

    def test_get_alias(self):
        cmd = self.reg.get("hello")
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd.name, "greet")

    def test_by_category(self):
        cmds = self.reg.by_category("core")
        self.assertEqual(len(cmds), 2)

    def test_categories(self):
        cats = self.reg.categories()
        self.assertIn("core", cats)
        self.assertEqual(len(cats["core"]), 2)

    def test_generate_help_no_topic(self):
        h = self.reg.generate_help()
        self.assertIn("core", h)

    def test_generate_help_category(self):
        h = self.reg.generate_help("core")
        self.assertIn("greet", h)
        self.assertIn("bye", h)

    def test_generate_help_command(self):
        h = self.reg.generate_help("greet")
        self.assertIn("Say hello", h)
        self.assertIn("greet", h)
        self.assertIn("привет", h)

    def test_generate_help_unknown(self):
        h = self.reg.generate_help("nonexistent")
        self.assertIn("Неизвестная", h)

    def test_parse_structured(self):
        name, args = self.reg.parse_structured("/greet world")
        self.assertEqual(name, "greet")
        self.assertEqual(args, "world")

    def test_parse_structured_alias(self):
        name, args = self.reg.parse_structured("/hello")
        self.assertEqual(name, "greet")

    def test_parse_structured_no_match(self):
        name, args = self.reg.parse_structured("foo bar")
        self.assertIsNone(name)

    def test_match_natural(self):
        name, args = self.reg.match_natural("привет мир")
        self.assertEqual(name, "greet")
        self.assertEqual(args, "мир")

    def test_match_natural_longest_prefix(self):
        self.reg.register(CommandDef("greet-formal", lambda a: "x", "core",
                                     natural_prefixes=["приветствую"]))
        name, args = self.reg.match_natural("приветствую вас")
        self.assertEqual(name, "greet-formal")

    def test_match_natural_no_match(self):
        name, args = self.reg.match_natural("unknown phrase")
        self.assertIsNone(name)

    def test_command_names(self):
        names = self.reg.command_names
        self.assertIn("greet", names)
        self.assertIn("bye", names)

    def test_command_names_no_dupes(self):
        names = self.reg.command_names
        self.assertEqual(len(names), len(set(names)))


if __name__ == "__main__":
    unittest.main()
