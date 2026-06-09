import ast
import json

from multiagent.agent_template import (
    AGENT_MANIFEST_TEMPLATE,
    SUBAGENT_TEMPLATES,
    generate_agent_code,
    generate_agent_manifest,
    validate_agent_code,
)


def test_generate_agent_code_returns_valid_python():
    code = generate_agent_code(
        agent_id="test_agent",
        class_name="TestAgent",
    )
    ast.parse(code)


def test_generate_agent_code_with_minimal_values():
    code = generate_agent_code(
        agent_id="x",
        class_name="X",
    )
    ast.parse(code)


def test_template_fills_agent_id():
    code = generate_agent_code(
        agent_id="my_agent",
        class_name="MyAgent",
    )
    assert "my_agent" in code
    assert "MyAgent" in code


def test_generate_agent_manifest_returns_dict():
    manifest = generate_agent_manifest(
        agent_id="test_agent",
        class_name="TestAgent",
        agent_type="tool",
        description="A tool agent",
    )
    assert isinstance(manifest, dict)
    assert manifest["name"] == "Test Agent"
    assert manifest["version"] == "1.0.0"
    assert manifest["type"] == "tool"
    assert manifest["description"] == "A tool agent"
    assert manifest["entry_point"] == "test_agent.py"
    assert manifest["class_name"] == "TestAgent"


def test_manifest_structure():
    manifest = generate_agent_manifest(
        agent_id="test",
        class_name="Test",
        agent_type="tool",
        description="desc",
    )
    assert set(manifest.keys()) == {
        "name", "version", "type", "description",
        "permissions", "dependencies", "entry_point", "class_name",
    }
    assert isinstance(manifest["permissions"], list)
    assert isinstance(manifest["dependencies"], list)


def test_validate_agent_code_returns_true_for_valid():
    code = generate_agent_code(
        agent_id="a",
        class_name="A",
    )
    assert validate_agent_code(code) is True


def test_validate_agent_code_returns_false_for_invalid():
    assert validate_agent_code("class broken def():") is False


def test_validate_agent_code_empty_string():
    assert validate_agent_code("") is False


def test_validate_agent_code_whitespace_only():
    assert validate_agent_code("   \n  ") is False


def test_validate_agent_code_syntax_error():
    assert validate_agent_code("def broken(") is False


def test_subagent_templates_has_expected_keys():
    expected = {"voice", "memory", "file_ops", "web", "code"}
    assert SUBAGENT_TEMPLATES.keys() == expected


def test_subagent_templates_all_same_constant():
    from multiagent.agent_template import AGENT_TEMPLATE
    for v in SUBAGENT_TEMPLATES.values():
        assert v is AGENT_TEMPLATE
