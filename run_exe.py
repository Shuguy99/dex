#!/usr/bin/env python3
"""Entry point for PyInstaller-packaged Dex application."""
# type: ignore[import] — standalone mypy skip for core imports

import argparse
import logging
import logging.handlers
import os
import signal
import sys
from pathlib import Path

from config import CONFIG  # type: ignore[import]
from core.assistant import DexAssistant  # type: ignore[import]

logger = logging.getLogger("dex")


def _setup_logging(debug: bool) -> None:
    level = logging.DEBUG if debug else logging.INFO
    log_dir = CONFIG.DATA_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh = logging.handlers.RotatingFileHandler(
        log_dir / "dex.log", maxBytes=5 * 1024 * 1024, backupCount=3,
        encoding="utf-8",
    )
    fh.setFormatter(fmt)

    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(fh)
    root.addHandler(ch)


def _setup_dirs() -> None:
    for sub in ("", "wearable", "plugins", "backups"):
        (CONFIG.DATA_DIR / sub).mkdir(parents=True, exist_ok=True)


def _run_cli(assistant: DexAssistant) -> int:
    print("Dex CLI. Введите 'выход' для завершения.")
    while True:
        try:
            cmd = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if cmd.lower() in ("exit", "quit", "выйти", "выход"):
            break
        if cmd:
            print(assistant.process_command(cmd))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Dex AI Assistant")
    parser.add_argument("--no-voice", action="store_true",
                        help="Отключить голосовой ввод")
    parser.add_argument("--no-gui", action="store_true",
                        help="Запустить без графического интерфейса")
    parser.add_argument("--debug", action="store_true",
                        help="Включить отладочный вывод")
    parser.add_argument("--skip-llm", action="store_true",
                        help="Пропустить инициализацию LLM")
    args = parser.parse_args()

    _setup_logging(args.debug)
    _setup_dirs()

    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
        os.chdir(str(base))
        logger.info("Frozen EXE, base dir: %s", base)
    else:
        logger.info("Running from source")

    logger.info("Запуск Dex AI Assistant v%s...", CONFIG.VERSION)
    assistant = DexAssistant()
    assistant.initialize()

    if args.skip_llm:
        logger.info("Инициализация LLM пропущена (--skip-llm)")
    else:
        assistant.init_llm_background()

    if args.no_voice:
        logger.info("Голосовой ввод отключён (--no-voice)")

    try:
        if args.no_gui:
            logger.info("Режим CLI (--no-gui)")
            return _run_cli(assistant)
        return assistant.run_dashboard()
    except KeyboardInterrupt:
        logger.info("Получен Ctrl+C, завершение...")
        return 0
    except Exception as exc:
        logger.exception("Критическая ошибка: %s", exc)
        print(f"Критическая ошибка: {exc}", file=sys.stderr)
        return 1
    finally:
        assistant.shutdown()
        logger.info("Dex AI Assistant завершил работу")


def _sigterm(_signum, _frame) -> None:
    logger.info("Получен сигнал SIGTERM, завершение...")
    sys.exit(0)


if __name__ == "__main__":
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _sigterm)
    sys.exit(main())
