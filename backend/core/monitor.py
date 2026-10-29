import os
import re
import shutil
import time
import resource
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

class RequestMetrics(BaseModel):
    request_id: str
    session_id: str
    task_type: str
    complexity: str
    total_time_ms: float
    routing_time_ms: float
    memory_rss_mb: float
    models_used: List[str]
    stage_latencies: Dict[str, float] = Field(default_factory=dict)
    consistency_score: Optional[float] = None
    status: str = "success"
    timestamp: float = Field(default_factory=time.time)

class PerformanceMonitor:
    def __init__(self):
        self._history: List[RequestMetrics] = []
        self._model_stats: Dict[str, Dict[str, Any]] = {}
        self._total_requests: int = 0
        self._failed_requests: int = 0

    def get_current_memory_mb(self) -> float:
        """Returns peak RSS memory in MB for the current Python process on macOS."""
        # On macOS ru_maxrss is in bytes
        try:
            rusage = resource.getrusage(resource.RUSAGE_SELF)
            return round(rusage.ru_maxrss / (1024 * 1024), 2)
        except Exception:
            return 0.0

    def get_storage_status(self) -> Dict[str, Any]:
        """Returns disk space metrics to ensure storage safety on M2."""
        try:
            total, used, free = shutil.disk_usage("/")
            return {
                "total_gb": round(total / (1024**3), 2),
                "used_gb": round(used / (1024**3), 2),
                "free_gb": round(free / (1024**3), 2)
            }
        except Exception:
            return {"free_gb": 0.0}

    def get_macos_system_memory(self) -> Dict[str, Any]:
        """Inspects macOS swapusage and system memory statistics."""
        import subprocess
        swap_info = {"swap_used_mb": 0.0, "swap_total_mb": 0.0}
        memory_free_pct = 70.0
        try:
            # sysctl vm.swapusage
            res = subprocess.run(["sysctl", "vm.swapusage"], capture_output=True, text=True, timeout=2)
            if res.returncode == 0:
                # e.g. total = 0.00M  used = 0.00M  free = 0.00M
                used_match = re.search(r"used\s*=\s*([0-9\.]+)M", res.stdout)
                total_match = re.search(r"total\s*=\s*([0-9\.]+)M", res.stdout)
                if used_match:
                    swap_info["swap_used_mb"] = float(used_match.group(1))
                if total_match:
                    swap_info["swap_total_mb"] = float(total_match.group(1))
        except Exception:
            pass

        try:
            # memory_pressure
            res = subprocess.run(["memory_pressure"], capture_output=True, text=True, timeout=2)
            if res.returncode == 0:
                pct_match = re.search(r"System-wide memory free percentage:\s*(\d+)%", res.stdout)
                if pct_match:
                    memory_free_pct = float(pct_match.group(1))
        except Exception:
            pass

        return {
            "swap": swap_info,
            "system_memory_free_pct": memory_free_pct
        }

    def record_request(
        self,
        request_id: str,
        session_id: str,
        task_type: str,
        complexity: str,
        total_time_ms: float,
        routing_time_ms: float,
        models_used: List[str],
        stage_results: List[Any],
        consistency_score: Optional[float] = None,
        status: str = "success"
    ) -> RequestMetrics:
        """Records metrics for an executed request and updates rolling statistics."""
        memory_mb = self.get_current_memory_mb()
        stage_latencies = {}

        for stage in stage_results:
            mid = getattr(stage, "model_id", "unknown")
            ms = getattr(stage, "execution_time_ms", 0.0)
            stage_name = getattr(stage, "stage_name", "unknown")
            stage_latencies[f"{stage_name} ({mid})"] = ms

            # Update model stats
            if mid not in self._model_stats:
                self._model_stats[mid] = {
                    "invocations": 0,
                    "total_ms": 0.0,
                    "avg_ms": 0.0,
                    "errors": 0
                }
            self._model_stats[mid]["invocations"] += 1
            self._model_stats[mid]["total_ms"] += ms
            self._model_stats[mid]["avg_ms"] = round(
                self._model_stats[mid]["total_ms"] / self._model_stats[mid]["invocations"], 2
            )
            if getattr(stage, "status", "success") != "success":
                self._model_stats[mid]["errors"] += 1

        metrics = RequestMetrics(
            request_id=request_id,
            session_id=session_id,
            task_type=task_type,
            complexity=complexity,
            total_time_ms=total_time_ms,
            routing_time_ms=routing_time_ms,
            memory_rss_mb=memory_mb,
            models_used=models_used,
            stage_latencies=stage_latencies,
            consistency_score=consistency_score,
            status=status
        )

        self._history.append(metrics)
        self._total_requests += 1
        if status != "success":
            self._failed_requests += 1

        # Keep rolling window of last 200 requests
        if len(self._history) > 200:
            self._history.pop(0)

        return metrics

    def get_system_summary(self) -> Dict[str, Any]:
        """Provides aggregate telemetry and resource health."""
        avg_total_ms = (
            round(sum(m.total_time_ms for m in self._history) / len(self._history), 2)
            if self._history else 0.0
        )

        return {
            "telemetry": {
                "total_requests": self._total_requests,
                "successful_requests": self._total_requests - self._failed_requests,
                "failed_requests": self._failed_requests,
                "average_total_latency_ms": avg_total_ms
            },
            "per_model_metrics": self._model_stats,
            "latest_rss_mb": self.get_current_memory_mb(),
            "system_resources": {
                "process_memory_rss_mb": self.get_current_memory_mb(),
                "storage": self.get_storage_status(),
                "macos_memory": self.get_macos_system_memory()
            }
        }

monitor = PerformanceMonitor()
