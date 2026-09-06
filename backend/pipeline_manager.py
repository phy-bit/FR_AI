import threading
import traceback


class PipelineManager:
    def __init__(self):
        self.thread = None
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.error = None

    def _worker(self):
        try:
            from ai_orchestrator import run_ai_loop

            run_ai_loop(self.stop_event)

        except Exception as exc:
            self.error = str(exc)
            print(f"[AI ORCHESTRATOR] Error: {exc}")
            traceback.print_exc()

        finally:
            with self.lock:
                self.thread = None

    def start(self):
        with self.lock:
            if self.thread is not None and self.thread.is_alive():
                return {
                    "success": False,
                    "status": "already_running"
                }

            self.error = None
            self.stop_event.clear()

            try:
                self.thread = threading.Thread(
                    target=self._worker,
                    name="FalconAIOrchestrator",
                    daemon=True
                )
                self.thread.start()

                return {
                    "success": True,
                    "status": "running"
                }

            except Exception as exc:
                self.thread = None
                self.error = str(exc)

                return {
                    "success": False,
                    "status": "start_failed",
                    "error": str(exc)
                }

    def stop(self):
        with self.lock:
            if self.thread is None or not self.thread.is_alive():
                self.thread = None
                return {
                    "success": False,
                    "status": "not_running"
                }

            self.stop_event.set()
            thread = self.thread

        thread.join(timeout=5)

        with self.lock:
            if thread.is_alive():
                return {
                    "success": False,
                    "status": "stop_timeout"
                }

            self.thread = None

        return {
            "success": True,
            "status": "stopped"
        }

    def status(self):
        with self.lock:
            running = (
                self.thread is not None
                and self.thread.is_alive()
            )

            result = {
                "running": running,
                "pid": None
            }

            if self.error:
                result["error"] = self.error

            return result


pipeline_manager = PipelineManager()