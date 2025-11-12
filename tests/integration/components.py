"""Component orchestration for integration tests."""

import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Set


class ComponentManager:
    """Manages lifecycle of Amor components from Procfile.test.

    Starts, stops, and monitors components defined in Procfile.test for
    integration testing. Provides programmatic control over the test environment.

    Example:
        manager = ComponentManager()
        manager.start(['ppg0', 'processor', 'audio'])
        time.sleep(5)  # Let components initialize
        # ... run tests ...
        manager.stop_all()
    """

    def __init__(self, procfile_path: Optional[str] = None, log_dir: Optional[str] = None):
        """Initialize component manager.

        Args:
            procfile_path: Path to Procfile.test (default: finds in repo root)
            log_dir: Directory for component logs (default: tests/integration/logs)
        """
        if procfile_path is None:
            # Find Procfile.test in repo root
            repo_root = Path(__file__).parent.parent.parent
            procfile_path = str(repo_root / "Procfile.test")

        self.procfile_path = procfile_path
        self.processes: Dict[str, subprocess.Popen] = {}
        self.log_handles: Dict[str, any] = {}
        self.log_dir = log_dir or str(Path(__file__).parent / "logs")
        os.makedirs(self.log_dir, exist_ok=True)

        # Parse Procfile.test
        self.commands = self._parse_procfile()

    def _parse_procfile(self) -> Dict[str, str]:
        """Parse Procfile.test and extract component commands.

        Returns:
            Dictionary mapping component names to shell commands

        Raises:
            FileNotFoundError: If Procfile.test not found
            ValueError: If Procfile format is invalid
        """
        if not os.path.exists(self.procfile_path):
            raise FileNotFoundError(f"Procfile not found: {self.procfile_path}")

        commands = {}
        with open(self.procfile_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue

                # Parse "name: command" format
                if ':' not in line:
                    raise ValueError(
                        f"Invalid Procfile format at line {line_num}: missing ':' separator"
                    )

                name, command = line.split(':', 1)
                name = name.strip()
                command = command.strip()

                if not name:
                    raise ValueError(f"Empty component name at line {line_num}")
                if not command:
                    raise ValueError(f"Empty command for component '{name}' at line {line_num}")

                if name in commands:
                    raise ValueError(f"Duplicate component name '{name}' at line {line_num}")

                commands[name] = command

        return commands

    def start(self, components: Optional[List[str]] = None, wait: float = 2.0):
        """Start specified components or all components if None.

        Args:
            components: List of component names to start, or None for all
            wait: Seconds to wait after starting for initialization

        Raises:
            ValueError: If component name not found in Procfile
            RuntimeError: If component is already running
        """
        if components is None:
            components = list(self.commands.keys())

        for component in components:
            if component not in self.commands:
                raise ValueError(
                    f"Component '{component}' not found in {self.procfile_path}. "
                    f"Available: {list(self.commands.keys())}"
                )

            if component in self.processes:
                if self.is_running(component):
                    raise RuntimeError(f"Component '{component}' is already running")
                else:
                    # Clean up dead process
                    if component in self.log_handles:
                        self.log_handles[component].close()
                        del self.log_handles[component]
                    del self.processes[component]

            # Setup log files
            log_file = os.path.join(self.log_dir, f"{component}.log")
            log_handle = open(log_file, 'w')
            self.log_handles[component] = log_handle

            # Start process
            command = self.commands[component]
            proc = subprocess.Popen(
                command,
                shell=True,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid  # Create new process group for clean shutdown
            )
            self.processes[component] = proc

            print(f"Started {component} (PID {proc.pid}): {command}")

        if wait > 0:
            time.sleep(wait)

    def stop(self, component: str, timeout: float = 5.0):
        """Stop a specific component.

        Args:
            component: Component name to stop
            timeout: Seconds to wait for graceful shutdown before SIGKILL

        Raises:
            ValueError: If component not running
        """
        if component not in self.processes:
            raise ValueError(f"Component '{component}' is not running")

        proc = self.processes[component]
        if not self.is_running(component):
            if component in self.log_handles:
                self.log_handles[component].close()
                del self.log_handles[component]
            del self.processes[component]
            return

        # Send SIGTERM to process group
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except ProcessLookupError:
            # Already dead
            if component in self.log_handles:
                self.log_handles[component].close()
                del self.log_handles[component]
            del self.processes[component]
            return

        # Wait for graceful shutdown
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            # Force kill if still running
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                proc.wait(timeout=1.0)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                pass

        # Close log handle
        if component in self.log_handles:
            self.log_handles[component].close()
            del self.log_handles[component]

        del self.processes[component]
        print(f"Stopped {component}")

    def stop_all(self, timeout: float = 5.0):
        """Stop all running components.

        Args:
            timeout: Seconds to wait per component for graceful shutdown
        """
        components = list(self.processes.keys())
        for component in components:
            try:
                self.stop(component, timeout=timeout)
            except Exception as e:
                print(f"Error stopping {component}: {e}")

        # Ensure all log handles are closed
        for component in list(self.log_handles.keys()):
            try:
                self.log_handles[component].close()
            except Exception:
                pass
            del self.log_handles[component]

    def is_running(self, component: str) -> bool:
        """Check if a component is currently running.

        Args:
            component: Component name to check

        Returns:
            True if running, False otherwise
        """
        if component not in self.processes:
            return False

        proc = self.processes[component]
        return proc.poll() is None

    def get_running_components(self) -> Set[str]:
        """Get set of currently running component names.

        Returns:
            Set of component names that are running
        """
        return {name for name in self.processes if self.is_running(name)}

    def restart(self, component: str, wait: float = 2.0):
        """Restart a component.

        Args:
            component: Component name to restart
            wait: Seconds to wait after restart for initialization
        """
        if self.is_running(component):
            self.stop(component)
        self.start([component], wait=wait)

    def get_log_path(self, component: str) -> str:
        """Get path to component's log file.

        Args:
            component: Component name

        Returns:
            Path to log file
        """
        return os.path.join(self.log_dir, f"{component}.log")

    def read_log(self, component: str, lines: Optional[int] = None) -> str:
        """Read log output from a component.

        Args:
            component: Component name
            lines: Number of lines to read from end (None for all)

        Returns:
            Log content as string

        Raises:
            FileNotFoundError: If log file doesn't exist
        """
        log_path = self.get_log_path(component)
        if not os.path.exists(log_path):
            raise FileNotFoundError(f"Log file not found: {log_path}")

        with open(log_path, 'r') as f:
            if lines is None:
                return f.read()
            else:
                all_lines = f.readlines()
                return ''.join(all_lines[-lines:])

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup all components."""
        self.stop_all()
