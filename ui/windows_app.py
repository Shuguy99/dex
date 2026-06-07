import configparser
import contextlib
import logging
import sys
import threading
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("dex.ui.windows_app")

try:
    from PyQt5.QtCore import Qt, QTimer, pyqtSignal
    from PyQt5.QtGui import QColor, QFont, QTextCursor
    from PyQt5.QtWidgets import (
        QAction,
        QApplication,
        QCheckBox,
        QComboBox,
        QFrame,
        QGridLayout,
        QGroupBox,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLineEdit,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMenu,
        QMenuBar,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QScrollArea,
        QSlider,
        QSplitter,
        QStackedWidget,
        QStatusBar,
        QStyle,
        QSystemTrayIcon,
        QTableWidget,
        QTableWidgetItem,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )

    from core.async_engine import Command
    PYSIDE_AVAILABLE = True
except ImportError:
    PYSIDE_AVAILABLE = False

STYLESHEET = """
QMainWindow { background-color: #1e1e2e; }
QWidget { background-color: #1e1e2e; color: #cdd6f4; font-family: 'Segoe UI'; font-size: 10pt; }
QPushButton { background-color: #313244; border: 1px solid #45475a; border-radius: 4px; padding: 6px 14px; color: #cdd6f4; min-height: 24px; }
QPushButton:hover { background-color: #45475a; }
QPushButton:pressed { background-color: #585b70; }
QPushButton#nav_btn { text-align: left; padding: 10px 16px; border-radius: 0; border: none; font-size: 11pt; border-left: 3px solid transparent; }
QPushButton#nav_btn:hover { background-color: #313244; border-left: 3px solid #89b4fa; }
QPushButton#nav_btn:checked { background-color: #313244; border-left: 3px solid #89b4fa; font-weight: bold; color: #89b4fa; }
QPushButton#cmd_btn { background-color: #89b4fa; color: #1e1e2e; border: none; border-radius: 4px; padding: 8px 16px; }
QPushButton#cmd_btn:hover { background-color: #b4d0fb; }
QPushButton#cmd_btn:disabled { background-color: #45475a; color: #6c7086; }
QPushButton#danger_btn { background-color: #f38ba8; color: #1e1e2e; border: none; border-radius: 4px; padding: 8px 16px; }
QPushButton#danger_btn:hover { background-color: #f5a7c1; }
QPushButton#stop_btn { background-color: #f9e2af; color: #1e1e2e; border: none; border-radius: 4px; padding: 8px 16px; }
QPushButton#stop_btn:hover { background-color: #f5e0b5; }
QLineEdit { background-color: #313244; border: 1px solid #45475a; border-radius: 4px; padding: 8px 12px; color: #cdd6f4; font-size: 11pt; }
QLineEdit:focus { border-color: #89b4fa; }
QLineEdit:disabled { background-color: #181825; color: #585b70; }
QTextEdit { background-color: #181825; border: 1px solid #313244; border-radius: 4px; padding: 8px; color: #cdd6f4; }
QTextEdit#output_area { background-color: #11111b; border: none; font-family: 'Consolas'; font-size: 10pt; padding: 12px; }
QListWidget { background-color: #11111b; border: 1px solid #313244; border-radius: 4px; }
QListWidget::item { padding: 6px 10px; border-radius: 3px; }
QListWidget::item:hover { background-color: #313244; }
QGroupBox { border: 1px solid #45475a; border-radius: 6px; margin-top: 12px; padding: 16px 12px 12px; font-weight: bold; color: #89b4fa; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
QStatusBar { background-color: #181825; border-top: 1px solid #313244; color: #a6adc8; font-size: 9pt; }
QProgressBar { border: 1px solid #45475a; border-radius: 3px; text-align: center; color: #cdd6f4; background-color: #313244; }
QProgressBar::chunk { background-color: #89b4fa; border-radius: 2px; }
QTableWidget { background-color: #11111b; border: 1px solid #313244; gridline-color: #313244; border-radius: 4px; }
QHeaderView::section { background-color: #181825; color: #89b4fa; padding: 6px; border: none; border-bottom: 1px solid #313244; }
QComboBox { background-color: #313244; border: 1px solid #45475a; border-radius: 4px; padding: 6px 12px; min-width: 120px; }
QScrollArea { border: none; }
QFrame#sidebar { background-color: #181825; border-right: 1px solid #313244; }
"""

