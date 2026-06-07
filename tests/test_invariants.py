import shutil
import tempfile
from pathlib import Path

import pytest

pytest.importorskip("hypothesis")
import contextlib

from hypothesis import assume, given
from hypothesis import strategies as st


@pytest.fixture
def sandbox():
    from core.sandbox import FileSandbox
    tmp = Path(tempfile.mkdtemp())
    allowed = tmp / "allowed"
    allowed.mkdir()
    (allowed / "test.txt").write_text("hello")
    sb = FileSandbox(allowed_dirs=[str(allowed)])
    sb._whitelist = {str(allowed.resolve())}
    return sb, tmp


class TestSandboxInvariants:
    @given(path=st.text(alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_./\\- ", min_size=1, max_size=50))
    def test_resolve_path_never_raises(self, path, sandbox):
        sb, _ = sandbox
        with contextlib.suppress(PermissionError, FileNotFoundError):
            sb.resolve_path(path)

    @given(path=st.text(min_size=1, max_size=100))
    def test_is_dangerous_always_bool(self, path, sandbox):
        sb, _ = sandbox
        result = sb.is_dangerous(path)
        assert isinstance(result, bool)

    def test_invariant_whitelist_write(self, sandbox):
        sb, tmp = sandbox
        allowed = tmp / "allowed"
        for f in allowed.iterdir():
            assert sb.validate_write(str(f))

    def test_invariant_whitelist_read(self, sandbox):
        sb, tmp = sandbox
        allowed = tmp / "allowed"
        for f in allowed.iterdir():
            assert sb.validate_read(str(f))

    @given(path=st.text(alphabet="abcdefghijklmnopqrstuvwxyz/", min_size=1, max_size=50))
    def test_outside_whitelist_blocked(self, path, sandbox):
        sb, tmp = sandbox
        assume(".." not in path)
        assume(not path.startswith(str(tmp / "allowed")))
        full = str(tmp / path)
        with contextlib.suppress(PermissionError, FileNotFoundError):
            assert not sb.validate_write(full) or sb.is_dangerous(full)

    def test_invariant_no_escape_via_symlink(self, sandbox):
        sb, tmp = sandbox
        allowed = tmp / "allowed"
        outside = tmp / "outside"
        outside.mkdir()
        link = allowed / "link"
        try:
            link.symlink_to(outside)
            assert not sb.validate_write(str(link / "secret.txt"))
        except (OSError, AttributeError):
            pytest.skip("symlinks not supported")

    def teardown_method(self, method):
        if hasattr(self, "_tmp"):
            shutil.rmtree(str(self._tmp), ignore_errors=True)
