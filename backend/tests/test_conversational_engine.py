import unittest
from backend.core.conversational_engine import detect_intent, answer_general_query

class TestConversationalEngine(unittest.TestCase):
    def test_greeting_intent(self):
        intent = detect_intent("hello there")
        self.assertEqual(intent, "greeting")
        resp = answer_general_query("hello there")
        self.assertIn("Hello", resp)

    def test_identity_intent(self):
        intent = detect_intent("who are you?")
        self.assertEqual(intent, "identity")
        resp = answer_general_query("who are you?")
        self.assertIn("SYNORA", resp)

    def test_science_explanation(self):
        resp = answer_general_query("Why is the sky blue?")
        self.assertIn("Rayleigh", resp)

    def test_creative_writing(self):
        intent = detect_intent("write a poem about the ocean")
        self.assertEqual(intent, "creative")
        resp = answer_general_query("write a poem about the ocean")
        self.assertTrue(len(resp) > 50)

    def test_comparative_question(self):
        resp = answer_general_query("Compare Python and Rust")
        self.assertIn("Python", resp)
        self.assertIn("Rust", resp)

if __name__ == "__main__":
    unittest.main()
