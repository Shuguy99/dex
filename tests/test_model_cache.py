import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.model_cache import ModelCache


class TestModelCache(unittest.TestCase):
    def setUp(self):
        self.cache = ModelCache(max_loaded=2, ttl=300)

    def test_init(self):
        self.assertEqual(self.cache._max_loaded, 2)
        self.assertEqual(self.cache._ttl, 300)
        self.assertEqual(self.cache.loaded_count(), 0)
        self.assertEqual(self.cache.loaded_models(), [])

    def test_acquire_new_model(self):
        result = self.cache.acquire("model_a")
        self.assertFalse(result)
        self.assertEqual(self.cache.loaded_count(), 1)

    def test_acquire_existing_model(self):
        self.cache.acquire("model_a")
        self.cache.mark_loaded("model_a", "handle_a")
        result = self.cache.acquire("model_a")
        self.assertTrue(result)
        self.assertEqual(self.cache.loaded_count(), 1)

    def test_acquire_eviction(self):
        self.cache.acquire("model_a")
        self.cache.acquire("model_b")
        self.cache.mark_loaded("model_a", "handle_a")
        self.cache.mark_loaded("model_b", "handle_b")
        # acquire model_c should evict one
        self.cache.acquire("model_c")
        self.assertEqual(self.cache.loaded_count(), 2)
        # model_c should be present
        self.assertIn("model_c", self.cache.loaded_models())

    def test_release(self):
        self.cache.acquire("model_a")
        self.cache.release("model_a")
        self.assertEqual(self.cache.loaded_count(), 0)
        self.assertNotIn("model_a", self.cache.loaded_models())

    def test_release_nonexistent(self):
        self.cache.release("nonexistent")
        self.assertEqual(self.cache.loaded_count(), 0)

    def test_mark_loaded(self):
        self.cache.acquire("model_a")
        self.cache.mark_loaded("model_a", "my_handle")
        self.assertIs(self.cache.get_handle("model_a"), "my_handle")

    def test_get_handle_nonexistent(self):
        handle = self.cache.get_handle("nonexistent")
        self.assertIsNone(handle)

    def test_get_handle_updates_last_use(self):
        self.cache.acquire("model_a")
        self.cache.mark_loaded("model_a", "handle")
        old_time = self.cache._last_use["model_a"]
        time.sleep(0.001)
        self.cache.get_handle("model_a")
        self.assertGreater(self.cache._last_use["model_a"], old_time)

    def test_evict_one_ttl_expired(self):
        cache = ModelCache(max_loaded=2, ttl=0)
        cache.acquire("model_a")
        cache.acquire("model_b")
        time.sleep(0.01)
        cache._evict_one()
        self.assertEqual(cache.loaded_count(), 1)

    def test_evict_one_oldest_when_no_expired(self):
        self.cache.acquire("model_a")
        self.cache.mark_loaded("model_a", "a")
        time.sleep(0.01)
        self.cache.acquire("model_b")
        self.cache.mark_loaded("model_b", "b")
        self.cache._evict_one()
        self.assertNotIn("model_a", self.cache.loaded_models())
        self.assertIn("model_b", self.cache.loaded_models())

    def test_unload_all(self):
        self.cache.acquire("model_a")
        self.cache.acquire("model_b")
        self.cache.unload_all()
        self.assertEqual(self.cache.loaded_count(), 0)
        self.assertEqual(self.cache.loaded_models(), [])

    def test_status(self):
        self.cache.acquire("model_a")
        with patch("core.model_cache.time.time", return_value=1000):
            status = self.cache.status()
        self.assertEqual(status["loaded"], ["model_a"])
        self.assertEqual(status["count"], 1)
        self.assertEqual(status["max"], 2)
        self.assertEqual(status["ttl"], 300)

    def test_concurrent_access(self):
        errors = []

        def worker(name):
            try:
                self.cache.acquire(name)
                self.cache.mark_loaded(name, f"handle_{name}")
                h = self.cache.get_handle(name)
                assert h == f"handle_{name}", f"Wrong handle for {name}"
                self.cache.release(name)
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=worker, args=(f"model_{i}",)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
