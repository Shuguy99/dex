import logging
from collections.abc import Callable

logger = logging.getLogger("dex.multiagent.kill_switch")

_KILL_SWITCH_CODE = "стоп код"
_IMMUTABLE = True


class KillSwitch:
    def __init__(self) -> None:
        self._triggered = False
        self._on_kill: list[Callable] = []
        self._phrase = _KILL_SWITCH_CODE

    @property
    def phrase(self) -> str:
        return self._phrase

    @property
    def immutable(self) -> bool:
        return _IMMUTABLE

    def register(self, callback: Callable):
        self._on_kill.append(callback)

    def trigger(self):
        if self._triggered:
            return
        self._triggered = True
        logger.critical("KILL SWITCH TRIGGERED — freezing all subsystems")

        for cb in self._on_kill:
            try:
                cb()
            except Exception as e:
                logger.error(f"Kill callback error: {e}")

        logger.critical("All subsystems frozen. Returning control to user.")

    def check_and_trigger(self, text: str) -> bool:
        if not self._triggered and self._phrase in text.lower():
            self.trigger()
            return True
        return False

    @property
    def is_triggered(self) -> bool:
        return self._triggered

    def reset(self):
        self._triggered = False
        logger.info("Kill switch reset")
