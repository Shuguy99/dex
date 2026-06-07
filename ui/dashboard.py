import logging
import threading
import time

logger = logging.getLogger("dex.ui.dashboard")

try:
    from textual.app import App, ComposeResult
    from textual.containers import Horizontal, Vertical
    from textual.reactive import reactive
    from textual.widget import Widget
    from textual.widgets import Footer, Header, Label, ListItem, ListView, Static
    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False


class AgentStatus(Widget):
    agents = reactive({})

    def render(self) -> str:
        if not self.agents:
            return "No agents"
        lines = ["── Агенты ──"]
        for name, info in self.agents.items():
            status = "●" if info.get("alive") else "○"
            icon = {"voice": "🎤", "memory": "🧠", "file_ops": "📁",
                    "web": "🌐", "code": "💻"}.get(info.get("type", ""), "❓")
            lines.append(f"  {status} {icon} {name}: v{info.get('version', '?')}")
        return "\n".join(lines)


class SensorStatus(Widget):
    sensors = reactive({})

    def render(self) -> str:
        if not self.sensors:
            return "No sensors"
        lines = ["── Сенсоры ──"]
        for name, active in self.sensors.items():
            icon = "●" if active else "○"
            lines.append(f"  {icon} {name}")
        return "\n".join(lines)


class SystemInfo(Widget):
    info = reactive({})

    def render(self) -> str:
        if not self.info:
            return "System info loading..."
        return (
            f"── Система ──\n"
            f"  Версия: {self.info.get('version', '?')}\n"
            f"  Uptime: {self.info.get('uptime', '?')}\n"
            f"  Памяти: {self.info.get('memories', 0)}\n"
            f"  Правил: {self.info.get('rules', 0)}\n"
            f"  Аномалий: {'⚠' if self.info.get('anomaly') else '✓'}"
        )


class LogViewer(Widget):
    logs = reactive([])

    def render(self) -> str:
        if not self.logs:
            return "── Логи (последние) ──\n  (нет событий)"
        lines = ["── Логи (последние) ──"]
        for entry in self.logs[-8:]:
            ts = entry.get("timestamp", "")[11:19] if entry.get("timestamp") else ""
            msg = entry.get("message", "")[:50]
            level = entry.get("level", "INFO")
            lines.append(f"  [{level[:3]}] {ts} {msg}")
        return "\n".join(lines)


class DexDashboard(App):
    TITLE = "Dex Dashboard"
    CSS = """
    Screen {
        layout: grid;
        grid-size: 2 2;
        grid-gutter: 1;
    }
    AgentStatus {
        border: solid green;
        padding: 1;
    }
    SensorStatus {
        border: solid blue;
        padding: 1;
    }
    SystemInfo {
        border: solid yellow;
        padding: 1;
    }
    LogViewer {
        border: solid white;
        padding: 1;
    }
    """

    def __init__(self, assistant=None) -> None:
        super().__init__()
        self._assistant = assistant
        self._refresh_thread: threading.Thread | None = None
        self._running = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield AgentStatus()
            yield SensorStatus()
        with Horizontal():
            yield SystemInfo()
            yield LogViewer()
        yield Footer()

    def on_mount(self):
        self._running = True
        self._refresh_thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self._refresh_thread.start()

    def _refresh_loop(self):
        while self._running:
            try:
                self.update_widgets()
            except Exception as e:
                logger.error(f"Dashboard refresh error: {e}")
            time.sleep(2)

    def update_widgets(self):
        if not self._assistant:
            return
        a = self._assistant

        agent_status = self.query_one(AgentStatus)
        agents = a.orchestrator.check_health()
        agent_status.agents = {
            name: {"type": agent.type, "alive": agent.alive, "version": agent.version}
            for name, agent in a.orchestrator._agents.items()
        }

        sensor_status = self.query_one(SensorStatus)
        sensor_status.sensors = {
            "camera": a.camera._active if hasattr(a.camera, '_active') else False,
            "microphone": a.microphone._active if hasattr(a.microphone, '_active') else False,
            "privacy mode": a.privacy.is_active
        }

        sys_info = self.query_one(SystemInfo)
        sys_info.info = {
            "version": a._config.VERSION,
            "uptime": a.uptime,
            "memories": a.vector_memory.count(),
            "rules": len(a.rule_engine.get_active_rules()),
            "anomaly": a.watchdog.has_anomaly,
            "agents": agents
        }

        log_viewer = self.query_one(LogViewer)
        log_viewer.logs = self._get_recent_logs()

    def _get_recent_logs(self) -> list[dict]:
        log_path = self._assistant._config.LOG_DIR / "dex.log"
        if not log_path.exists():
            return []
        lines = []
        try:
            with open(log_path, encoding="utf-8") as f:
                all_lines = f.readlines()
                for line in all_lines[-20:]:
                    lines.append({
                        "timestamp": line[:19] if len(line) > 19 else "",
                        "level": line.split("]")[1].strip() if "]" in line else "INFO",
                        "message": line.strip()
                    })
        except Exception:
            pass
        return lines

    def on_unmount(self):
        self._running = False
