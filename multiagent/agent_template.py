AGENT_TEMPLATE = '''import logging

logger = logging.getLogger("dex.agent.{agent_id}")


class {class_name}:
    def __init__(self, config: dict = None):
        self.id = "{agent_id}"
        self.config = config or {{}}
        logger.info(f"Agent {{self.id}} initialized")

    def process(self, input_data):
        raise NotImplementedError("Subclasses must implement process()")

    def run(self):
        logger.info(f"Agent {{self.id}} running")
'''

SUBAGENT_TEMPLATES = {
    "voice": AGENT_TEMPLATE,
    "memory": AGENT_TEMPLATE,
    "file_ops": AGENT_TEMPLATE,
    "web": AGENT_TEMPLATE,
    "code": AGENT_TEMPLATE,
}

AGENT_MANIFEST_TEMPLATE = {
    "name": "{agent_name}",
    "version": "1.0.0",
    "type": "{agent_type}",
    "description": "{description}",
    "permissions": [],
    "dependencies": [],
    "entry_point": "{agent_id}.py",
    "class_name": "{class_name}"
}
