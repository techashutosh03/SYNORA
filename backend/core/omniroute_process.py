"""
OmniRoute Process Manager
Automatically discovers, boots, and maintains the OmniRoute 376-provider AI Proxy Gateway
whenever SYNORA is started (via `./synora`, FastAPI backend, or Claw Code CLI).
"""

import os
import sys
import time
import socket
import shutil
import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger("synora.omniroute_manager")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OMNIROUTE_HOST = "127.0.0.1"
OMNIROUTE_PORT = 20128

class OmniRouteProcessManager:
    _instance: Optional["OmniRouteProcessManager"] = None
    _process: Optional[subprocess.Popen] = None

    @classmethod
    def get_instance(cls) -> "OmniRouteProcessManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def is_listening(self, host: str = OMNIROUTE_HOST, port: int = OMNIROUTE_PORT, timeout: float = 0.5) -> bool:
        """Checks if port 20128 is accepting TCP connections."""
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False

    def start_background(self, wait_seconds: float = 25.0) -> bool:
        """
        Spawns OmniRoute in the background if it is not already online.
        Waits up to wait_seconds for OmniRoute to start listening on port 20128.
        """
        if self.is_listening():
            logger.info("⚡ OmniRoute Gateway is already online on port %d", OMNIROUTE_PORT)
            return True

        npm_path = (
            shutil.which("npm") or 
            "/usr/local/bin/npm" or 
            "/opt/homebrew/bin/npm" or 
            "npm"
        )

        logs_dir = REPO_ROOT / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_file = logs_dir / "omniroute.log"

        print(f"\033[96m⚡ [SYNORA] OmniRoute Gateway is offline. Automatically booting OmniRoute on port {OMNIROUTE_PORT}...\033[0m")
        logger.info("Spawning OmniRoute ('npm run dev') from %s -> %s", REPO_ROOT, log_file)

        out_fd = open(log_file, "a", encoding="utf-8")
        try:
            self._process = subprocess.Popen(
                [npm_path, "run", "dev"],
                cwd=str(REPO_ROOT),
                stdout=out_fd,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                env={**os.environ, "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin")}
            )
        except Exception as exc:
            logger.error("Failed to spawn OmniRoute process: %s", exc)
            print(f"\033[91m⚠️ [SYNORA] Failed to automatically launch OmniRoute: {exc}\033[0m")
            return False

        # Poll until online or timeout
        start = time.time()
        while time.time() - start < wait_seconds:
            if self.is_listening():
                elapsed = round(time.time() - start, 1)
                print(f"\033[92m✅ [SYNORA] OmniRoute AI Gateway is now ONLINE on http://127.0.0.1:{OMNIROUTE_PORT}/v1 ({elapsed}s, PID: {self._process.pid})\033[0m")
                logger.info("OmniRoute became ready in %.1fs", elapsed)
                return True
            time.sleep(0.5)

        logger.warning("OmniRoute process spawned (PID: %s), still starting up in background...", self._process.pid if self._process else "unknown")
        return False

    async def ensure_online_async(self, wait_seconds: float = 25.0) -> bool:
        """Asynchronous wrapper for booting OmniRoute without blocking event loop."""
        if self.is_listening():
            return True
        return await asyncio.to_thread(self.start_background, wait_seconds)

    def stop_if_managed(self):
        """Terminates the OmniRoute process if it was spawned by this manager."""
        if self._process and self._process.poll() is None:
            logger.info("Terminating managed OmniRoute process (PID: %d)...", self._process.pid)
            try:
                self._process.terminate()
                self._process.wait(timeout=3.0)
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass
            self._process = None

omniroute_process_manager = OmniRouteProcessManager.get_instance()
