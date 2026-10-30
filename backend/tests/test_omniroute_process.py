import unittest
from backend.core.omniroute_process import OmniRouteProcessManager, omniroute_process_manager

class TestOmniRouteProcessManager(unittest.TestCase):
    def test_singleton_instance(self):
        m1 = OmniRouteProcessManager.get_instance()
        m2 = OmniRouteProcessManager.get_instance()
        self.assertIs(m1, m2)

    def test_listening_check(self):
        # Port 20128 is running in our test environment
        is_up = omniroute_process_manager.is_listening(timeout=1.0)
        self.assertIsInstance(is_up, bool)

    def test_start_background_when_already_listening(self):
        if omniroute_process_manager.is_listening():
            # If already listening, it should return True immediately without spawning
            started = omniroute_process_manager.start_background(wait_seconds=1.0)
            self.assertTrue(started)

if __name__ == "__main__":
    unittest.main()
