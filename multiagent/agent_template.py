import ast
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

AGENT_TEMPLATE = '''import logging
from typing import Any

logger = logging.getLogger("dex.agent.{agent_id}")

class {class_name}:
    def __init__(self, config: dict = None) -> None:
        self.id = "{agent_id}"
        self.config = config or {{}}
        logger.info(f"Agent {{self.id}} initialized")

    def process(self, input_data) -> dict[str, Any]:
        raise NotImplementedError("Subclasses must implement process()")

    def run(self) -> None:
        logger.info(f"Agent {{self.id}} running")
'''

SUBAGENT_TEMPLATES: dict[str, str] = {
    "voice": AGENT_TEMPLATE,
    "memory": AGENT_TEMPLATE,
    "file_ops": AGENT_TEMPLATE,
    "web": AGENT_TEMPLATE,
    "code": AGENT_TEMPLATE,
}

AGENT_MANIFEST_TEMPLATE: dict[str, Any] = {
    "name": "{agent_name}",
    "version": "1.0.0",
    "type": "{agent_type}",
    "description": "{description}",
    "permissions": [],
    "dependencies": [],
    "entry_point": "{agent_id}.py",
    "class_name": "{class_name}"
}


def generate_agent_code(
    agent_id: str,
    class_name: str,
) -> str:
    """Generate Python agent source code from the AGENT_TEMPLATE.

    Args:
        agent_id: Unique identifier for the agent (used in logging and filenames).
        class_name: Name of the generated Python class.

    Returns:
        A string containing the rendered Python source code.
    """
    return AGENT_TEMPLATE.format(agent_id=agent_id, class_name=class_name)


def generate_agent_manifest(
    agent_id: str,
    class_name: str,
    agent_type: str,
    description: str,
) -> dict[str, Any]:
    """Generate an agent manifest dict from the AGENT_MANIFEST_TEMPLATE.

    The *agent_name* is derived automatically from *agent_id* by replacing
    underscores with spaces and applying title case.

    Args:
        agent_id: Unique identifier (also used to derive the display name).
        class_name: Name of the Python class the manifest points to.
        agent_type: Type category.
        description: Human-readable description.

    Returns:
        A dictionary conforming to the manifest schema.
    """
    agent_name = agent_id.replace("_", " ").title()
    manifest = dict(AGENT_MANIFEST_TEMPLATE)
    manifest["name"] = agent_name
    manifest["type"] = agent_type
    manifest["description"] = description
    manifest["entry_point"] = f"{agent_id}.py"
    manifest["class_name"] = class_name
    return manifest


def validate_agent_code(code: str) -> bool:
    """Check whether *code* is syntactically valid Python.

    Uses ``ast.parse`` under the hood.  Returns ``True`` for valid code,
    ``False`` for any syntax error or empty/whitespace-only input.
    """
    if not code or not code.strip():
        return False
    try:
        ast.parse(code, mode="exec")
        return True
    except SyntaxError:
        return False


if __name__ == "__main__":
    source = generate_agent_code(
        agent_id="demo_agent",
        class_name="DemoAgent",
        agent_type="assistant",
        description="A demonstration agent",
    )
    print("=== Generated Source ===")
    print(source)

    manifest = generate_agent_manifest(
        agent_id="demo_agent",
        class_name="DemoAgent",
        agent_type="assistant",
        description="A demonstration agent",
    )
    print("=== Generated Manifest ===")
    print(json.dumps(manifest, indent=2))

    print(f"\n=== Validation: {validate_agent_code(source)} ===")
