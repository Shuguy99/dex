import logging
import os
import sys

if getattr(sys, 'frozen', False):
    os.chdir(os.path.dirname(sys.executable))
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

from core.assistant import DexAssistant

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    assistant = DexAssistant()
    assistant.initialize()
    ret = assistant.run_dashboard()
    assistant.shutdown()
    sys.exit(ret or 0)
