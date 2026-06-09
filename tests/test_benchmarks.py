import os
import sys
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.async_engine import AsyncCommandQueue, Command
from core.command import CommandDef, CommandRegistry, parse_args
from core.diagnostics import ThreadDiagnostics
from core.model_cache import ModelCache


class TestBenchmarks(unittest.TestCase):
    def test_command_registry_1000_register_and_parse(self):
        reg = CommandRegistry()

        def handler(args: str) -> str:
            return "ok"

        start = time.perf_counter()
        for i in range(1000):
            reg.register(
                CommandDef(
                    f"cmd_{i}",
                    handler,
                    "bench",
                    description=f"benchmark command {i}",
                )
            )
        for i in range(1000):
            reg.parse_structured(f"/cmd_{i}")
        elapsed = time.perf_counter() - start
        self.assertLess(elapsed, 0.5)

    def test_async_queue_100_commands(self):
        q = AsyncCommandQueue()
        results = []
        lock = threading.Lock()
        all_done = threading.Event()

        def processor(text: str) -> str:
            return text

        q.start(processor)

        def cb(result: str) -> None:
            with lock:
                results.append(result)
                if len(results) >= 100:
                    all_done.set()

        start = time.perf_counter()
        for i in range(100):
            q.post(Command(text=f"bench_{i}", callback=cb))
        ok = all_done.wait(timeout=5.0)
        elapsed = time.perf_counter() - start
        q.stop()

        self.assertTrue(ok, "Not all 100 commands processed within timeout")
        self.assertLess(elapsed, 2.0)
        self.assertEqual(len(results), 100)

    def test_model_cache_1000_acquire_release(self):
        cache = ModelCache(max_loaded=1000, ttl=3600)

        start = time.perf_counter()
        for i in range(1000):
            cache.acquire(f"bench_model_{i}")
        for i in range(1000):
            cache.release(f"bench_model_{i}")
        elapsed = time.perf_counter() - start
        self.assertLess(elapsed, 0.5)
        self.assertEqual(cache.loaded_count(), 0)

    def test_thread_diagnostics_100_snapshots(self):
        diag = ThreadDiagnostics()

        start = time.perf_counter()
        for _ in range(100):
            diag.snapshot()
        elapsed = time.perf_counter() - start
        self.assertLess(elapsed, 0.5)

    def test_parse_args_1000_parses(self):
        start = time.perf_counter()
        for _ in range(1000):
            parse_args("--model qwen --verbose --temp=0.7 positional1 positional2")
        elapsed = time.perf_counter() - start
        self.assertLess(elapsed, 0.2)


if __name__ == "__main__":
    unittest.main()
