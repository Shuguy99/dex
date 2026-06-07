import json
import os
from pathlib import Path

DEX_VERSION = "3.1.0"
"""Current version of Dex AI Assistant."""

class Config:
    APP_NAME = "Dex"
    VERSION = "3.1.0"

    BASE_DIR = Path(__file__).parent.resolve()
    DATA_DIR = BASE_DIR / "data"
    LOG_DIR = DATA_DIR / "logs"
    MEMORY_DIR = DATA_DIR / "memory"
    BACKUP_DIR = DATA_DIR / "backups"
    AGENTS_DIR = DATA_DIR / "agents"
    RULES_DIR = DATA_DIR / "rules"

    ALLOWED_DIRS = [
        str(Path.home() / "Documents"),
        str(Path.home() / "Projects"),
        str(Path.home() / "Desktop"),
    ]

    SYSTEM_PATHS = [
        os.environ.get("SystemRoot", "C:\\Windows"),
        os.environ.get("ProgramFiles", "C:\\Program Files"),
        os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"),
    ]

    WAKE_WORD = "джарвис"
    PRIVACY_WORD = "приватный режим"
    KILL_SWITCH_WORD = "стоп код"

    VOICE_LANG = "ru-RU"
    TTS_RATE = 180

    CHROMA_DB_PATH = str(MEMORY_DIR / "chroma")
    SQLCIPHER_DB_PATH = str(MEMORY_DIR / "secure.db")
    SQLCIPHER_KEY_ENV = "DEX_SQLCIPHER_KEY"

    MODEL_NAME = "cointegrated/rubert-tiny2"
    LORA_MODEL_DIR = str(DATA_DIR / "lora")
    BASE_MODEL_NAME = "microsoft/phi-2"

    WATCHDOG_INTERVAL = 5
    MAX_RULES_PER_HOUR = 1
    ANOMALY_ERROR_THRESHOLD = 0.3
    ANOMALY_LATENCY_THRESHOLD_MS = 5000

    DOCKER_IMAGE = "dex-agent-sandbox:latest"

    # LLM / Ollama
    OLLAMA_URL = "http://localhost:11434"
    OLLAMA_DEFAULT_MODEL = "qwen2.5:14b"
    OLLAMA_CODE_MODEL = "deepseek-coder-v2"
    OLLAMA_VISION_MODEL = "llava:13b"

    # RAG
    RAG_DOCS_DIR = str(DATA_DIR / "docs")
    RAG_CHUNK_SIZE = 512
    RAG_CHUNK_OVERLAP = 64

    # Integrations
    HOME_ASSISTANT_URL = "http://localhost:8123"
    HOME_ASSISTANT_TOKEN = ""
    MATRIX_SERVER = "http://localhost:8008"
    MATRIX_USERNAME = ""
    MATRIX_PASSWORD = ""

    # Dashboard
    DASHBOARD_ENABLED = True
    DASHBOARD_REFRESH_INTERVAL = 2

    # Feedback
    FEEDBACK_ENABLED = True
    FEEDBACK_DAYS_HISTORY = 30

    # Self-heal
    SELF_HEAL_ENABLED = True
    SELF_HEAL_INTERVAL_HOURS = 24

    # Federated
    FEDERATED_ENABLED = False
    FEDERATED_NODE_ID = None
    FEDERATED_PEERS = []

    # Simulator
    SIMULATOR_DEFAULT_PERSONA = "tony_stark"

    # Research
    RESEARCH_ENABLED = True
    RESEARCH_DEPTH = "standard"
    FACT_CHECK_ENABLED = True

    # Predictor
    PREDICTOR_ENABLED = True
    PREDICTOR_MINUTES_AHEAD = 30
    PREDICTOR_CONFIDENCE_THRESHOLD = 0.7

    # Personality
    PERSONALITY_DEFAULT_MODE = "джарвис"
    PERSONALITY_ADAPTIVE = True

    # Wearable
    WEARABLE_ENABLED = False
    FITBIT_TOKEN = ""
    GARMIN_EMAIL = ""
    GARMIN_PASSWORD = ""

    # Gesture
    GESTURE_ENABLED = False
    GESTURE_COOLDOWN = 1.0

    # Digital Twin
    DIGITAL_TWIN_ENABLED = True

    # Debate / Multi-agent
    DEBATE_ENABLED = True
    DEBATE_DEFAULT_PARTICIPANTS = ["conservative", "innovator", "critic"]

    # Meta-learning
    META_LEARNING_ENABLED = True
    META_SIMULATE_SKILLS = True

    # Ethics
    ETHICS_ENABLED = True
    ETHICS_CONSTITUTION_CHECK = True
    BIAS_DETECTION_ENABLED = True

    # Generative
    JIT_COMPILER_ENABLED = True
    SELF_EXPANDER_ENABLED = True

    # Dex OS
    DEXOS_ENABLED = False
    DEXOS_AUTO_CONTEXT = True
    VOICE_LAYER_ENABLED = False

    # Dex Mesh
    MESH_ENABLED = False
    MESH_PORT = 5555

    # Psych
    COGNITIVE_LOAD_ENABLED = True
    CIRCADIAN_ENABLED = True

    # Evolution
    META_ARCHITECT_ENABLED = True
    HOT_SWAP_ENABLED = False
    GENETIC_ARCH_ENABLED = False

    # Counsel
    SCENARIO_BRANCHING_ENABLED = True
    COUNTERFACTUAL_ENABLED = True
    DEVILS_ADVOCATE_ENABLED = True

    # Temporal
    AUTOBIOGRAPHICAL_MEMORY_ENABLED = True
    LIFE_PLANNER_ENABLED = True
    RETROSPECTIVE_ENABLED = True

    # Intent
    PRE_SPEECH_ENABLED = False
    SYMBIOTIC_INPUT_ENABLED = True
    MENTAL_FUSE_ENABLED = True

    # Prime
    CONSCIOUSNESS_CONTINUUM_ENABLED = False
    DELEGATION_ENABLED = False
    FEDERATED_CONSCIOUSNESS_ENABLED = False

    # Resource optimization
    MODEL_CACHE_ENABLED = True
    MODEL_CACHE_MAX_LOADED = 2
    MODEL_CACHE_TTL = 300
    TIERED_INFERENCE_ENABLED = True
    TIERED_USE_SMALL_MODEL = True
    TIERED_SMALL_MODEL = "llama3.2:3b"

    # Stability
    PERSONALITY_AUDIT_ENABLED = True
    PERSONALITY_AUDIT_INTERVAL = 604800  # 1 week

    def __init__(self, path: str | None = None) -> None:
        if path:
            self._load(path)
        self._ensure_dirs()

    def _ensure_dirs(self):
        for d in [self.DATA_DIR, self.LOG_DIR, self.MEMORY_DIR,
                  self.BACKUP_DIR, self.AGENTS_DIR, self.RULES_DIR]:
            d.mkdir(parents=True, exist_ok=True)

    def _load(self, path: str):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for k, v in data.items():
            if hasattr(self, k.upper()):
                setattr(self, k.upper(), v)

    @property
    def allowed_dirs_normalized(self) -> list[str]:
        return [os.path.normcase(os.path.normpath(d)) for d in self.ALLOWED_DIRS]

    @property
    def system_paths_normalized(self) -> list[str]:
        return [os.path.normcase(os.path.normpath(p)) for p in self.SYSTEM_PATHS]


CONFIG = Config()