COLORS = {
    "info": "#89b4fa", "success": "#a6e3a1",
    "warn": "#f9e2af", "error": "#f38ba8",
    "cmd": "#cba6f7", "system": "#94e2d5",
}

CONFIG_PATH = Path("data/config_gui.ini")


class DexWindowsApp(QMainWindow):
    status_changed = pyqtSignal(str, str)

    def __init__(self, assistant=None) -> None:
        super().__init__()
        self.assistant = assistant
        self._running = True

        self.setWindowTitle("Dex AI Assistant")
        self.setMinimumSize(1100, 720)
        self.resize(1280, 800)
        self.setStyleSheet(STYLESHEET)

        self._load_settings()
        self._setup_menu()
        self._setup_ui()
        self._setup_tray()
        self._setup_timers()

        self._log("Dex запускается...", "system")
        self._llm_init_done = False
        self._init_progress()

        self.status_changed.connect(self._on_status)

    def _init_progress(self):
        self._bar.setValue(10)
        self._bar_label.setText("Инициализация модулей...")
        QTimer.singleShot(200, self._finish_init)

    def _finish_init(self):
        self._bar.setValue(60)
        self._bar_label.setText("Загрузка LLM в фоне...")
        if self.assistant:
            def on_llm(ok):
                self._llm_init_done = True
                self._bar.setValue(100)
                self._bar_label.setText("LLM готова" if ok else "LLM не найдена (rule-based)")
                self._input.setEnabled(True)
                self._send_btn.setEnabled(True)
                if ok:
                    self._log("LLM загружена. Dex готов к работе.", "success")
                else:
                    self._log("LLM не отвечает. Работаю в офлайн-режиме.", "warn")
                QTimer.singleShot(2000, self._hide_bar)
            self.assistant.init_llm_background(callback=on_llm)
        else:
            self._bar.setValue(100)
            self._bar_label.setText("Готово")
            self._input.setEnabled(True)
            self._send_btn.setEnabled(True)
            QTimer.singleShot(1000, self._hide_bar)

    def _hide_bar(self):
        self._bar.hide()
        self._bar_label.hide()

    def _on_status(self, msg, level):
        self._log(msg, level)

    def _load_settings(self):
        self._settings = {"volume": 70, "model": "qwen2.5:14b", "mode": "auto",
                          "autostart": False, "notify": True}
        try:
            if CONFIG_PATH.exists():
                cfg = configparser.ConfigParser()
                cfg.read(CONFIG_PATH)
                if "gui" in cfg:
                    s = cfg["gui"]
                    for k in self._settings:
                        if k in s:
                            if isinstance(self._settings[k], bool):
                                self._settings[k] = s.getboolean(k)
                            elif isinstance(self._settings[k], int):
                                self._settings[k] = s.getint(k)
                            else:
                                self._settings[k] = s.get(k)
        except Exception:
            pass

    def _save_settings(self):
        try:
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            cfg = configparser.ConfigParser()
            cfg["gui"] = {k: str(v) for k, v in self._settings.items()}
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                cfg.write(f)
        except Exception as e:
            logger.error(f"Settings save: {e}")

    def _setup_menu(self):
        mb = self.menuBar()
        fm = mb.addMenu("Файл")
        fm.addAction("Перезапустить", self._restart_dex)
        fm.addAction("Выход", self.close)

        vm = mb.addMenu("Вид")
        for name, idx in [("Чат", 0), ("Статус", 1), ("Диагностика", 2), ("Настройки", 3)]:
            act = QAction(name, self)
            act.triggered.connect(lambda checked, i=idx: self._switch_page(i))
            vm.addAction(act)

        tm = mb.addMenu("Инструменты")
        tm.addAction("Диагностика потоков", self._show_diagnostics)
        tm.addAction("Аудит личности", lambda: self._run_cmd("аудит"))
        tm.addAction("Статус ресурсов", lambda: self._run_cmd("ресурсы"))
        tm.addAction("Проверить Ollama", self._check_ollama)

        mb.addMenu("Помощь").addAction("О программе", self._show_about)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        ml = QHBoxLayout(central)
        ml.setContentsMargins(0, 0, 0, 0)
        ml.setSpacing(0)

        # Sidebar
        sb = QFrame()
        sb.setObjectName("sidebar")
        sb.setFixedWidth(180)
        sbl = QVBoxLayout(sb)
        sbl.setContentsMargins(0, 0, 0, 0)
        sbl.setSpacing(0)
        logo = QLabel("  DEX")
        logo.setStyleSheet("font-size: 18pt; font-weight: bold; color: #89b4fa; padding: 16px 12px; border-bottom: 1px solid #313244;")
        sbl.addWidget(logo)
        self._nav_btns = []
        for name, idx in [("Чат", 0), ("Статус", 1), ("Диагностика", 2), ("Настройки", 3)]:
            btn = QPushButton(f"  {name}")
            btn.setObjectName("nav_btn")
            btn.setCheckable(True)
            btn.setChecked(idx == 0)
            btn.clicked.connect(lambda checked, i=idx: self._switch_page(i))
            sbl.addWidget(btn)
            self._nav_btns.append(btn)
        sbl.addStretch()
        self._llm_status_label = QLabel("  LLM: загрузка...")
        self._llm_status_label.setStyleSheet("color: #f9e2af; padding: 8px; font-size: 9pt; border-top: 1px solid #313244;")
        sbl.addWidget(self._llm_status_label)
        ml.addWidget(sb)

        # Stack
        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_chat_page())
        self._stack.addWidget(self._build_status_page())
        self._stack.addWidget(self._build_diagnostics_page())
        self._stack.addWidget(self._build_settings_page())
        ml.addWidget(self._stack, 1)

        self._sb = QStatusBar()
        self.setStatusBar(self._sb)
        self._status_lbl = QLabel("Ready")
        self._sb.addWidget(self._status_lbl)
        self._ollama_lbl = QLabel()
        self._sb.addPermanentWidget(self._ollama_lbl)

    def _build_chat_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Progress bar
        bar_layout = QHBoxLayout()
        self._bar = QProgressBar()
        self._bar.setMaximum(100)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(6)
        self._bar_label = QLabel("")
        self._bar_label.setStyleSheet("color: #a6adc8; font-size: 9pt;")
        bar_layout.addWidget(self._bar, 1)
        bar_layout.addWidget(self._bar_label)
        layout.addLayout(bar_layout)

        # Toolbar
        tb = QHBoxLayout()
        for name, cmd in [("Статус", "статус"), ("Помощь", "помощь")]:
            btn = QPushButton(name)
            btn.setObjectName("cmd_btn")
            btn.clicked.connect(lambda checked, c=cmd: self._run_cmd(c))
            tb.addWidget(btn)
        stop_btn = QPushButton("Стоп")
        stop_btn.setObjectName("stop_btn")
        stop_btn.clicked.connect(self._stop_generation)
        tb.addWidget(stop_btn)
        tb.addStretch()
        self._thinking_lbl = QLabel("")
        self._thinking_lbl.setStyleSheet("color: #f9e2af; font-style: italic;")
        tb.addWidget(self._thinking_lbl)
        layout.addLayout(tb)

        self._output = QTextEdit()
        self._output.setObjectName("output_area")
        self._output.setReadOnly(True)
        layout.addWidget(self._output, 1)

        # Input
        il = QHBoxLayout()
        self._input = QLineEdit()
        self._input.setPlaceholderText("Введите команду... (Enter для отправки)")
        self._input.returnPressed.connect(self._on_input)
        self._input.setEnabled(False)
        il.addWidget(self._input, 1)
        self._send_btn = QPushButton("Отправить")
        self._send_btn.setObjectName("cmd_btn")
        self._send_btn.clicked.connect(self._on_input)
        self._send_btn.setEnabled(False)
        self._send_btn.setFixedWidth(120)
        il.addWidget(self._send_btn)
        layout.addLayout(il)
        return page

    def _build_status_page(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        left = QVBoxLayout()
        left.setSpacing(12)
        sg = QGroupBox("Система")
        sgrid = QGridLayout(sg)
        self._sys = {}
        for i, (k, lbl) in enumerate([("version", "Версия"), ("uptime", "Uptime"),
                                       ("memories", "Воспоминаний"), ("rules", "Правил")]):
            sgrid.addWidget(QLabel(lbl + ":"), i, 0)
            v = QLabel("--")
            v.setStyleSheet("color: #89b4fa; font-weight: bold;")
            sgrid.addWidget(v, i, 1)
            self._sys[k] = v
        left.addWidget(sg)

        ag = QGroupBox("Агенты")
        self._agent_list = QListWidget()
        self._agent_list.setMaximumHeight(180)
        ag_layout = QVBoxLayout(ag)
        ag_layout.addWidget(self._agent_list)
        left.addWidget(ag)

        sensg = QGroupBox("Сенсоры")
        sensgrid = QGridLayout(sensg)
        self._sensors = {}
        for i, name in enumerate(["Микрофон", "Камера", "Приватность", "Жесты"]):
            sensgrid.addWidget(QLabel(name + ":"), i, 0)
            v = QLabel("○")
            sensgrid.addWidget(v, i, 1)
            self._sensors[name] = v
        left.addWidget(sensg)
        layout.addLayout(left, 1)

        right = QVBoxLayout()
        right.setSpacing(12)
        lg = QGroupBox("Логи")
        self._log_view = QTextEdit()
        self._log_view.setReadOnly(True)
        ll = QVBoxLayout(lg)
        ll.addWidget(self._log_view)
        right.addWidget(lg)

        mg = QGroupBox("Модули онлайн")
        self._mod_table = QTableWidget(0, 3)
        self._mod_table.setHorizontalHeaderLabels(["Модуль", "Статус", "Данных"])
        self._mod_table.horizontalHeader().setStretchLastSection(True)
        self._mod_table.setMaximumHeight(180)
        modl = QVBoxLayout(mg)
        modl.addWidget(self._mod_table)
        right.addWidget(mg, 1)
        layout.addLayout(right, 2)
        return page

    def _build_diagnostics_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        tb = QHBoxLayout()
        refresh_btn = QPushButton("Обновить")
        refresh_btn.setObjectName("cmd_btn")
        refresh_btn.clicked.connect(self._refresh_diagnostics)
        tb.addWidget(refresh_btn)
        tb.addStretch()
        layout.addLayout(tb)

        self._diag_output = QTextEdit()
        self._diag_output.setReadOnly(True)
        self._diag_output.setStyleSheet("font-family: 'Consolas'; font-size: 9pt;")
        layout.addWidget(self._diag_output, 1)
        return page

    def _build_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        sw = QWidget()
        sl = QVBoxLayout(sw)
        sl.setSpacing(16)

        g1 = QGroupBox("Личность")
        g1g = QGridLayout(g1)
        g1g.addWidget(QLabel("Режим:"), 0, 0)
        self._mode_cb = QComboBox()
        self._mode_cb.addItems(["auto", "working", "relaxed", "creative", "professional"])
        self._mode_cb.setCurrentText(self._settings["mode"])
        self._mode_cb.currentTextChanged.connect(self._on_mode_change)
        g1g.addWidget(self._mode_cb, 0, 1)
        sl.addWidget(g1)

        g2 = QGroupBox("Языковая модель")
        g2g = QGridLayout(g2)
        g2g.addWidget(QLabel("Активная модель:"), 0, 0)
        self._model_cb = QComboBox()
        self._model_cb.setEditable(True)
        self._model_cb.addItems(["qwen2.5:14b", "deepseek-coder-v2", "llama3.1:8b", "mistral:7b", "llama3.2:3b", "llama3.2:1b"])
        self._model_cb.setCurrentText(self._settings["model"])
        g2g.addWidget(self._model_cb, 0, 1)
        reload_btn = QPushButton("Перезагрузить")
        reload_btn.setObjectName("cmd_btn")
        reload_btn.clicked.connect(self._reload_model)
        g2g.addWidget(reload_btn, 1, 0, 1, 2)
        self._model_status = QLabel("")
        self._model_status.setStyleSheet("color: #a6adc8;")
        g2g.addWidget(self._model_status, 2, 0, 1, 2)

        g2g.addWidget(QLabel("Установить модель:"), 3, 0)
        self._install_input = QLineEdit()
        self._install_input.setPlaceholderText("например, llama3.2:3b")
        g2g.addWidget(self._install_input, 3, 1)
        install_btn = QPushButton("Установить")
        install_btn.setObjectName("cmd_btn")
        install_btn.clicked.connect(self._install_model)
        g2g.addWidget(install_btn, 4, 0, 1, 2)
        self._install_status = QLabel("")
        self._install_status.setStyleSheet("color: #a6adc8;")
        g2g.addWidget(self._install_status, 5, 0, 1, 2)
        refresh_list_btn = QPushButton("Обновить список моделей")
        refresh_list_btn.setObjectName("cmd_btn")
        refresh_list_btn.clicked.connect(self._refresh_model_list)
        g2g.addWidget(refresh_list_btn, 6, 0, 1, 2)
        sl.addWidget(g2)

        g3 = QGroupBox("Аудио")
        g3g = QGridLayout(g3)
        g3g.addWidget(QLabel("Громкость:"), 0, 0)
        self._vol_slider = QSlider(Qt.Horizontal)
        self._vol_slider.setRange(0, 100)
        self._vol_slider.setValue(self._settings["volume"])
        self._vol_slider.valueChanged.connect(lambda v: self._settings.update({"volume": v}))
        g3g.addWidget(self._vol_slider, 0, 1)
        self._vol_lbl = QLabel(f"{self._settings['volume']}%")
        self._vol_lbl.setStyleSheet("color: #89b4fa; font-weight: bold;")
        self._vol_slider.valueChanged.connect(lambda v: self._vol_lbl.setText(f"{v}%"))
        g3g.addWidget(self._vol_lbl, 0, 2)
        sl.addWidget(g3)

        g4 = QGroupBox("Сенсоры")
        g4g = QGridLayout(g4)
        self._cam_chk = QCheckBox("Камера")
        self._cam_chk.toggled.connect(lambda v: self._run_cmd("камера вкл" if v else "камера выкл"))
        g4g.addWidget(self._cam_chk, 0, 0)
        self._gest_chk = QCheckBox("Жесты")
        self._gest_chk.toggled.connect(lambda v: self._run_cmd("жесты вкл" if v else "жесты выкл"))
        g4g.addWidget(self._gest_chk, 1, 0)
        self._silent_chk = QCheckBox("Тихий режим")
        self._silent_chk.toggled.connect(lambda v: self._run_cmd("тихий вкл" if v else "тихий выкл"))
        g4g.addWidget(self._silent_chk, 2, 0)
        sl.addWidget(g4)

        g5 = QGroupBox("Запуск")
        self._startup_chk = QCheckBox("Автозапуск с Windows")
        self._startup_chk.setChecked(self._settings["autostart"])
        self._startup_chk.toggled.connect(self._toggle_autostart)
        sl.addWidget(g5)
        g5_layout = QVBoxLayout(g5)
        g5_layout.addWidget(self._startup_chk)

        sl.addStretch()
        scroll.setWidget(sw)
        layout.addWidget(scroll, 1)

        bar = QHBoxLayout()
        bar.addStretch()
        save_lbl = QLabel("")
        save_lbl.setStyleSheet("color: #a6adc8;")
        bar.addWidget(save_lbl)
        save_btn = QPushButton("Сохранить")
        save_btn.setObjectName("cmd_btn")
        save_btn.clicked.connect(lambda: self._do_save(save_lbl))
        bar.addWidget(save_btn)
        layout.addLayout(bar)
        return page

    def _on_mode_change(self, mode):
        self._settings["mode"] = mode
        self._run_cmd(f"режим {mode}")

    def _reload_model(self):
        model = self._model_cb.currentText()
        self._settings["model"] = model
        self._model_status.setText(f"Перезагрузка {model}...")
        self._model_status.setStyleSheet("color: #f9e2af;")
        if self.assistant:
            def _do():
                self.assistant.llm.default_model = model
                self.assistant._llm_ready = False
                self.assistant.init_llm_background(callback=lambda ok:
                    self.status_changed.emit(f"Модель {model}: {'готова' if ok else 'недоступна'}", "success" if ok else "warn"))
            threading.Thread(target=_do, daemon=True).start()
        self._model_status.setText(f"Модель {model} загружается...")

    def _install_model(self):
        model_name = self._install_input.text().strip()
        if not model_name:
            self._install_status.setText("Введите название модели")
            self._install_status.setStyleSheet("color: #f38ba8;")
            return
        self._install_status.setText(f"Установка {model_name}...")
        self._install_status.setStyleSheet("color: #f9e2af;")
        self._install_input.setEnabled(False)

        def _do():
            ok = self.assistant.llm.pull_model(model_name)
            self.assistant.gui_scheduler.schedule(lambda: self._on_install_done(model_name, ok))
        threading.Thread(target=_do, daemon=True).start()

    def _on_install_done(self, model_name, ok):
        self._install_input.setEnabled(True)
        if ok:
            self._install_status.setText(f"✓ {model_name} установлена")
            self._install_status.setStyleSheet("color: #a6e3a1;")
            self._refresh_model_list()
        else:
            self._install_status.setText(f"✗ Ошибка установки {model_name}")
            self._install_status.setStyleSheet("color: #f38ba8;")

    def _refresh_model_list(self):
        if not self.assistant:
            return
        self._model_cb.clear()
        models = getattr(self.assistant.llm, "models", [])
        if models:
            self._model_cb.addItems(models)
            current = self._settings.get("model", "")
            if current in models:
                self._model_cb.setCurrentText(current)
        else:
            self._model_cb.addItems(["qwen2.5:14b", "deepseek-coder-v2", "llama3.1:8b", "mistral:7b", "llama3.2:3b", "llama3.2:1b"])
            self._model_cb.setCurrentText(self._settings["model"])

    def _toggle_autostart(self, enabled):
        self._settings["autostart"] = enabled
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                 r"Software\Microsoft\Windows\CurrentVersion\Run",
                                 0, winreg.KEY_SET_VALUE)
            if enabled:
                script = Path(sys.executable).parent / "pythonw.exe"
                if not script.exists():
                    script = sys.executable
                winreg.SetValueEx(key, "DexAssistant", 0, winreg.REG_SZ,
                                  f'"{script}" "{Path("main.py").absolute()}" --dashboard')
            else:
                with contextlib.suppress(FileNotFoundError):
                    winreg.DeleteValue(key, "DexAssistant")
            winreg.CloseKey(key)
        except Exception as e:
            logger.error(f"Autostart: {e}")

    def _do_save(self, lbl):
        self._save_settings()
        lbl.setText("Сохранено")
        QTimer.singleShot(2000, lambda: lbl.setText(""))

    def _setup_tray(self):
        self._tray = QSystemTrayIcon(self)
        self._tray.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        self._tray.setToolTip("Dex AI Assistant")
        m = QMenu()
        m.addAction("Показать", self.show)
        m.addAction("Скрыть", self.hide)
        m.addSeparator()
        m.addAction("Выход", lambda: (self._tray.hide(), self.close()))
        self._tray.setContextMenu(m)
        self._tray.activated.connect(lambda r: self.show() if r == QSystemTrayIcon.DoubleClick else None)

    def _setup_timers(self):
        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self._refresh)
        self._refresh_timer.start(3000)
        QTimer.singleShot(1000, self._check_ollama)

    def _switch_page(self, idx):
        self._stack.setCurrentIndex(idx)
        for i, btn in enumerate(self._nav_btns):
            btn.setChecked(i == idx)

    def _on_input(self):
        text = self._input.text().strip()
        if not text:
            return
        self._input.clear()
        self._run_cmd(text)

    def _run_cmd(self, text):
        self._log(f"> {text}", "cmd")
        if not self.assistant:
            self._log("Ассистент не инициализирован", "error")
            return
        self._thinking_lbl.setText("Декс думает...")
        self._send_btn.setEnabled(False)
        self._input.setEnabled(False)
        self.assistant.cmd_queue.post(Command(
            text=text,
            callback=lambda r: self.assistant.gui_scheduler.schedule(lambda: self._on_result(text, r)),
            error_callback=lambda e: self.assistant.gui_scheduler.schedule(lambda: self._log(f"Ошибка: {e}", "error")),
        ))

    def _on_result(self, _cmd, result):
        self._log(str(result), "info")
        self._thinking_lbl.setText("")
        self._send_btn.setEnabled(True)
        self._input.setEnabled(True)
        self._input.setFocus()

    def _stop_generation(self):
        if self.assistant:
            self.assistant.cancel_generation()
            self._log("[Прервано пользователем]", "warn")
            self._thinking_lbl.setText("")
            self._send_btn.setEnabled(True)
            self._input.setEnabled(True)

    def _log(self, msg, level="info"):
        color = COLORS.get(level, "#cdd6f4")
        ts = datetime.now().strftime("%H:%M:%S")
        html = f'<span style="color:{color};">[{ts}] {msg}</span><br>'
        self._output.append(html)
        cursor = self._output.textCursor()
        cursor.movePosition(QTextCursor.End)
        self._output.setTextCursor(cursor)
        if hasattr(self, "_log_view"):
            self._log_view.append(html)

    def _refresh(self):
        if not self.assistant:
            return
        a = self.assistant
        self._status_lbl.setText(f"Uptime: {getattr(a, 'uptime', '?')} | "
                                  f"Queue: {a.cmd_queue.pending_count()}")
        self._refresh_sys()
        self._refresh_sensors()
        self._refresh_agents()
        self._refresh_mod_table()
        self._refresh_diagnostics()
        # LLM status
        if a._llm_ready:
            self._llm_status_label.setText(f"  LLM: {getattr(a.llm, 'default_model', '?')}")
            self._llm_status_label.setStyleSheet("color: #a6e3a1; padding: 8px; font-size: 9pt; border-top: 1px solid #313244;")
        elif self._llm_init_done:
            self._llm_status_label.setText("  LLM: offline")
            self._llm_status_label.setStyleSheet("color: #f38ba8; padding: 8px; font-size: 9pt; border-top: 1px solid #313244;")

    def _refresh_sys(self):
        if not self.assistant:
            return
        a = self.assistant
        vals = {
            "version": getattr(a._config, "VERSION", "?"),
            "uptime": getattr(a, "uptime", "?"),
            "memories": str(a.vector_memory.count()) if hasattr(a, "vector_memory") and hasattr(a.vector_memory, "count") else "?",
            "rules": str(len(getattr(getattr(a, "rule_engine", None), "_rules", []))),
        }
        for k, v in vals.items():
            if k in self._sys:
                self._sys[k].setText(v)

    def _refresh_sensors(self):
        if not self.assistant:
            return
        a = self.assistant
        states = {
            "Микрофон": hasattr(a, "microphone") and getattr(a.microphone, "_active", False),
            "Камера": hasattr(a, "camera") and getattr(a.camera, "_active", False),
            "Приватность": not getattr(getattr(a, "privacy", None), "is_active", False),
            "Жесты": hasattr(a, "gesture") and hasattr(a.gesture, "_active") and a.gesture._active,
        }
        for name, active in states.items():
            if name in self._sensors:
                self._sensors[name].setText("●" if active else "○")
                self._sensors[name].setStyleSheet(f"color: {'#a6e3a1' if active else '#f38ba8'}; font-weight: bold; font-size: 14pt;")

    def _refresh_agents(self):
        if not self.assistant or not hasattr(self.assistant, "orchestrator"):
            return
        self._agent_list.clear()
        try:
            agents = self.assistant.orchestrator.check_health() if hasattr(self.assistant.orchestrator, "check_health") else {}
            if not agents:
                self._agent_list.addItem("No agents")
                return
            for name, info in agents.items():
                s = "●" if info.get("alive") else "○"
                self._agent_list.addItem(f"  {s} {name} v{info.get('version', '?')}")
        except Exception:
            self._agent_list.addItem("Agent status unavailable")

    def _refresh_mod_table(self):
        if not self.assistant:
            return
        a = self.assistant
        data = [
            ("Meta-Learner", "meta_learner", "data/meta_learning"),
            ("Ethical CP", "co_processor", "data/ethics"),
            ("JIT", "jit_compiler", "data/jit_agents"),
            ("Circadian", "circadian", "data/psych"),
            ("Cognitive", "cognitive_load", "data/psych"),
        ]
        self._mod_table.setRowCount(len(data))
        for i, (name, attr, ddir) in enumerate(data):
            mod = getattr(a, attr, None)
            self._mod_table.setItem(i, 0, QTableWidgetItem(name))
            si = QTableWidgetItem("●" if mod else "○")
            si.setForeground(QColor("#a6e3a1" if mod else "#585b70"))
            self._mod_table.setItem(i, 1, si)
            dp = Path(ddir)
            self._mod_table.setItem(i, 2, QTableWidgetItem(str(len(list(dp.glob("*")))) if dp.exists() else "0"))

    def _refresh_diagnostics(self):
        if not self.assistant or not hasattr(self, "_diag_output"):
            return
        report = self.assistant.diagnostics.report()
        self._diag_output.setText(report)

    def _show_diagnostics(self):
        self._switch_page(2)

    def _check_ollama(self):
        try:
            import urllib.request
            urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
            self._ollama_lbl.setText("Ollama: ●")
            self._ollama_lbl.setStyleSheet("color: #a6e3a1; font-weight: bold;")
        except Exception:
            self._ollama_lbl.setText("Ollama: ○")
            self._ollama_lbl.setStyleSheet("color: #f38ba8; font-weight: bold;")

    def _restart_dex(self):
        self._log("Перезапуск...", "system")

    def _show_about(self):
        QMessageBox.about(self, "Dex AI Assistant v3+",
            "Dex — AI-ассистент\nПолностью локальное исполнение\n(Ollama + ChromaDB)\n\n© 2026")

    def closeEvent(self, event):
        self._running = False
        if self._tray:
            self._tray.hide()
        if self.assistant:
            self.assistant.shutdown()
        event.accept()


def run_windows_app(assistant=None):
    app = QApplication(sys.argv)
    window = DexWindowsApp(assistant=assistant)
    window.show()
    if window._tray:
        window._tray.show()
    return app.exec()
