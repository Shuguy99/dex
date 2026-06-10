import logging
import threading
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from config import CONFIG
from core.app_launcher import AppLauncher
from core.async_engine import AsyncCommandQueue, GUIScheduler, TimeoutWrapper
from core.diagnostics import ThreadDiagnostics
from core.llm import OllamaClient
from core.model_cache import ModelCache
from core.permissions import PermissionManager
from core.personality import PersonalityEngine
from core.personality_auditor import PersonalityAuditor
from core.planner import TaskPlanner
from core.plugin_system import PluginSystem
from core.predictor import PersonalPredictor
from core.sandbox import FileSandbox
from core.tiered_inference import route_command
from core.voice import VoiceEngine
from core.voice_clone import VoiceCloner
from core.wake_word import WakeWordDetector
from counsel.counterfactual import CounterfactualAnalyzer
from counsel.devils_advocate import DevilsAdvocate
from counsel.scenario_branch import ScenarioTree
from dexos.contextual_desktop import ContextualDesktop
from dexos.search_engine import LocalSearchEngine
from dexos.voice_layer import VoiceLayer
from ethics.bias_detector import BiasDetector
from ethics.co_processor import EthicalCoProcessor
from evolution.genetic_search import GeneticArchitectureSearch
from evolution.hot_swapper import HotSwapper
from evolution.meta_architect import MetaArchitect
from generative.jit_compiler import JITCompiler
from generative.self_expander import SelfExpander
from intent.mental_fuse import MentalFuse
from intent.pre_speech import PreSpeechInterface
from intent.symbiotic_input import SymbioticInput
from learning.ab_testing import ABTester
from learning.backup import BackupManager
from learning.constitution import ConstitutionalChecker
from learning.digital_twin import DigitalTwin
from learning.federated import FederatedLearning
from learning.feedback import FeedbackCollector
from learning.lora import LoRATrainer
from learning.meta_learner import MetaLearner
from learning.research import ResearchAgent
from learning.rule_engine import RuleEngine
from learning.self_heal import SelfHealer
from memory.encryptor import SecureMemory
from memory.rag import RAGEngine
from memory.validator import MemoryValidator
from memory.vector_store import VectorMemory
from mesh.agent_swarm import AgentSwarm
from mesh.fault_tolerant_core import FaultTolerantCore
from mesh.privacy_controller import MeshPrivacyController
from multiagent.debate import AgentDebate
from multiagent.kill_switch import KillSwitch
from multiagent.orchestrator import Agent, Orchestrator
from multiagent.sandbox import AgentSandbox
from multiagent.version_control import AgentVersionControl
from prime.consciousness_continuum import ConsciousnessContinuum
from prime.delegation import DelegationEngine
from prime.federated_consciousness import FederatedConsciousness
from psych.circadian import CircadianAdapter
from psych.cognitive_load import CognitiveLoadAnalyzer
from sensors.camera import Camera
from sensors.gesture import GestureController
from sensors.microphone import Microphone
from sensors.privacy import PrivacyManager
from sensors.vision import VisionEngine
from temporal.autobiographical_memory import AutobiographicalMemory
from temporal.life_planner import LifePlanner
from temporal.retrospective import RetrospectiveAnalyzer
from watchdog.anomaly import AnomalyDetector
from watchdog.logger import DexLogger
from watchdog.monitor import WatchdogMonitor

logger = logging.getLogger("dex")


