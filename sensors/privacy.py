import logging

logger = logging.getLogger("dex.sensors.privacy")


class PrivacyManager:
    def __init__(self) -> None:
        self._active = False
        self._components: dict[str, object] = {}

    def register(self, name: str, component) -> None:
        self._components[name] = component

    def enable(self) -> None:
        self._active = True
        for name, comp in self._components.items():
            if hasattr(comp, "enable_privacy_mode"):
                comp.enable_privacy_mode()
                logger.info(f"Privacy: disabled {name}")
        logger.info("Privacy mode ON")

    def disable(self) -> None:
        self._active = False
        for name, comp in self._components.items():
            if hasattr(comp, "disable_privacy_mode"):
                comp.disable_privacy_mode()
                logger.info(f"Privacy: restored {name}")
        logger.info("Privacy mode OFF")

    @property
    def is_active(self) -> bool:
        return self._active

    def toggle(self) -> None:
        if self._active:
            self.disable()
        else:
            self.enable()

    def status_report(self) -> dict[str, bool]:
        return {name: hasattr(comp, "_privacy_mode") and getattr(comp, "_privacy_mode", False)
                for name, comp in self._components.items()}
