import unittest
from backend.core.routing_benchmark import (
    run_routing_benchmark,
    run_evaluation_suite,
    BENCHMARK_DATASET,
    UNSEEN_EVAL_DATASET
)

class TestRoutingBenchmark(unittest.TestCase):
    def test_tuning_benchmark_suite(self):
        """
        Executes the tuning benchmark suite (64 prompts) covering:
        - Pure Chat & Conceptual queries
        - Claw Code Read-Only inspections & git status/diff audits
        - Claw Code Mutating / Confirmations (compound tasks, fixes without run tests)
        - Ambiguous prompts fast-pathing to Clarification
        - Context-resolved follow-ups (disambiguated by prior error traces)
        - Multilingual prompts (Hindi, Hinglish, Spanish, French)
        Asserts >= 98% accuracy.
        """
        results = run_routing_benchmark(BENCHMARK_DATASET)
        total = results["total_cases"]
        passed = results["passed_cases"]
        accuracy = results["accuracy_pct"]

        self.assertGreaterEqual(total, 60, "Benchmark must have at least 60 diverse evaluation cases")
        self.assertGreaterEqual(accuracy, 98.0, f"Routing accuracy fell below 98%: {passed}/{total} ({accuracy}%)")
        self.assertEqual(len(results["misroutes"]), 0, f"Unexpected misroutes: {results['misroutes']}")

    def test_unseen_holdout_benchmark_suite(self):
        """
        Executes the unseen holdout evaluation suite (44 prompts) to guarantee
        out-of-sample generalization across languages and task modes.
        Asserts >= 95% accuracy and >= 0.90 clarification F1.
        """
        results = run_routing_benchmark(UNSEEN_EVAL_DATASET)
        total = results["total_cases"]
        passed = results["passed_cases"]
        accuracy = results["accuracy_pct"]

        self.assertGreaterEqual(total, 40, "Unseen holdout benchmark must have at least 40 cases")
        self.assertGreaterEqual(accuracy, 95.0, f"Unseen routing accuracy fell below 95%: {passed}/{total} ({accuracy}%)")
        self.assertEqual(len(results["misroutes"]), 0, f"Unexpected unseen misroutes: {results['misroutes']}")

        # Language breakdown assertions
        lang_stats = results["language_stats"]
        for lang in ("en", "hi_hinglish", "es", "fr"):
            self.assertIn(lang, lang_stats)
            self.assertGreater(lang_stats[lang]["total"], 0)
            self.assertGreaterEqual(lang_stats[lang]["accuracy_pct"], 90.0)

        # Clarification metrics assertions
        c_metrics = results["clarification_metrics"]
        self.assertGreaterEqual(c_metrics["precision"], 0.90)
        self.assertGreaterEqual(c_metrics["recall"], 0.90)
        self.assertGreaterEqual(c_metrics["f1_score"], 0.90)

    def test_full_evaluation_suite(self):
        suite = run_evaluation_suite()
        self.assertIn("benchmark_dataset", suite)
        self.assertIn("unseen_holdout_dataset", suite)
        self.assertIn("combined_summary", suite)
        combined = suite["combined_summary"]
        self.assertGreaterEqual(combined["total_cases"], 100)
        self.assertGreaterEqual(combined["overall_accuracy_pct"], 98.0)

if __name__ == "__main__":
    unittest.main()

