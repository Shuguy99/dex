import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.personality import MODES, PersonalityEngine


class TestPersonalityEngine(unittest.TestCase):
    def setUp(self):
        self.engine = PersonalityEngine(default_mode="джарвис")

    def test_init_default(self):
        self.assertEqual(self.engine.current_mode, "джарвис")
        self.assertEqual(self.engine._history, [])
        self.assertEqual(self.engine._user_tone_history, [])
        self.assertEqual(self.engine._custom_instructions, [])
        self.assertFalse(self.engine._greeted)

    def test_init_custom_mode(self):
        engine = PersonalityEngine(default_mode="рабочий")
        self.assertEqual(engine.current_mode, "рабочий")

    def test_init_invalid_mode(self):
        engine = PersonalityEngine(default_mode="nonexistent")
        self.assertEqual(engine.current_mode, "nonexistent")
        self.assertEqual(engine._mode["name"], "jarvis")

    def test_system_prompt(self):
        prompt = self.engine.system_prompt
        self.assertIn("Dex", prompt)
        self.assertIn("style:", prompt)

    def test_system_prompt_with_custom_instructions(self):
        self.engine.add_instruction("Be more formal")
        self.engine.add_instruction("Use emojis")
        prompt = self.engine.system_prompt
        self.assertIn("Be more formal", prompt)
        self.assertIn("Use emojis", prompt)

    def test_set_mode_valid(self):
        result = self.engine.set_mode("рабочий")
        self.assertTrue(result)
        self.assertEqual(self.engine.current_mode, "рабочий")

    def test_set_mode_invalid(self):
        result = self.engine.set_mode("nonexistent")
        self.assertFalse(result)
        self.assertEqual(self.engine.current_mode, "джарвис")

    def test_analyze_tone_positive(self):
        result = self.engine.analyze_tone("отлично спасибо класс")
        self.assertEqual(result["tone"], "positive")
        self.assertGreater(result["positive_score"], 0)

    def test_analyze_tone_negative(self):
        result = self.engine.analyze_tone("плохо ужасно медленно")
        self.assertEqual(result["tone"], "negative")
        self.assertGreater(result["negative_score"], 0)

    def test_analyze_tone_question(self):
        result = self.engine.analyze_tone("как дела?")
        self.assertEqual(result["tone"], "questioning")

    def test_analyze_tone_urgency_high(self):
        result = self.engine.analyze_tone("Стоп!")
        self.assertEqual(result["urgency"], "high")

    def test_analyze_tone_urgency_medium(self):
        result = self.engine.analyze_tone("Это длинное предложение с восклицанием!")
        self.assertEqual(result["urgency"], "medium")

    def test_analyze_tone_urgency_low(self):
        result = self.engine.analyze_tone("спокойный вопрос без восклицаний")
        self.assertEqual(result["urgency"], "low")

    def test_analyze_tone_updates_history(self):
        self.engine.analyze_tone("отлично")
        self.engine.analyze_tone("плохо")
        self.assertEqual(len(self.engine._user_tone_history), 2)
        self.assertEqual(self.engine._user_tone_history, ["positive", "negative"])

    def test_adapt_response_high_urgency(self):
        adapted = self.engine.adapt_response("Стоп!", "Выполняю остановку")
        self.assertTrue(adapted.startswith("Сэр!"))

    def test_adapt_response_high_urgency_already_sir(self):
        adapted = self.engine.adapt_response("Стоп!", "Сэр, выполняю остановку")
        self.assertEqual(adapted, "Сэр, выполняю остановку")

    def test_adapt_response_negative_low_formality(self):
        engine = PersonalityEngine(default_mode="расслабленный")
        adapted = engine.adapt_response("плохо", "Понял")
        self.assertIn("кофе", adapted)

    def test_adapt_response_positive(self):
        adapted = self.engine.adapt_response("отлично спасибо", "Рад помочь")
        self.assertIn("Рад стараться", adapted)

    def test_get_greeting_first_time(self):
        greeting = self.engine.get_greeting()
        self.assertEqual(greeting, MODES["джарвис"]["greeting"])

    def test_get_greeting_already_greeted(self):
        self.engine.get_greeting()
        greeting = self.engine.get_greeting()
        self.assertEqual(greeting, "")

    def test_add_instruction(self):
        self.engine.add_instruction("Test instruction")
        self.assertIn("Test instruction", self.engine._custom_instructions)

    def test_record_interaction(self):
        self.engine.record_interaction("привет", "здравствуйте")
        self.assertEqual(len(self.engine._history), 1)
        self.assertEqual(self.engine._history[0]["user"], "привет")
        self.assertEqual(self.engine._history[0]["dex"], "здравствуйте")
        self.assertIn("tone", self.engine._history[0])
        self.assertIn("timestamp", self.engine._history[0])

    def test_get_mode_list(self):
        modes = self.engine.get_mode_list()
        self.assertIn("джарвис", modes)
        self.assertIn("рабочий", modes)
        self.assertIn("расслабленный", modes)
        self.assertIn("креативный", modes)

    def test_tts_rate(self):
        rate = self.engine.tts_rate()
        self.assertEqual(rate, MODES["джарвис"]["tts_rate"])
        self.engine.set_mode("рабочий")
        self.assertEqual(self.engine.tts_rate(), MODES["рабочий"]["tts_rate"])

    def test_system_prompt_property_formats_instructions(self):
        self.engine.add_instruction("Be concise")
        prompt = self.engine.system_prompt
        self.assertIn("- Be concise", prompt)


if __name__ == "__main__":
    unittest.main()
