import unittest
from backend.core.routing_benchmark import run_routing_benchmark

class TestRoutingBenchmark(unittest.TestCase):
    def test_routing_benchmark_suite(self):
        """
        Executes the 64-prompt routing accuracy benchmark covering:
        - Pure Chat & Conceptual queries
        - Claw Code Read-Only inspections & git status/diff audits
        - Claw Code Mutating / Confirmations (compound tasks, fixes without run tests)
        - Ambiguous prompts fast-pathing to Clarification
        - Context-resolved follow-ups (disambiguated by prior error traces)
        - Multilingual prompts (Hindi, Hinglish, Spanish, French)
        Asserts >= 98% accuracy.
        """
        results = run_routing_benchmark()
        total = results["total_cases"]
        passed = results["passed_cases"]
        accuracy = results["accuracy_pct"]

        self.assertGreaterEqual(total, 60, "Benchmark must have at least 60 diverse evaluation cases")
        self.assertGreaterEqual(accuracy, 98.0, f"Routing accuracy fell below 98%: {passed}/{total} ({accuracy}%)")
        self.assertEqual(len(results["misroutes"]), 0, f"Unexpected misroutes: {results['misroutes']}")

if __name__ == "__main__":
    unittest.main()

