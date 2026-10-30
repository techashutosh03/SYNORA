import unittest
from backend.core.conversational_engine import (
    detect_intent, 
    answer_general_query, 
    is_reality_check_query, 
    generate_reality_check,
    handle_attachments_analysis
)

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

    def test_reality_check_detection(self):
        self.assertTrue(is_reality_check_query("give me the reality check on tech jobs"))
        self.assertTrue(is_reality_check_query("give me the reality cheak"))
        self.assertTrue(is_reality_check_query("tell me the brutal truth about AI startups"))

    def test_reality_check_generation(self):
        resp = generate_reality_check("give me the reality check on building an AI startup")
        self.assertIn("REALITY CHECK", resp)
        self.assertIn("Raw Truth", resp)
        self.assertIn("Playbook", resp)

    def test_reality_check_routing(self):
        import asyncio
        from backend.core.router import router
        decision = asyncio.run(router.route("give me the reality check on tech careers", simulate=True))
        self.assertEqual(decision.task_type, "reality_check")
        self.assertTrue(decision.confidence > 0.9)

    def test_attachment_analysis_markdown(self):
        att = [{
            "name": "README.md",
            "category": "markdown",
            "size": 1024,
            "text_content": "# Architecture Guide\n\n## Overview\nSystem docs."
        }]
        resp = handle_attachments_analysis("Analyze this file", att)
        self.assertIn("README.md", resp)
        self.assertIn("Architecture Guide", resp)

    def test_attachment_analysis_video(self):
        att = [{
            "name": "screen_recording.mov",
            "category": "video",
            "type": "video/quicktime",
            "size": 5242880
        }]
        resp = handle_attachments_analysis("Analyze this video", att)
        self.assertIn("screen_recording.mov", resp)
        self.assertIn("Video", resp)

if __name__ == "__main__":
    unittest.main()