class DexAssistant:
    def __init__(self) -> None:
        self._config = CONFIG
        self._start_time = datetime.now()

        # Core
        self.voice = VoiceEngine(lang=CONFIG.VOICE_LANG)
        self.sandbox = FileSandbox(CONFIG.ALLOWED_DIRS, CONFIG.SYSTEM_PATHS)
        self.permissions = PermissionManager(voice_engine=self.voice)
        self.app_launcher = AppLauncher()
        self.wake_word = WakeWordDetector(CONFIG.WAKE_WORD)

        # LLM
        self.llm = OllamaClient(
            base_url=CONFIG.OLLAMA_URL,
            default_model=CONFIG.OLLAMA_DEFAULT_MODEL
        )
        self.planner = TaskPlanner(llm_client=self.llm, executor=self._execute_step)
        self.voice_cloner = VoiceCloner()

        # Plugin system
        self.plugins = PluginSystem(str(CONFIG.DATA_DIR / "plugins"))

        # Watchdog
        self.watchdog = WatchdogMonitor(
            interval=CONFIG.WATCHDOG_INTERVAL,
            log_dir=str(CONFIG.LOG_DIR)
        )
        self.anomaly = AnomalyDetector(
            error_threshold=CONFIG.ANOMALY_ERROR_THRESHOLD,
            latency_threshold_ms=CONFIG.ANOMALY_LATENCY_THRESHOLD_MS
        )
        self.dex_logger = DexLogger(str(CONFIG.LOG_DIR))

        # Memory
        self.vector_memory = VectorMemory(CONFIG.CHROMA_DB_PATH)
        self.secure_memory = SecureMemory(CONFIG.SQLCIPHER_DB_PATH)
        self.memory_validator = MemoryValidator(vector_memory=self.vector_memory)
        self.rag = RAGEngine(
            vector_memory=self.vector_memory,
            llm_client=self.llm,
            docs_dir=CONFIG.RAG_DOCS_DIR
        )

        # Multiagent (must be before learning/SelfHealer)
        self.orchestrator = Orchestrator(CONFIG.AGENTS_DIR)
        self.agent_vc = AgentVersionControl(CONFIG.AGENTS_DIR)
        self.agent_sandbox = AgentSandbox(CONFIG.DOCKER_IMAGE)
        self.kill_switch = KillSwitch()

        # Learning
        self.rule_engine = RuleEngine(CONFIG.RULES_DIR, max_per_hour=CONFIG.MAX_RULES_PER_HOUR)
        self.ab_tester = ABTester(CONFIG.BACKUP_DIR)
        self.backup_manager = BackupManager(CONFIG.BACKUP_DIR)
        self.lora = LoRATrainer(CONFIG.LORA_MODEL_DIR, CONFIG.BASE_MODEL_NAME)
        self.feedback = FeedbackCollector(str(CONFIG.DATA_DIR / "feedback"))
        self.constitution = ConstitutionalChecker()
        self.self_healer = SelfHealer(llm_client=self.llm, sandbox=self.agent_sandbox)
        self.research = ResearchAgent(
            llm_client=self.llm, rag_engine=self.rag, vector_memory=self.vector_memory
        )
        self.digital_twin = DigitalTwin(llm_client=self.llm, vector_memory=self.vector_memory)
        self.federated = FederatedLearning(
            data_dir=str(CONFIG.DATA_DIR / "federated"),
            node_id=CONFIG.FEDERATED_NODE_ID
        )

        # Sensors
        self.camera = Camera()
        self.microphone = Microphone()
        self.vision = VisionEngine(llm_client=self.llm)
        self.gesture = GestureController()
        self.privacy = PrivacyManager()
        self.privacy.register("camera", self.camera)
        self.privacy.register("microphone", self.microphone)
        self.privacy.register("voice", self.voice)

        # Personality & Predictor
        self.personality = PersonalityEngine(default_mode=CONFIG.PERSONALITY_DEFAULT_MODE)
        self.predictor = PersonalPredictor(llm_client=self.llm)

        # Debate
        self.debate = AgentDebate(llm_client=self.llm)

        # Meta-learning
        self.meta_learner = MetaLearner(
            llm_client=self.llm, sandbox=self.agent_sandbox,
            rule_engine=self.rule_engine, lora_trainer=self.lora,
            rag_engine=self.rag
        )

        # Ethics
        self.ethics = EthicalCoProcessor(
            llm_client=self.llm, constitution_checker=self.constitution
        )
        self.bias_detector = BiasDetector()

        # Generative
        self.jit_compiler = JITCompiler(
            llm_client=self.llm, sandbox=self.agent_sandbox,
            plugin_system=self.plugins
        )
        self.self_expander = SelfExpander(llm_client=self.llm)

        # Dex OS
        self.desktop = ContextualDesktop(llm_client=self.llm)
        self.voice_layer = VoiceLayer(app_launcher=self.app_launcher)
        self.local_search = LocalSearchEngine(
            vector_memory=self.vector_memory, rag_engine=self.rag
        )

        # Dex Mesh
        self.swarm = AgentSwarm(local_server_port=CONFIG.MESH_PORT)
        self.mesh_privacy = MeshPrivacyController()
        self.fault_core = FaultTolerantCore()

        # Psych
        self.cognitive_load = CognitiveLoadAnalyzer()
        self.circadian = CircadianAdapter()

        # Evolution
        self.meta_architect = MetaArchitect(llm_client=self.llm)
        self.hot_swapper = HotSwapper()
        self.genetic_search = GeneticArchitectureSearch(
            llm_client=self.llm, user_simulator=self.run_simulator if hasattr(self, 'run_simulator') else None
        )

        # Counsel
        self.scenario_tree = ScenarioTree(llm_client=self.llm, predictor=self.predictor)
        self.counterfactual = CounterfactualAnalyzer(llm_client=self.llm)
        self.devils_advocate = DevilsAdvocate(llm_client=self.llm)

        # Temporal
        self.autobio_memory = AutobiographicalMemory(
            llm_client=self.llm, vector_memory=self.vector_memory
        )
        self.life_planner = LifePlanner(llm_client=self.llm)
        self.retrospective = RetrospectiveAnalyzer(
            llm_client=self.llm, feedback_collector=self.feedback,
            autobiographical_memory=self.autobio_memory
        )

        # Intent
        self.pre_speech = PreSpeechInterface(camera=self.camera)
        self.symbiotic_input = SymbioticInput(llm_client=self.llm)
        self.mental_fuse = MentalFuse()

        # Prime
        self.continuum = ConsciousnessContinuum()
        self.delegation = DelegationEngine(mesh_swarm=self.swarm)
        self.federated_consciousness = FederatedConsciousness(
            llm_client=self.llm, mesh_privacy=self.mesh_privacy
        )

        # Resource optimization
        self.model_cache = ModelCache(
            max_loaded=CONFIG.MODEL_CACHE_MAX_LOADED,
            ttl=CONFIG.MODEL_CACHE_TTL
        )
        self.personality_auditor = PersonalityAuditor(
            data_dir=str(CONFIG.DATA_DIR / "temporal")
        )

        # Async engine
        self.cmd_queue = AsyncCommandQueue()
        self.timeout = TimeoutWrapper(default_timeout=30.0)
        self.gui_scheduler = GUIScheduler()
        self.diagnostics = ThreadDiagnostics()
        self._ready = threading.Event()

        self._command_handlers: dict[str, Callable[..., str]] = {}
        self._initialized = False
        self._feedback_mode = False
        self._conversation_history: list[dict[str, str]] = []
        self._conversation_max = 50
        self._conv_lock = threading.Lock()
        self._pending_task: dict[str, Any] | None = None

    def initialize(self) -> None:
        logger.info(f"{CONFIG.APP_NAME} v{CONFIG.VERSION} initializing...")

        self.permissions.ensure_non_admin()

        # Memory
        self.vector_memory.initialize()
        self.secure_memory.initialize()

        # Agents
        self.orchestrator.load_agents()
        self._register_default_agents()

        # LLM — lazy check, don't block startup
        self._llm_ready = False
        logger.info("LLM check deferred to background")

        # Plugins
        self.plugins.discover()
        self.plugins.load_all()

        # Feedback
        if CONFIG.FEEDBACK_ENABLED:
            self.feedback.load_history()
            logger.info(f"Feedback history loaded: {len(self.feedback._ratings)} entries")

        # Dex Mesh (if enabled)
        if CONFIG.MESH_ENABLED:
            self.swarm.start(command_handler=self.process_command)

        # Commands
        self._register_builtin_commands()
        self._register_plugin_commands()

        # Async command queue
        self.cmd_queue.start(processor=self.process_command)

        self._initialized = True
        self.watchdog.start()
        logger.info(f"{CONFIG.APP_NAME} ready. Uptime: {self.uptime}")

    def init_llm_background(self, callback: Callable[[bool], None] | None = None) -> None:
        def _load() -> None:
            logger.info("Background LLM init starting...")
            try:
                self.timeout.call(self.llm.check_available, timeout=15)
                if self.llm.ready:
                    self._llm_ready = True
                    self._ready.set()
                    logger.info(f"LLM ready: {self.llm.models}")
                else:
                    logger.warning("LLM not available")
            except Exception as e:
                logger.warning(f"LLM init error: {e}")
            finally:
                if callback:
                    callback(self._llm_ready)
        threading.Thread(target=_load, daemon=True, name="llm-load").start()

    @property
    def llm_ready(self) -> bool:
        return self._llm_ready

    def _register_default_agents(self) -> None:
        agent_types = ["voice", "memory", "file_ops", "web", "code", "rag", "vision"]
        for atype in agent_types:
            agent = Agent(
                agent_id=f"{atype}_agent",
                agent_type=atype,
                config={"auto_start": False}
            )
            self.orchestrator.register_agent(agent)

    def _register_builtin_commands(self) -> None:
        cmds = {
            # Core
            "открой": self._cmd_open,
            "запусти": self._cmd_launch,
            "открой файл": self._cmd_open_file,
            # Memory & RAG
            "напомни": self._cmd_remember,
            "запомни": self._cmd_remember,
            "что ты помнишь": self._cmd_recall,
            "найди": self._cmd_search_kb,
            "спроси": self._cmd_query_rag,
            # Planning & Research
            "подготовь": self._cmd_plan,
            "спланируй": self._cmd_plan,
            "исследуй": self._cmd_research,
            "проверь факт": self._cmd_fact_check,
            # Feedback & Self-heal
            "оцени": self._cmd_feedback,
            "просканируй код": self._cmd_self_heal,
            "конституция": self._cmd_constitution,
            # Personality
            "режим": self._cmd_set_mode,
            "личность": self._cmd_personality,
            # Predictor
            "прогноз": self._cmd_predict,
            "паттерны": self._cmd_patterns,
            "симуляция": self._cmd_simulate,
            # Digital Twin
            "двойник": self._cmd_twin,
            "ответь за меня": self._cmd_twin_reply,
            "идея": self._cmd_idea,
            # Debate
            "дебаты": self._cmd_debate,
            "проверь решение": self._cmd_critic,
            # Security
            "приватный режим": self._cmd_privacy,
            "стоп код": self._cmd_kill_switch,
            "верни старый мозг": self._cmd_rollback_model,
            # Meta-learning
            "мета обучение": self._cmd_meta_report,
            "стратегия": self._cmd_select_strategy,
            "синтезируй": self._cmd_synthetic_scenario,
            # Ethics
            "этика": self._cmd_ethics_check,
            "мораль": self._cmd_ethics_check,
            "bias": self._cmd_bias,
            "когнитивное искажение": self._cmd_bias,
            # Generative
            "создай агента": self._cmd_jit_compile,
            "jit": self._cmd_jit_compile,
            "улучшение": self._cmd_self_expand,
            "предложение": self._cmd_self_expand,
            # Dex OS
            "рабочий стол": self._cmd_desktop,
            "дашборд": self._cmd_desktop,
            "голос слой": self._cmd_voice_layer,
            "поищи": self._cmd_search_local,
            "локальный поиск": self._cmd_search_local,
            # Dex Mesh
            "mesh": self._cmd_mesh,
            "рой": self._cmd_mesh,
            "пиры": self._cmd_peers,
            # Psych
            "нагрузка": self._cmd_cognitive_load,
            "циркадный": self._cmd_circadian,
            "циркад": self._cmd_circadian,
            # Evolution
            "архитектура": self._cmd_architect,
            "эволюция": self._cmd_architect,
            "генетика": self._cmd_genetic,
            "горячая замена": self._cmd_hot_swap,
            # Counsel
            "сценарий": self._cmd_scenario,
            "дерево решений": self._cmd_scenario,
            "развилка": self._cmd_fork,
            "контраргумент": self._cmd_devils_advocate,
            "адвокат": self._cmd_devils_advocate,
            # Temporal
            "воспоминание": self._cmd_autobio_recall,
            "помнишь": self._cmd_autobio_recall,
            "цель": self._cmd_add_goal,
            "жизненные цели": self._cmd_life_goals,
            "ретроспектива": self._cmd_retrospective,
            "итоги месяца": self._cmd_monthly_report,
            # Intent
            "предречь": self._cmd_pre_speech,
            "заверши": self._cmd_complete,
            "предскажи ввод": self._cmd_complete,
            "предохранитель": self._cmd_mental_fuse,
            # Prime
            "сессия": self._cmd_session,
            "делегируй": self._cmd_delegate,
            "отозвать": self._cmd_recall_delegate,
            "федерация": self._cmd_federated,
            "коллективный": self._cmd_federated,
            # Personality Audit
            "аудит": self._cmd_personality_audit,
            "дрейф": self._cmd_personality_audit,
            "ресурсы": self._cmd_resources,
            # System
            "статус": self._cmd_status,
            "помощь": self._cmd_help,
        }
        self._command_handlers = cmds

        # Plugin management command
        cmds["плагин"] = self._cmd_plugin
        self._command_handlers = cmds

    def _register_plugin_commands(self) -> None:
        for prefix, _plugin_name in self.plugins.get_command_prefixes().items():
            if prefix not in self._command_handlers:
                self._command_handlers[prefix] = self._make_plugin_handler(prefix)

    def _make_plugin_handler(self, prefix: str) -> Callable[[str], str]:
        def handler(args: str) -> str:
            full_text = f"{prefix} {args}".strip() if args else prefix
            result = self.plugins.execute(full_text)
            if result is not None:
                return result
            return f"Плагин '{prefix}' не обработал команду"
        return handler

    def process_command(self, text: str) -> str:
        text = text.strip()
        logger.info(f"Command: {text}")

        start = time.time()

        # 1. Kill switch
        if self.kill_switch.check_and_trigger(text):
            return "Стоп-код активирован. Все процессы заморожены."

        # 2. Privacy mode
        if self.privacy.is_active and "приватный режим" not in text.lower():
            return "Приватный режим активен. Команды не выполняются."

        # 3. Tiered inference for simple responses
        if CONFIG.TIERED_INFERENCE_ENABLED:
            routing = route_command(text, use_small_model=CONFIG.TIERED_USE_SMALL_MODEL)
            if routing["simple_response"] is not None:
                result = routing["simple_response"]
                self._post_process(text, result, routing.get("action", ""), start)
                return result

        # 4. Structured command matching (try all registered handlers)
        text_lower = text.lower()
        for prefix, handler in sorted(self._command_handlers.items(),
                                      key=lambda x: -len(x[0])):
            if text_lower.startswith(prefix):
                args = text[len(prefix):].strip()
                can_proceed, reasons = self.constitution.can_proceed(prefix, {"args": args})
                if not can_proceed:
                    return "⛔ Действие заблокировано конституцией:\n" + "\n".join(reasons)
                result = handler(args)
                self._post_process(text, result, prefix, start)
                return result

        # 5. Mental fuse check for destructive patterns
        mental = self.mental_fuse.check(text)
        if mental.get("blocked"):
            return f"⛔ {mental.get('reason', 'Действие заблокировано')}"

        # 6. Natural conversation via LLM (PRIMARY PATH)
        result = self._conversational_respond(text)
        self._post_process(text, result, "llm", start)
        return result

    def _execute_step(self, action: str, params: dict[str, Any]) -> str:
        action_map = {
            "open_file": lambda p: self._cmd_open(p.get("name", "")),
            "launch_app": lambda p: self._cmd_launch(p.get("name", "")),
            "create_folder": lambda p: self._create_folder(p.get("name", "new")),
            "write_file": lambda p: self._write_file(p.get("name", "file"),
                                                      p.get("content", "")),
            "run_command": lambda p: self._run_shell(p.get("cmd", "")),
            "search_memory": lambda p: self._cmd_recall(p.get("query", "")),
            "send_notification": lambda p: f"Notification: {p.get('message', '')}",
            "execute_script": lambda p: self._run_shell(f"python {p.get('path', '')}"),
            "install_package": lambda p: self._run_shell(f"pip install {p.get('name', '')}"),
            "clone_repo": lambda p: self._run_shell(
                f"git clone {p.get('url', '')} {p.get('dir', '')}"),
        }
        handler = action_map.get(action)
        if handler:
            return handler(params)
        return f"Unknown action: {action}"

    def _create_folder(self, name: str) -> str:
        import os
        path = os.path.join(CONFIG.ALLOWED_DIRS[0], name)
        os.makedirs(path, exist_ok=True)
        return f"Папка создана: {path}"

    def _write_file(self, name: str, content: str) -> str:
        import os
        path = os.path.join(CONFIG.ALLOWED_DIRS[0], name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Файл создан: {path}"

    def _run_shell(self, cmd: str) -> str:
        import subprocess
        can, reasons = self.constitution.can_proceed("run_command", {"cmd": cmd})
        if not can:
            return f"⛔ {reasons[0]}"
        result = subprocess.run(cmd, capture_output=True, text=True,
                                 shell=True, timeout=30)
        output = result.stdout[-500:] if result.stdout else result.stderr[-500:]
        return output or "Команда выполнена"

    def _cmd_open(self, args: str) -> str:
        if not args:
            return "Что открыть, сэр?"
        path = self.sandbox.resolve_path(args)
        if not path:
            return f"Не могу найти: {args}"
        if self.sandbox.is_dangerous(path):
            ok = self.permissions.confirm_dangerous_action(f"Открыть системный файл: {path}")
            if not ok:
                return "Действие отклонено"
        self.sandbox.open_file(path)
        return f"Открываю: {path}"

    def _cmd_launch(self, args: str) -> str:
        if not args:
            return "Что запустить, сэр?"
        success = self.app_launcher.launch(args)
        return f"Запускаю: {args}" if success else f"Не удалось запустить: {args}"

    def _cmd_open_file(self, args: str) -> str:
        return self._cmd_open(args)

    def _cmd_remember(self, args: str) -> str:
        if not args:
            return "Что запомнить, сэр?"
        if SecureMemory.is_sensitive(args):
            self.secure_memory.store("user_fact", str(hash(args)), args)
            return "Информация сохранена в защищённом хранилище"
        if not self.memory_validator.validate_new_fact(args):
            self.voice.say("Эта информация противоречит уже известной. Подтвердите сохранение.")
            response = self.voice.listen(timeout=5)
            if response and ("да" in response or "подтверждаю" in response):
                self.vector_memory.add(args, {"source": "user"}, doc_id=str(hash(args)))
                return "Информация сохранена (подтверждено)"
            return "Сохранение отклонено"
        self.vector_memory.add(args, {"source": "user"}, doc_id=str(hash(args)))
        return "Запомнил, сэр"

    def _cmd_recall(self, args: str) -> str:
        query = args or "воспоминания"
        if self.llm.ready:
            result = self.rag.query(query, use_llm=True)
            if result:
                return result
        results = self.vector_memory.search(query, n_results=5)
        if not results:
            return "Я пока ничего не помню, сэр"
        memories = [f"- {r.get('text', '')[:100]}" for r in results]
        return "Нашёл в памяти:\n" + "\n".join(memories)

    def _cmd_search_kb(self, args: str) -> str:
        if not args:
            return "Что найти?"
        results = self.rag.query(args, use_llm=self.llm.ready)
        return results

    def _cmd_query_rag(self, args: str) -> str:
        if not args:
            return "О чём спросить?"
        return self.rag.query(args, use_llm=self.llm.ready)

    def _cmd_plan(self, args: str) -> str:
        if not args:
            return "Что спланировать?"
        plan = self.planner.create_plan(args)
        if not plan:
            return "Не удалось создать план"
        result = self.planner.execute_plan(plan)
        return self.planner.summarize_plan(result)

    def _cmd_feedback(self, args: str) -> str:
        if not args:
            stats = self.feedback.get_stats(CONFIG.FEEDBACK_DAYS_HISTORY)
            return (
                f"Статистика оценок:\n"
                f"  Всего: {stats.get('count', 0)}\n"
                f"  Средняя: {stats.get('avg', 0):.1f}/5\n"
                f"  Мин: {stats.get('min', 0)}, Макс: {stats.get('max', 0)}\n"
                f"  За период: {stats.get('days', 0)} дней"
            )
        rating = self.feedback.ask(args)
        if rating:
            return f"Оценка {rating}/5 сохранена"
        return "Оценка не требуется"

    def _cmd_self_heal(self, args: str) -> str:
        path = args or str(CONFIG.BASE_DIR / "core" / "assistant.py")
        if not Path(path).exists():
            return f"Файл не найден: {path}"
        result = self.self_healer.analyze_code(path)
        if not result:
            return "Проблем не найдено"
        lines = [f"Найдено {len(result)} проблем:"]
        for issue in result[:10]:
            lines.append(f"  L{issue['line']} [{issue['severity']}]: {issue['message']}")
        return "\n".join(lines)

    def _cmd_constitution(self, args: str) -> str:
        articles = self.constitution.get_articles()
        lines = ["── Конституция Dex ──"]
        for a in articles:
            icon = {"critical": "🔴", "high": "🟡", "medium": "🟢"}.get(a["severity"], "⚪")
            lines.append(f"  {icon} [{a['severity'].upper()}] {a['principle']}")
        return "\n".join(lines)

    def _cmd_privacy(self, args: str) -> str:
        self.privacy.toggle()
        state = "включён" if self.privacy.is_active else "выключен"
        return f"Приватный режим {state}"

    def _cmd_kill_switch(self, args: str) -> str:
        self.kill_switch.trigger()
        return "Стоп-код активирован"

    def _cmd_rollback_model(self, args: str) -> str:
        backups = self.backup_manager.list_backups("model")
        if not backups:
            return "Нет доступных резервных копий"
        latest = str(CONFIG.BACKUP_DIR / backups[0]["name"])
        data = self.backup_manager.restore_backup(latest)
        if data:
            return "Предыдущая версия модели восстановлена"
        return "Ошибка восстановления"

    def _cmd_status(self, args: str) -> str:
        health = self.orchestrator.check_health()
        mem_count = self.vector_memory.count()
        rules_count = len(self.rule_engine.get_active_rules())
        llm_status = "✓" if self.llm.ready else "✗"
        feedback_stats = self.feedback.get_stats(CONFIG.FEEDBACK_DAYS_HISTORY)
        return (
            f"Статус системы:\n"
            f"- Версия: {CONFIG.VERSION}\n"
            f"- Работает: {self.uptime}\n"
            f"- LLM: {llm_status} ({len(self.llm.models)} моделей)\n"
            f"- Агентов: {health['active_agents']}/{health['total_agents']}\n"
            f"- Воспоминаний: {mem_count}\n"
            f"- Документов в RAG: {len(self.rag._index)}\n"
            f"- Активных правил: {rules_count}\n"
            f"- Средняя оценка: {feedback_stats['avg']:.1f}/5\n"
            f"- Плагинов: {len(self.plugins.list_plugins())}\n"
            f"- Аномалий: {'⚠' if self.watchdog.has_anomaly else '✓'}"
        )

    def _cmd_help(self, args: str) -> str:
        return (
            "Доступные команды:\n"
            "  📁 открой/запусти — файлы и приложения\n"
            "  🧠 запомни/найди/спроси — память и RAG\n"
            "  📋 подготовь/спланируй — многошаговые задачи\n"
            "  ⭐ оцени — обратная связь\n"
            "  🔍 просканируй код — самодиагностика\n"
            "  📜 конституция — принципы работы\n"
            "  🔒 приватный режим — вкл/выкл\n"
            "  🛑 стоп код — аварийная остановка\n"
            "  🔄 верни старый мозг — откат модели\n"
            "  📊 статус — информация о системе\n"
            "  ❓ помощь — эта справка"
        )

    def _conversational_respond(self, text: str) -> str:
        with self._conv_lock:
            self._conversation_history.append({"role": "user", "content": text})
            if len(self._conversation_history) > self._conversation_max * 2:
                self._conversation_history = self._conversation_history[-self._conversation_max * 2:]

            if not self.llm.ready:
                for rule in self.rule_engine.get_active_rules():
                    pattern = rule.get("pattern", "")
                    if pattern:
                        import re
                        if re.search(pattern, text, re.IGNORECASE):
                            action = rule.get("expected_action", "")
                            result = f"Согласно правилу: {action}"
                            self._conversation_history.append({"role": "assistant", "content": result})
                            return result
                result = "Простите, сэр, я не понимаю эту команду"
                self._conversation_history.append({"role": "assistant", "content": result})
                return result

            history_slice = self._conversation_history[-12:]

        memory_context = ""
        try:
            results = self.vector_memory.search(text, n_results=3)
            if results and isinstance(results, dict) and results.get("documents"):
                docs = [d for d in results["documents"][0] if d][:2]
                if docs:
                    memory_context = "\nRelevant context:\n" + "\n".join(docs)
        except Exception:
            pass

        energy = self.circadian.get_current_phase() if hasattr(self, 'circadian') else "medium"

        load_info = ""
        if hasattr(self, 'cognitive_load'):
            load_data = self.cognitive_load.get_load_score()
            if load_data.get("score", 0) > 0.7:
                load_info = "\n[User appears busy or stressed — keep response concise]"

        system_prompt = (
            f"Ты — Dex, голосовой ассистент. "
            f"Текущий режим: {self.personality.current_mode}. "
            f"Энергия пользователя: {energy}.{load_info}"
            f"{memory_context}"
            f"\n\nОтвечай на русском, кратко и по делу. "
            f"Если пользователь просит что-то сделать — скажи, что умеешь: "
            f"открывать файлы, запускать приложения, запоминать, искать, "
            f"планировать задачи, исследовать темы, проводить дебаты."
        )

        try:
            response = self.llm.chat(
                messages=[{"role": "system", "content": system_prompt}] + history_slice,
                temperature=0.7,
            )
            result = response.strip()
        except Exception as e:
            logger.error(f"LLM conversation error: {e}")
            result = "Простите, сэр, произошла ошибка. Попробуйте ещё раз."

        with self._conv_lock:
            self._conversation_history.append({"role": "assistant", "content": result})

        try:
            self.digital_twin.learn_from_message(text, result)
            self.personality_auditor.record_interaction(text, result)
        except Exception:
            pass

        return result

    def _post_process(self, text: str, result: str, command: str, start: float) -> None:
        """Common post-processing after any command is handled."""
        elapsed = (time.time() - start) * 1000
        error = "ошибк" in result.lower() or "не удалось" in result.lower()
        self.dex_logger.log_command(text, result, elapsed, success=not error)
        self.anomaly.record_latency(elapsed)
        if error:
            self.anomaly.record_error()
        self._collect_feedback(command, result)
        self._post_command_hooks(text, result, command)

    def _post_command_hooks(self, text: str, result: str, command: str) -> None:
        if CONFIG.DIGITAL_TWIN_ENABLED:
            self.digital_twin.learn_from_message(text, result)
        if CONFIG.PREDICTOR_ENABLED:
            self.predictor.record_command(command)
            self.predictor.analyze_patterns()
        if CONFIG.PERSONALITY_AUDIT_ENABLED:
            error = "ошибк" in result.lower() or "не удалось" in result.lower()
            self.personality_auditor.record_interaction(text, result, error=error)
            self.personality_auditor.audit()

    def _cmd_research(self, args: str) -> str:
        if not args:
            return "Что исследовать?"
        report = self.research.investigate(args, depth=CONFIG.RESEARCH_DEPTH)
        lines = [f"── Исследование: {report['topic']} ──"]
        lines.append(f"Источников: {report['sources_count']}")
        lines.append("")
        lines.append(report.get("summary", "")[:1000])
        lines.append("\nПолный отчёт сохранён.")
        return "\n".join(lines)

    def _cmd_fact_check(self, args: str) -> str:
        if not args:
            return "Что проверить?"
        result = self.research.fact_check(args)
        if result.get("match"):
            return f"✓ Факт подтверждён: {args}"
        elif result.get("correction"):
            return f"⚠️ Сэр, в вашей базе знаний иная информация:\n{result['correction']}"
        return "Факт не найден в базе знаний."

    def _cmd_set_mode(self, args: str) -> str:
        if not args:
            modes = self.personality.get_mode_list()
            return f"Текущий режим: {self.personality.current_mode}\nДоступные: {', '.join(modes)}"
        if self.personality.set_mode(args):
            return f"Режим «{args}» активирован. {self.personality._mode.get('greeting', '')}"
        return f"Нет такого режима: {args}. Доступны: {', '.join(self.personality.get_mode_list())}"

    def _cmd_personality(self, args: str) -> str:
        return f"Текущий режим: {self.personality.current_mode}"

    def _cmd_predict(self, args: str) -> str:
        predictions = self.predictor.predict_next(CONFIG.PREDICTOR_MINUTES_AHEAD)
        if not predictions:
            return "Недостаточно данных для прогноза."
        lines = ["── Прогноз на 30 минут ──"]
        for p in predictions:
            confidence = "●" * int(p.get("confidence", 0) * 5) + "○" * (5 - int(p.get("confidence", 0) * 5))
            lines.append(f"  {confidence} {p['name']} ({p.get('reason', '')[:50]})")
        return "\n".join(lines)

    def _cmd_patterns(self, args: str) -> str:
        return self.predictor.get_pattern_summary()

    def _cmd_simulate(self, args: str) -> str:
        if not args:
            return "Что симулировать? Например: удалить test.txt"
        report = self.predictor.simulate_consequence("user_action", {"description": args})
        lines = ["── Симуляция последствий ──"]
        if report.get("risks"):
            for r in report["risks"]:
                icon = "🔴" if "CRITICAL" in r else "🟡" if "HIGH" in r or "MEDIUM" in r else "🟢"
                lines.append(f"  {icon} {r[:100]}")
        lines.append(f"\nВердикт: {'Безопасно' if report.get('safe', True) else 'Есть риски'}")
        return "\n".join(lines)

    def _cmd_twin(self, args: str) -> str:
        return self.digital_twin.get_profile_summary()

    def _cmd_twin_reply(self, args: str) -> str:
        if not args:
            return "Что нужно сказать?"
        reply = self.digital_twin.generate_reply(args)
        return reply

    def _cmd_idea(self, args: str) -> str:
        if not args:
            return "О чём сгенерировать идеи?"
        ideas = self.digital_twin.generate_ideas(args)
        if not ideas:
            return "Не удалось сгенерировать идеи. Убедитесь, что LLM доступна."
        lines = ["── Сгенерированные идеи ──"]
        for i, idea in enumerate(ideas, 1):
            lines.append(f"  {i}. {idea}")
        return "\n".join(lines)

    def _cmd_debate(self, args: str) -> str:
        if not args:
            return "Какую тему вынести на дебаты?"
        participants = CONFIG.DEBATE_DEFAULT_PARTICIPANTS
        result = self.debate.debate(args, participants=participants, rounds=2)
        lines = [f"── Дебаты: {result['topic']} ──"]
        for h in result.get("history", []):
            speaker_icon = {"conservative": "🛡️", "innovator": "🚀",
                            "critic": "🔍", "pragmatist": "⚖️"}.get(h["speaker"], "💬")
            lines.append(f"\n{speaker_icon} {h['speaker']}:")
            lines.append(f"  {h['argument'][:300]}")
        if result.get("synthesis"):
            lines.append(f"\n── Синтез ──\n{result['synthesis'][:500]}")
        return "\n".join(lines)

    def _cmd_critic(self, args: str) -> str:
        if not args:
            return "Какое решение проверить?"
        review = self.debate.get_critic_review(args)
        lines = ["── Проверка решения ──"]
        verdict_icon = {"approved": "✓", "rejected": "✗", "needs_changes": "⚠️"}
        lines.append(f"Вердикт: {verdict_icon.get(review.get('verdict', ''), '?')} {review.get('verdict', 'unknown')}")
        if review.get("flaws"):
            lines.append("Уязвимости:")
            for flaw in review["flaws"]:
                lines.append(f"  • {flaw}")
        return "\n".join(lines)

    def _cmd_meta_report(self, args: str) -> str:
        return self.meta_learner.get_meta_report()

    def _cmd_select_strategy(self, args: str) -> str:
        if not args:
            return "Для какого типа ошибок выбрать стратегию?"
        result = self.meta_learner.select_strategy(args)
        return f"Стратегия: {result.get('strategy', '?')} — {result.get('reason', '?')}"

    def _cmd_synthetic_scenario(self, args: str) -> str:
        topics = [args] if args else ["распознавание речи", "автоматизация", "безопасность"]
        scenarios = self.meta_learner.generate_synthetic_scenarios(topics)
        if not scenarios:
            return "Не удалось создать сценарии."
        lines = ["── Синтетические сценарии ──"]
        for s in scenarios:
            lines.append(f"  {s.get('topic')} [{s.get('difficulty')}]: {s.get('task', '')[:100]}")
        return "\n".join(lines)

    def _cmd_ethics_check(self, args: str) -> str:
        if not args:
            return "Какое действие проверить этически?"
        report = self.ethics.evaluate_action(args, {"input": args}, user_input=args)
        lines = [f"── Этическая оценка: {args[:60]} ──"]
        for framework, eval_result in report.get("evaluations", {}).items():
            icon = {"ethical": "✓", "unethical": "✗", "questionable": "?"}
            lines.append(f"  {icon.get(eval_result.get('verdict', ''), '?')} {framework}: "
                         f"{eval_result.get('reason', '')[:80]}")
        lines.append(f"\nВердикт: {report.get('recommendation', '')}")
        if report.get("biases_detected"):
            for b in report["biases_detected"]:
                lines.append(f"  ⚠️ {b.get('message', '')}")
        return "\n".join(lines)

    def _cmd_bias(self, args: str) -> str:
        if not args:
            return self.bias_detector.get_bias_summary()
        biases = self.bias_detector.check_command(args)
        if not biases:
            return "Когнитивных искажений не обнаружено."
        lines = ["── Когнитивные искажения ──"]
        for b in biases:
            lines.append(f"  ⚠️ {b.get('message', '')}")
        return "\n".join(lines)

    def _cmd_jit_compile(self, args: str) -> str:
        if not args:
            return "Опишите задачу для агента."
        result = self.jit_compiler.compile_agent(args)
        if result.get("success"):
            return f"✓ JIT-агент создан: {result.get('agent_id', '?')}\n{result.get('test_output', '')[:200]}"
        return f"✗ Ошибка: {result.get('reason', '') or result.get('error', '')}"

    def _cmd_self_expand(self, args: str) -> str:
        domain = args if args else None
        result = self.self_expander.propose_improvement(domain)
        if not result.get("success"):
            return f"Не удалось создать предложение: {result.get('reason', '')}"
        prop = result.get("proposal", {})
        lines = [f"── Предложение: {prop.get('title', '')} ──"]
        lines.append(f"  Описание: {prop.get('description', '')[:200]}")
        lines.append(f"  Сложность: {prop.get('complexity', 'unknown')}")
        lines.append(f"  Файл: {prop.get('file_path', '')}")
        return "\n".join(lines)

    def _cmd_desktop(self, args: str) -> str:
        ctx = args if args else None
        dash = self.desktop.get_dashboard(override_context=ctx)
        lines = [f"── {dash['dashboard']['label']} ──"]
        for w in dash["dashboard"]["widgets"]:
            lines.append(f"  ▸ {w}")
        return "\n".join(lines)

    def _cmd_voice_layer(self, args: str) -> str:
        return self.voice_layer.get_layer_summary()

    def _cmd_search_local(self, args: str) -> str:
        if not args:
            return self.local_search.get_search_summary()
        results = self.local_search.search(args)
        if not results:
            return f"Ничего не найдено по запросу: {args}"
        lines = [f"── Результаты для: {args} ──"]
        for r in results[:5]:
            lines.append(f"  [{r['score']:.1f}] {r.get('title', '')[:60]}")
            lines.append(f"       {r.get('snippet', '')[:100]}")
        return "\n".join(lines)

    def _cmd_mesh(self, args: str) -> str:
        if not CONFIG.MESH_ENABLED:
            return "Dex Mesh отключён. Включите в конфиге."
        return self.swarm.get_swarm_summary()

    def _cmd_peers(self, args: str) -> str:
        if not CONFIG.MESH_ENABLED:
            return "Dex Mesh отключён."
        found = self.swarm.discover_peers()
        lines = ["── Поиск пиров ──"]
        if found:
            for p in found:
                lines.append(f"  Найден: {p.get('peer_id')} на порту {p.get('port')}")
        else:
            lines.append("  Пиры не обнаружены.")
        return "\n".join(lines)

    def _cmd_cognitive_load(self, args: str) -> str:
        return self.cognitive_load.get_load_summary()

    def _cmd_circadian(self, args: str) -> str:
        if args in ("set wake", "set bed"):
            parts = args.split()
            if len(parts) == 3:
                self.circadian.update_sleep_schedule(
                    wake_time=parts[2] if parts[1] == "wake" else None,
                    bed_time=parts[2] if parts[1] == "bed" else None
                )
                return "Расписание обновлено."
        return self.circadian.get_circadian_summary()

    def _cmd_architect(self, args: str) -> str:
        if not args:
            return self.meta_architect.get_arch_summary()
        result = self.meta_architect.propose_architecture_change(current_topology=args)
        if result.get("success"):
            p = result["proposal"]
            lines = [f"── {p.get('title', '')} ──"]
            lines.append(f"  {p.get('description', '')[:200]}")
            lines.append(f"  Топология: {p.get('new_topology', '')}")
            return "\n".join(lines)
        return "Не удалось сгенерировать предложение."

    def _cmd_genetic(self, args: str) -> str:
        if args == "seed":
            self.genetic_search.seed_population()
            return "Популяция создана."
        if args == "evolve":
            result = self.genetic_search.evolve()
            return f"Эволюция завершена. Best fitness: {result['best_fitness']:.3f}"
        return self.genetic_search.get_genetic_summary()

    def _cmd_hot_swap(self, args: str) -> str:
        return self.hot_swapper.get_swap_summary()

    def _cmd_scenario(self, args: str) -> str:
        if not args:
            return self.scenario_tree.get_scenario_summary()
        tree = self.scenario_tree.build_tree(args)
        lines = [f"── Дерево решений: {args[:60]} ──"]
        for b in tree.get("branches", [])[:5]:
            lines.append(f"  › {b.get('decision', '?')} "
                         f"(p={b.get('probability', 0):.0%}, "
                         f"risk={b.get('risk_level', '?')})")
            lines.append(f"    → {b.get('outcome', '')[:100]}")
        return "\n".join(lines)

    def _cmd_fork(self, args: str) -> str:
        if not args:
            return self.counterfactual.get_counterfactual_summary()
        parts = args.split("|")
        decision = parts[0].strip()
        chosen = parts[1].strip() if len(parts) > 1 else "текущий вариант"
        alt = parts[2].strip() if len(parts) > 2 else "альтернатива"
        self.counterfactual.save_fork(decision, chosen, alt)
        return "Развилка сохранена. Через неделю напомню о пересмотре."

    def _cmd_devils_advocate(self, args: str) -> str:
        if not args:
            return self.devils_advocate.get_advocate_summary()
        result = self.devils_advocate.analyze(args)
        lines = [f"── Контраргументы: {args[:60]} ──"]
        for c in result.get("counterarguments", []):
            icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}
            lines.append(f"  {icon.get(c.get('severity', ''), '⚪')} "
                         f"[{c.get('dimension', '')}] {c.get('argument', '')[:150]}")
        return "\n".join(lines)

    def _cmd_autobio_recall(self, args: str) -> str:
        if not args:
            return self.autobio_memory.get_autobio_summary()
        results = self.autobio_memory.recall(args)
        if not results:
            return f"Не нашёл воспоминаний по запросу: {args}"
        lines = [f"── Воспоминания: {args} ──"]
        for r in results[:3]:
            date = r.get("timestamp", "")[:10]
            emotion = r.get("emotion", {}).get("primary", "?")
            lines.append(f"  [{date}] ({emotion}) {r.get('user_input', '')[:100]}")
        return "\n".join(lines)

    def _cmd_add_goal(self, args: str) -> str:
        if not args:
            return "Укажите цель. Например: цель выучить Python / категория learning"
        parts = args.split("/")
        desc = parts[0].strip()
        cat = parts[1].strip() if len(parts) > 1 else "learning"
        gid = self.life_planner.add_goal(desc, category=cat)
        return f"Цель добавлена: {gid}"

    def _cmd_life_goals(self, args: str) -> str:
        return self.life_planner.get_life_summary()

    def _cmd_retrospective(self, args: str) -> str:
        return self.retrospective.get_retro_summary()

    def _cmd_monthly_report(self, args: str) -> str:
        report = self.retrospective.generate_monthly_report()
        lines = [f"── Отчёт за {report.get('period', '?')} ──"]
        lines.append(f"  Взаимодействий: {report.get('stats', {}).get('total_interactions', 0)}")
        lines.append(f"  Средняя оценка: {report.get('stats', {}).get('avg_feedback', 0):.1f}/5")
        lines.append(f"\n  {report.get('narrative', '')[:300]}")
        return "\n".join(lines)

    def _cmd_pre_speech(self, args: str) -> str:
        return self.pre_speech.get_pre_speech_summary()

    def _cmd_complete(self, args: str) -> str:
        if not args:
            return self.symbiotic_input.get_symbiotic_summary()
        completions = self.symbiotic_input.predict_completion(args)
        if not completions:
            return "Нет предсказаний."
        return "Возможные продолжения:\n" + "\n".join(f"  ▸ {c}" for c in completions)

    def _cmd_mental_fuse(self, args: str) -> str:
        if not args:
            return self.mental_fuse.get_mental_fuse_summary()
        check = self.mental_fuse.check(args)
        if check.get("blocked"):
            return "\n".join(check.get("messages", []))
        return "Действие безопасно."

    def _cmd_session(self, args: str) -> str:
        if args == "start":
            self.continuum.start_session("local")
            return "Сессия начата."
        if args == "save":
            info = self.continuum.prepare_handoff()
            if info is None:
                return "Ошибка сохранения сессии."
            return f"Сессия сохранена. {info.get('context_size', 0)} взаимодействий."
        if args == "restore":
            ok = self.continuum.restore_session()
            return "Сессия восстановлена." if ok else "Нет сохранённой сессии."
        return self.continuum.get_context_summary()

    def _cmd_delegate(self, args: str) -> str:
        if not args:
            return self.delegation.get_delegation_summary()
        parts = args.split("/")
        name = parts[0].strip()
        device = parts[1].strip() if len(parts) > 1 else "remote"
        dep = self.delegation.deploy_sub_personality(name, device)
        return f"Делегирован '{name}' на {device} (id: {dep.get('id', '?')})"

    def _cmd_recall_delegate(self, args: str) -> str:
        if not args:
            return "Укажите ID делегации."
        result = self.delegation.reintegrate(args)
        if result.get("success"):
            return f"Опыт делегации '{result['name']}' интегрирован. " \
                   f"Поглощено {result.get('experiences_absorbed', 0)} инсайтов."
        return "Не удалось отозвать делегацию."

    def _cmd_federated(self, args: str) -> str:
        if not args:
            return self.federated_consciousness.get_federated_summary()
        session = self.federated_consciousness.propose_collaboration(
            args, ["local"]
        )
        return f"Федеративная сессия создана: {session.get('id', '?')}"

    def _cmd_personality_audit(self, args: str) -> str:
        audit = self.personality_auditor.audit(force=True)
        report = self.personality_auditor.report()
        if audit and audit.get("alert"):
            report += "\n⚠️ Обнаружен значительный дрейф личности!"
        return report

    def _cmd_resources(self, args: str) -> str:
        cache_info = self.model_cache.status()
        lines = ["=== Resource Status ==="]
        lines.append(f"Model cache: {cache_info['count']}/{cache_info['max']} loaded")
        if cache_info["loaded"]:
            lines.append(f"  Models: {', '.join(cache_info['loaded'])}")
        return "\n".join(lines)

    def _cmd_plugin(self, args: str) -> str:
        parts = args.strip().split(None, 1)
        sub = parts[0].lower() if parts else "list"
        if sub == "list":
            plugins = self.plugins.list_plugins()
            if not plugins:
                return "Нет установленных плагинов"
            lines = [f"── Плагины ({len(plugins)}) ──"]
            for p in plugins:
                status = "✅" if p["loaded"] and p["enabled"] else "⏹️" if not p["enabled"] else "⚠️"
                lines.append(f"  {status} {p['name']} v{p['version']} — {p['description']}")
            return "\n".join(lines)
        if sub == "enable" and len(parts) > 1:
            if self.plugins.enable_plugin(parts[1]):
                return f"Плагин '{parts[1]}' включён"
            return f"Плагин '{parts[1]}' не найден"
        if sub == "disable" and len(parts) > 1:
            if self.plugins.disable_plugin(parts[1]):
                return f"Плагин '{parts[1]}' отключён"
            return f"Плагин '{parts[1]}' не найден"
        if sub == "info" and len(parts) > 1:
            plugin = self.plugins.get_plugin(parts[1])
            if not plugin:
                return f"Плагин '{parts[1]}' не найден"
            cmds = "\n".join(f"  /{k} — {v}" for k, v in plugin.commands.items())
            return (
                f"── {plugin.name} v{plugin.version} ──\n"
                f"  {plugin.description}\n"
                f"  Статус: {'✅ включён' if plugin.enabled else '⏹️ отключён'}\n"
                f"  Загружен: {'да' if plugin._instance else 'нет'}\n"
                f"  Файл: {plugin.module_path}\n"
                f"  Команды:\n{cmds}"
            )
        return (
            "Команды плагинов:\n"
            "  плагин list — список плагинов\n"
            "  плагин enable <имя> — включить\n"
            "  плагин disable <имя> — отключить\n"
            "  плагин info <имя> — подробно"
        )

    def _collect_feedback(self, command: str, result: str) -> None:
        if not CONFIG.FEEDBACK_ENABLED:
            return
        if not command or command == "llm":
            return
        if any(w in result.lower() for w in ["ошибк", "не удалось", "не понимаю"]):
            self.feedback.ask(
                f"command: {command}",
                "Команда выполнена с проблемой. Оцените результат."
            )

    def run_dashboard(self) -> int:
        if CONFIG.DASHBOARD_ENABLED:
            try:
                from ui.windows_app import run_windows_app
                logger.info("Windows dashboard started")
                return run_windows_app(assistant=self)
            except ImportError:
                try:
                    from ui.dashboard import DexDashboard
                    app = DexDashboard(assistant=self)
                    logger.info("Textual dashboard started (fallback)")
                    app.run()
                except ImportError as e:
                    logger.warning(f"Dashboard unavailable: {e}")
                    print("Install PyQt5: pip install PyQt5")
        return 0

    def run_simulator(self, persona: str = "tony_stark", num_commands: int = 10) -> dict[str, Any]:
        from testing.user_simulator import UserSimulator
        sim = UserSimulator(persona=persona, llm_client=self.llm)
        logger.info(f"Starting simulator: {sim.persona_name}")
        report = sim.run_session(self.process_command, num_commands=num_commands)
        print("\n=== Simulation Report ===")
        print(f"Persona: {report['persona']}")
        print(f"Commands: {report['commands']}")
        print(f"Errors provoked: {report['errors_provoked']}")
        print(f"Error rate: {report['error_rate']:.1%}")
        print(f"Helpful rate: {report['helpful_rate']:.1%}")
        return report

    @property
    def uptime(self) -> str:
        delta = datetime.now() - self._start_time
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours}ч {minutes}м {seconds}с"

    def get_conversation_summary(self, n: int = 5) -> list[dict[str, str]]:
        with self._conv_lock:
            return self._conversation_history[-n * 2:]

    def cancel_generation(self) -> None:
        self.cmd_queue.cancel_current()

    def shutdown(self) -> None:
        logger.info("Shutting down Dex...")
        self.cmd_queue.stop()
        self.wake_word.stop()
        self.voice.stop_listening()
        self.camera.stop()
        self.microphone.stop()
        self.watchdog.stop()
        if CONFIG.MESH_ENABLED:
            self.swarm.stop()
        self.secure_memory.close()
        logger.info("Dex shut down")
