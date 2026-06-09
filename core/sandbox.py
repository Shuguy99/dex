import logging
import os
import shutil

logger = logging.getLogger("dex.sandbox")


class SandboxError(PermissionError):
    pass


class FileSandbox:
    def __init__(self, allowed_dirs: list[str], system_paths: list[str]) -> None:
        self._allowed = [os.path.normcase(os.path.normpath(d)) for d in allowed_dirs]
        self._system = [os.path.normcase(os.path.normpath(p)) for p in system_paths]

    def _normalize(self, path: str) -> str:
        return os.path.normcase(os.path.normpath(os.path.abspath(path)))

    def _is_allowed(self, path: str) -> bool:
        normalized = self._normalize(path)
        return any(normalized.startswith(allowed) for allowed in self._allowed)

    def _is_system(self, path: str) -> bool:
        normalized = self._normalize(path)
        return any(normalized.startswith(sys_path) for sys_path in self._system)

    def check_read(self, path: str) -> None:
        if not self._is_allowed(path):
            raise SandboxError(f"Read blocked: {path} is outside allowed directories")

    def check_write(self, path: str) -> None:
        if not self._is_allowed(path):
            raise SandboxError(f"Write blocked: {path} is outside allowed directories")

    def is_dangerous(self, path: str) -> bool:
        return self._is_system(path)

    def open_file(self, path: str) -> str | None:
        normalized = self._normalize(path)
        if not os.path.exists(normalized):
            return None
        self.check_read(normalized)
        os.startfile(normalized)
        logger.info(f"Opened file: {normalized}")
        return normalized

    def read_file(self, path: str) -> str:
        normalized = self._normalize(path)
        self.check_read(normalized)
        with open(normalized, encoding="utf-8") as f:
            return f.read()

    def write_file(self, path: str, content: str) -> None:
        normalized = self._normalize(path)
        self.check_write(normalized)
        os.makedirs(os.path.dirname(normalized), exist_ok=True)
        with open(normalized, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Written: {normalized}")

    def delete_file(self, path: str, confirmed: bool = False) -> None:
        normalized = self._normalize(path)
        self.check_write(normalized)
        if self._is_system(normalized) and not confirmed:
            raise SandboxError(f"Deletion of system file requires confirmation: {normalized}")
        os.remove(normalized)
        logger.info(f"Deleted: {normalized}")

    def move_file(self, src: str, dst: str, confirmed: bool = False) -> None:
        src_norm = self._normalize(src)
        dst_norm = self._normalize(dst)
        self.check_read(src_norm)
        self.check_write(dst_norm)
        if self._is_system(src_norm) and not confirmed:
            raise SandboxError(f"Move of system file requires confirmation: {src_norm}")
        shutil.move(src_norm, dst_norm)
        logger.info(f"Moved: {src_norm} -> {dst_norm}")

    def list_directory(self, path: str) -> list[str]:
        normalized = self._normalize(path)
        self.check_read(normalized)
        return os.listdir(normalized)

    def resolve_path(self, path: str) -> str | None:
        normalized = self._normalize(path)
        if os.path.exists(normalized):
            return normalized
        for base in self._allowed:
            candidate = os.path.join(base, path.lstrip("/\\"))
            if os.path.exists(candidate):
                return os.path.normpath(candidate)
        return None
