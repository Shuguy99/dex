import contextlib
import os
import shutil
import tempfile
from pathlib import Path

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

pytest.importorskip("hypothesis")


_tmp_dirs: set[str] = set()


def _make_sandbox():
    from core.sandbox import FileSandbox
    tmp = Path(tempfile.mkdtemp())
    _tmp_dirs.add(str(tmp))
    allowed = tmp / "allowed"
    allowed.mkdir()
    (allowed / "test.txt").write_text("hello")
    sb = FileSandbox(allowed_dirs=[str(allowed)], system_paths=[])
    sb._whitelist = {str(allowed.resolve())}
    return sb, tmp


class TestSandboxInvariants:
    def teardown_method(self, method):
        for d in list(_tmp_dirs):
            try:
                shutil.rmtree(d, ignore_errors=True)
                _tmp_dirs.discard(d)
            except Exception:
                pass

    @given(path=st.text(alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_./\\- ", min_size=1, max_size=50))
    def test_resolve_path_never_raises(self, path):
        sb, _ = _make_sandbox()
        with contextlib.suppress(PermissionError, FileNotFoundError):
            sb.resolve_path(path)

    @given(path=st.text(min_size=1, max_size=100))
    @settings(deadline=None)
    def test_is_dangerous_always_bool(self, path):
        sb, _ = _make_sandbox()
        result = sb.is_dangerous(path)
        assert isinstance(result, bool)

    def test_invariant_whitelist_write(self):
        sb, tmp = _make_sandbox()
        allowed = tmp / "allowed"
        for f in allowed.iterdir():
            assert sb.check_write(str(f)) is None

    def test_invariant_whitelist_read(self):
        sb, tmp = _make_sandbox()
        allowed = tmp / "allowed"
        for f in allowed.iterdir():
            assert sb.check_read(str(f)) is None

    @given(path=st.text(alphabet="abcdefghijklmnopqrstuvwxyz/", min_size=1, max_size=50))
    def test_outside_whitelist_blocked(self, path):
        from core.sandbox import SandboxError
        sb, tmp = _make_sandbox()
        assume(".." not in path)
        assume(not path.startswith(str(tmp / "allowed")))
        full = str(tmp / path)
        if os.path.lexists(full) and not os.path.isdir(full):
            assume(False)
        try:
            sb.check_write(full)
        except (PermissionError, FileNotFoundError, SandboxError):
            pass
        else:
            assert sb.is_dangerous(full)

    def test_invariant_no_escape_via_symlink(self):
        from core.sandbox import SandboxError
        sb, tmp = _make_sandbox()
        allowed = tmp / "allowed"
        outside = tmp / "outside"
        outside.mkdir()
        link = allowed / "link"
        try:
            link.symlink_to(outside)
            with pytest.raises((PermissionError, SandboxError)):
                sb.check_write(str(link / "secret.txt"))
        except (OSError, AttributeError):
            pytest.skip("symlinks not supported")
        finally:
            shutil.rmtree(str(tmp), ignore_errors=True)
