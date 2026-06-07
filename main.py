#!/usr/bin/env python3
import argparse
import logging
import time

from config import CONFIG
from core.assistant import DexAssistant
from watchdog.logger import DexLogger

logger = logging.getLogger("dex")


def main():
    parser = argparse.ArgumentParser(description="Dex AI Assistant v3+")
    parser.add_argument("--config", "-c", help="Path to config file")
    parser.add_argument("--voice", "-v", action="store_true", help="Enable voice mode")
    parser.add_argument("--gesture", action="store_true", help="Enable gesture control")
    parser.add_argument("--daemon", "-d", action="store_true", help="Run as daemon")
    parser.add_argument("--command", "-cmd", help="Run a single command and exit")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--dashboard", action="store_true", help="Launch GUI dashboard")
    parser.add_argument("--simulate", "-s", metavar="PERSONA",
                        help="Run user simulator (tony_stark/beginner/hostile/power_user)")
    parser.add_argument("--commands", type=int, default=10,
                        help="Number of simulator commands (default: 10)")
    parser.add_argument("--index-docs", metavar="DIR",
                        help="Index a directory for RAG")
    parser.add_argument("--self-heal", metavar="FILE",
                        help="Run self-diagnosis on a Python file")
    parser.add_argument("--feedback", action="store_true",
                        help="Show feedback stats")
    parser.add_argument("--research", metavar="TOPIC",
                        help="Run research on a topic and exit")
    parser.add_argument("--debate", metavar="TOPIC",
                        help="Run multi-agent debate on a topic and exit")
    parser.add_argument("--mode", metavar="MODE",
                        help="Set personality mode (working/relaxed/creative/джарвис)")
    parser.add_argument("--twin-profile", action="store_true",
                        help="Show digital twin profile")
    parser.add_argument("--predict", action="store_true",
                        help="Show usage predictions")
    parser.add_argument("--meta-report", action="store_true",
                        help="Show meta-learning report")
    parser.add_argument("--ethics-check", metavar="ACTION",
                        help="Ethically evaluate an action")
    parser.add_argument("--jit", metavar="DESCRIPTION",
                        help="JIT-compile an agent from description")
    parser.add_argument("--desktop", action="store_true",
                        help="Show Dex OS contextual desktop")
    parser.add_argument("--cognitive-load", action="store_true",
                        help="Show cognitive load analysis")
    parser.add_argument("--circadian", action="store_true",
                        help="Show circadian adaptation status")
    parser.add_argument("--mesh", action="store_true",
                        help="Show mesh status and discover peers")
    args = parser.parse_args()

    level = logging.DEBUG if args.debug else logging.INFO

    DexLogger(str(CONFIG.LOG_DIR), level=level)

    if args.config:
        CONFIG.__init__(args.config)

    assistant = DexAssistant()
    assistant.initialize()

    # Single command
    if args.command:
        result = assistant.process_command(args.command)
        print(result)
        assistant.shutdown()
        return

    # RAG indexing
    if args.index_docs:
        count = assistant.rag.index_directory(args.index_docs)
        print(f"Indexed {count} chunks from {args.index_docs}")
        assistant.shutdown()
        return

    # Self-heal
    if args.self_heal:
        issues = assistant.self_healer.analyze_code(args.self_heal)
        if issues:
            print(f"Found {len(issues)} issues:")
            for i in issues[:15]:
                print(f"  L{i['line']} [{i['severity']}]: {i['message']}")
        else:
            print("No issues found")
        assistant.shutdown()
        return

    # Feedback stats
    if args.feedback:
        stats = assistant.feedback.get_stats(CONFIG.FEEDBACK_DAYS_HISTORY)
        print(f"Feedback stats ({CONFIG.FEEDBACK_DAYS_HISTORY}d):")
        print(f"  Total ratings: {stats['count']}")
        print(f"  Average: {stats['avg']:.1f}/5")
        print(f"  Range: {stats['min']}-{stats['max']}")
        assistant.shutdown()
        return

    # Simulator
    if args.simulate:
        personae = ["tony_stark", "beginner", "hostile", "power_user"]
        if args.simulate not in personae:
            print(f"Unknown persona: {args.simulate}")
            print(f"Available: {', '.join(personae)}")
            assistant.shutdown()
            return
        assistant.run_simulator(args.simulate, args.commands)
        assistant.shutdown()
        return

    # Personality mode
    if args.mode:
        result = assistant.process_command(f"режим {args.mode}")
        print(result)

    # Research
    if args.research:
        result = assistant.process_command(f"исследуй {args.research}")
        print(result)
        assistant.shutdown()
        return

    # Debate
    if args.debate:
        result = assistant.process_command(f"дебаты {args.debate}")
        print(result)
        assistant.shutdown()
        return

    # Digital twin profile
    if args.twin_profile:
        profile = assistant.digital_twin.get_profile_summary() if hasattr(assistant, 'digital_twin') else "Twin not available"
        print(profile)
        assistant.shutdown()
        return

    # Predictions
    if args.predict:
        result = assistant.process_command("прогноз")
        print(result)
        assistant.shutdown()
        return

    # Meta-learning report
    if args.meta_report:
        result = assistant.process_command("мета обучение")
        print(result)
        assistant.shutdown()
        return

    # Ethics check
    if args.ethics_check:
        result = assistant.process_command(f"этика {args.ethics_check}")
        print(result)
        assistant.shutdown()
        return

    # JIT compile
    if args.jit:
        result = assistant.process_command(f"создай агента {args.jit}")
        print(result)
        assistant.shutdown()
        return

    # Dex OS desktop
    if args.desktop:
        result = assistant.process_command("рабочий стол")
        print(result)
        assistant.shutdown()
        return

    # Cognitive load
    if args.cognitive_load:
        result = assistant.process_command("нагрузка")
        print(result)
        assistant.shutdown()
        return

    # Circadian
    if args.circadian:
        result = assistant.process_command("циркадный")
        print(result)
        assistant.shutdown()
        return

    # Mesh
    if args.mesh:
        result = assistant.process_command("mesh")
        print(result)
        assistant.shutdown()
        return

    # GUI Dashboard
    if args.dashboard:
        assistant.run_dashboard()
        assistant.shutdown()
        return

    # Gesture + Voice / daemon mode
    if args.gesture and hasattr(assistant, 'gesture'):
        import threading
        gesture_thread = threading.Thread(
            target=assistant.gesture.start,
            args=(assistant.process_command, CONFIG.GESTURE_ENABLED),
            daemon=True
        )
        gesture_thread.start()

    if args.voice or args.daemon:
        if assistant.llm.ready:
            assistant.voice.say(
                f"Здравствуйте, сэр. {CONFIG.APP_NAME} версия {CONFIG.VERSION} "
                f"с искусственным интеллектом готов."
            )
        else:
            assistant.voice.say(
                f"Здравствуйте, сэр. {CONFIG.APP_NAME} версия {CONFIG.VERSION} готов. "
                f"Модель ИИ не обнаружена. Работаю в режиме правил."
            )
        assistant.voice.start_background_listening(
            on_command=assistant.process_command
        )
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            assistant.shutdown()
    else:
        # Interactive CLI mode
        llm_status = "✓" if assistant.llm.ready else "✗"
        print(f"{CONFIG.APP_NAME} v{CONFIG.VERSION} | LLM: {llm_status}")
        print("=" * 50)
        print("Commands: помощь, статус, выход")
        print("=" * 50)
        try:
            while True:
                cmd = input("> ").strip()
                if cmd.lower() in ("exit", "quit", "выйти", "выход"):
                    break
                if cmd:
                    result = assistant.process_command(cmd)
                    print(result)
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            assistant.shutdown()


if __name__ == "__main__":
    main()
