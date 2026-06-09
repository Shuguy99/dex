import os
import queue
import sys
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.async_engine import AsyncCommandQueue, Command, TimeoutWrapper


class TestAsyncCommandQueueStress(unittest.TestCase):
    def setUp(self):
        self.results: list[str] = []
        self.errors: list[str] = []
        self._lock = threading.Lock()

    def _callback(self, result: str) -> None:
        with self._lock:
            self.results.append(result)

    def _error_callback(self, err: str) -> None:
        with self._lock:
            self.errors.append(err)

    def test_1000_commands(self):
        acq = AsyncCommandQueue()

        def processor(text: str) -> str:
            return text.upper()

        acq.start(processor)
        for i in range(1000):
            acq.post(Command(
                text=str(i),
                callback=self._callback,
                error_callback=self._error_callback,
            ))
        acq._queue.join()
        acq.stop()

        self.assertEqual(len(self.results), 1000)
        self.assertEqual(len(self.errors), 0)
        for i in range(1000):
            self.assertIn(str(i).upper(), self.results)

    def test_cancellation(self):
        started = threading.Event()
        can_finish = threading.Event()

        def processor(text: str) -> str:
            started.set()
            can_finish.wait(timeout=5)
            return text.upper()

        acq = AsyncCommandQueue()
        acq.start(processor)
        acq.post(Command(text="test", callback=self._callback))
        started.wait(timeout=5)
        acq.cancel_current()
        can_finish.set()
        time.sleep(0.2)
        acq.stop()

        self.assertEqual(len(self.results), 0)

    def test_error_handling(self):
        def processor(text: str) -> str:
            raise ValueError(f"error:{text}")

        acq = AsyncCommandQueue()
        acq.start(processor)
        for i in range(10):
            acq.post(Command(
                text=str(i),
                callback=self._callback,
                error_callback=self._error_callback,
            ))
        acq._queue.join()
        acq.stop()

        self.assertEqual(len(self.results), 0)
        self.assertEqual(len(self.errors), 10)
        for err in self.errors:
            self.assertIn("error:", err)

    def test_fifo_order(self):
        order: list[int] = []
        lock = threading.Lock()

        def processor(text: str) -> str:
            return text

        def cb(result: str) -> None:
            with lock:
                order.append(int(result))

        acq = AsyncCommandQueue()
        acq.start(processor)
        for i in range(100):
            acq.post(Command(text=str(i), callback=cb))
        acq._queue.join()
        acq.stop()

        self.assertEqual(order, list(range(100)))

    def test_max_queue_size(self):
        q: queue.Queue[int] = queue.Queue(maxsize=5)
        for i in range(5):
            q.put_nowait(i)
        with self.assertRaises(queue.Full):
            q.put_nowait(5)
        self.assertEqual(q.qsize(), 5)

    def test_queue_empty_after_drain(self):
        acq = AsyncCommandQueue()

        def processor(text: str) -> str:
            return text

        acq.start(processor)
        for i in range(100):
            acq.post(Command(text=str(i)))
        acq._queue.join()
        acq.stop()

        self.assertEqual(acq.pending_count(), 0)


class TestTimeoutWrapper(unittest.TestCase):
    def test_timeout_raises(self):
        wrapper = TimeoutWrapper(default_timeout=1.0)

        def slow() -> None:
            time.sleep(10)

        start = time.time()
        with self.assertRaises(TimeoutError):
            wrapper.call(slow, timeout=0.05)
        elapsed = time.time() - start
        self.assertLess(elapsed, 2)

    def test_successful_call(self):
        wrapper = TimeoutWrapper(default_timeout=5.0)

        def fast() -> str:
            return "hello world"

        result = wrapper.call(fast)
        self.assertEqual(result, "hello world")

    def test_error_propagation(self):
        wrapper = TimeoutWrapper(default_timeout=5.0)

        def failing() -> None:
            raise ValueError("custom error")

        with self.assertRaises(ValueError):
            wrapper.call(failing)

    def test_default_timeout_used(self):
        wrapper = TimeoutWrapper(default_timeout=0.05)

        def slow() -> None:
            time.sleep(10)

        with self.assertRaises(TimeoutError):
            wrapper.call(slow)


if __name__ == "__main__":
    unittest.main()
