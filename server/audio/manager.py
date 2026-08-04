from __future__ import annotations

import os
import signal
import subprocess
import atexit
from typing import Final, Set

class AudioManager:
    """Centralized manager for audio playback processes."""

    def __init__(self) -> None:
        self._started_pids: Set[int] = set()
        self._processes: dict[int, subprocess.Popen] = {}
        atexit.register(self.stop_all)

    def register_process(self, pid: int, process: subprocess.Popen | None = None) -> None:
        """Registers a PID and optionally stores the process object."""
        self._started_pids.add(pid)
        if process is not None:
            self._processes[pid] = process

    def unregister_process(self, pid: int) -> None:
        """Unregisters a PID and removes its stored process object."""
        self._started_pids.discard(pid)
        self._processes.pop(pid, None)

    def is_ffplay_running(self) -> bool:
        """Returns True if any registered ffplay process is still alive."""
        alive: Set[int] = set()
        for pid in list(self._started_pids):
            process = self._processes.get(pid)
            if process is not None:
                if process.poll() is not None:
                    self.unregister_process(pid)
                    continue
            try:
                # Signal 0 only checks existence; raises OSError if the process is none.
                os.kill(pid, 0)
                alive.add(pid)
            except (ProcessLookupError, OSError):
                self.unregister_process(pid)
        return bool(alive)

    def start_process(self, command: list[str], env: dict[str, str] | None = None, stdin: subprocess.PIPE | None = None) -> int:
        """Starts a process and registers its PID along with the Popen object."""
        process = subprocess.Popen(
            command,
            stdin=stdin,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env=env,
        )
        if stdin is not None and process.stdin is not None:
            # We don't close stdin here, the caller is responsible for writing and closing
            pass
        self.register_process(process.pid, process)
        return process.pid

    def stop_all(self) -> list[str]:
        """Stops all registered audio processes and returns any errors."""
        errors: list[str] = []
        for pid in list(self._started_pids):
            process = self._processes.get(pid)
            try:
                if process is not None:
                    process.terminate()
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=3)
                else:
                    os.kill(pid, signal.SIGTERM)
            except (ProcessLookupError, OSError):
                pass
            except Exception as exc:
                errors.append(str(exc))
            finally:
                self.unregister_process(pid)
        
        return errors

# Global instance for easy access
audio_manager = AudioManager()
