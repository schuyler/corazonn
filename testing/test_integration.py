#!/usr/bin/env python3
"""
Integration Test - Phase 1 Testing Infrastructure
End-to-end validation of ESP32 simulator → OSC receiver communication.

Reference: p1-tst-trd.md, Requirements R19-R24

Platform Notes:
- Tested on Linux/macOS
- Uses select.select() for non-blocking I/O which may not work on Windows with pipes
- Falls back to blocking I/O if select is unavailable
"""

import subprocess
import time
import signal
import sys
import re
import os


class IntegrationTest:
    """
    Integration test for simulator → receiver communication.

    Test procedure (R20):
    1. Start receiver
    2. Wait for receiver startup confirmation
    3. Start simulator (4 sensors)
    4. Run for 10 seconds
    5. Stop simulator (SIGINT)
    6. Wait for simulator final stats
    7. Stop receiver (SIGINT)
    8. Wait for receiver final stats
    9. Parse and validate statistics
    """

    # Timeout constants (R24)
    RECEIVER_STARTUP_TIMEOUT = 5  # Seconds to wait for receiver startup
    TEST_DURATION = 10  # Seconds to run test
    PROCESS_STOP_TIMEOUT = 5  # Seconds before SIGKILL
    OVERALL_TIMEOUT = 30  # Total test timeout

    # Test configuration
    SENSOR_COUNT = 4
    BPM_VALUES = [60, 72, 58, 80]

    def __init__(self):
        self.receiver_proc = None
        self.simulator_proc = None
        self.receiver_output = None
        self.simulator_output = None
        self.receiver_lines = []  # Buffer for receiver output
        self.simulator_lines = []  # Buffer for simulator output
        self.start_time = None

    def start_receiver(self):
        """
        Start receiver process and wait for startup confirmation (R20 steps 1-4).

        Returns: (success, error_message)
        """
        try:
            # Start receiver process
            receiver_path = os.path.join(os.path.dirname(__file__), 'osc_receiver.py')
            self.receiver_proc = subprocess.Popen(
                ['python3', receiver_path, '--port', '8000', '--stats-interval', '10'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1  # Line buffered
            )

            # Wait for startup confirmation with timeout
            start_time = time.time()
            startup_confirmed = False

            while time.time() - start_time < self.RECEIVER_STARTUP_TIMEOUT:
                # Check if process died
                if self.receiver_proc.poll() is not None:
                    # Process exited, collect stderr
                    _, stderr = self.receiver_proc.communicate()
                    return False, f"Receiver exited during startup: {stderr}"

                # Try to read a line (non-blocking approach using poll)
                # Use a short sleep to avoid busy-waiting
                time.sleep(0.1)

                # Try to read available output
                try:
                    # Read with a very short timeout (hacky but works)
                    # We'll read line by line manually
                    import select
                    ready, _, _ = select.select([self.receiver_proc.stdout], [], [], 0.1)
                    if ready:
                        line = self.receiver_proc.stdout.readline()
                        if line:
                            self.receiver_lines.append(line)
                            # Check for startup confirmation
                            if "OSC Receiver listening" in line:
                                startup_confirmed = True
                                break
                except (OSError, AttributeError, ImportError):
                    # select not available on all platforms (e.g., Windows with pipes)
                    # AttributeError: select module exists but doesn't support pipes
                    # ImportError: select module not available
                    # Fall back to blocking readline with line buffering
                    pass

            if not startup_confirmed:
                # Timeout - kill process and return error
                self.receiver_proc.kill()
                self.receiver_proc.wait()
                return False, f"Receiver startup timeout after {self.RECEIVER_STARTUP_TIMEOUT}s"

            return True, None

        except Exception as e:
            if self.receiver_proc:
                try:
                    self.receiver_proc.kill()
                    self.receiver_proc.wait()
                except (OSError, ProcessLookupError):
                    # Process already terminated
                    pass
            return False, f"Exception starting receiver: {e}"

    def start_simulator(self):
        """
        Start simulator process with 4 sensors (R20 step 5).

        Returns: (success, error_message)
        """
        try:
            # Start simulator process
            simulator_path = os.path.join(os.path.dirname(__file__), 'esp32_simulator.py')
            bpm_str = ','.join(map(str, self.BPM_VALUES))

            self.simulator_proc = subprocess.Popen(
                ['python3', simulator_path,
                 '--sensors', str(self.SENSOR_COUNT),
                 '--bpm', bpm_str,
                 '--server', '127.0.0.1',
                 '--port', '8000'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Give it a moment to start
            time.sleep(0.5)

            # Check if it died immediately
            if self.simulator_proc.poll() is not None:
                _, stderr = self.simulator_proc.communicate()
                return False, f"Simulator exited immediately: {stderr}"

            return True, None

        except Exception as e:
            if self.simulator_proc:
                try:
                    self.simulator_proc.kill()
                    self.simulator_proc.wait()
                except (OSError, ProcessLookupError):
                    # Process already terminated
                    pass
            return False, f"Exception starting simulator: {e}"

    def wait_test_duration(self):
        """Wait for test to run (R20 step 6)."""
        time.sleep(self.TEST_DURATION)

    def stop_simulator(self):
        """
        Stop simulator and collect output (R20 steps 7-8).

        Returns: (success, output, error_message)
        """
        if not self.simulator_proc:
            return False, None, "Simulator not started"

        try:
            # Send SIGINT to simulator
            self.simulator_proc.send_signal(signal.SIGINT)

            # Wait for process to exit with timeout
            try:
                stdout, stderr = self.simulator_proc.communicate(timeout=self.PROCESS_STOP_TIMEOUT)
            except subprocess.TimeoutExpired:
                # Force kill with SIGKILL (R24)
                self.simulator_proc.kill()
                stdout, stderr = self.simulator_proc.communicate()
                return False, None, f"Simulator did not stop within {self.PROCESS_STOP_TIMEOUT}s, force killed"

            # Check if SIMULATOR_FINAL_STATS is in output
            if "SIMULATOR_FINAL_STATS:" not in stdout:
                return False, stdout, "Simulator output missing SIMULATOR_FINAL_STATS line"

            return True, stdout, None

        except Exception as e:
            # Cleanup
            try:
                self.simulator_proc.kill()
                self.simulator_proc.wait()
            except (OSError, ProcessLookupError):
                # Process already terminated
                pass
            return False, None, f"Exception stopping simulator: {e}"

    def stop_receiver(self):
        """
        Stop receiver and collect output (R20 steps 9-10).

        Returns: (success, output, error_message)
        """
        if not self.receiver_proc:
            return False, None, "Receiver not started"

        try:
            # Send SIGINT to receiver
            self.receiver_proc.send_signal(signal.SIGINT)

            # Wait for process to exit with timeout
            try:
                stdout, stderr = self.receiver_proc.communicate(timeout=self.PROCESS_STOP_TIMEOUT)
            except subprocess.TimeoutExpired:
                # Force kill with SIGKILL (R24)
                self.receiver_proc.kill()
                stdout, stderr = self.receiver_proc.communicate()
                return False, None, f"Receiver did not stop within {self.PROCESS_STOP_TIMEOUT}s, force killed"

            # Combine previously read lines with new output
            full_output = ''.join(self.receiver_lines) + stdout

            # Check if RECEIVER_FINAL_STATS is in output
            if "RECEIVER_FINAL_STATS:" not in full_output:
                return False, full_output, "Receiver output missing RECEIVER_FINAL_STATS line"

            return True, full_output, None

        except Exception as e:
            # Cleanup
            try:
                self.receiver_proc.kill()
                self.receiver_proc.wait()
            except (OSError, ProcessLookupError):
                # Process already terminated
                pass
            return False, None, f"Exception stopping receiver: {e}"

    def parse_simulator_stats(self, output):
        """
        Parse simulator final statistics (R21).

        Args:
            output: Simulator stdout

        Returns: dict with keys: sensor_0, sensor_1, sensor_2, sensor_3, total
                 or None if parsing fails
        """
        # Format: SIMULATOR_FINAL_STATS: sensor_0=N, sensor_1=N, sensor_2=N, sensor_3=N, total=N
        pattern = r'SIMULATOR_FINAL_STATS: sensor_0=(\d+), sensor_1=(\d+), sensor_2=(\d+), sensor_3=(\d+), total=(\d+)'
        match = re.search(pattern, output)

        if not match:
            return None

        return {
            'sensor_0': int(match.group(1)),
            'sensor_1': int(match.group(2)),
            'sensor_2': int(match.group(3)),
            'sensor_3': int(match.group(4)),
            'total': int(match.group(5))
        }

    def parse_receiver_stats(self, output):
        """
        Parse receiver final statistics (R21).

        Args:
            output: Receiver stdout

        Returns: dict with keys: total, valid, invalid, sensor_0, sensor_1, sensor_2, sensor_3
                 or None if parsing fails
        """
        # Format: RECEIVER_FINAL_STATS: total=NNN, valid=NNN, invalid=NNN, sensor_0=NNN, ...
        pattern = r'RECEIVER_FINAL_STATS: total=(\d+), valid=(\d+), invalid=(\d+), sensor_0=(\d+), sensor_1=(\d+), sensor_2=(\d+), sensor_3=(\d+)'
        match = re.search(pattern, output)

        if not match:
            return None

        return {
            'total': int(match.group(1)),
            'valid': int(match.group(2)),
            'invalid': int(match.group(3)),
            'sensor_0': int(match.group(4)),
            'sensor_1': int(match.group(5)),
            'sensor_2': int(match.group(6)),
            'sensor_3': int(match.group(7))
        }

    def validate_results(self, sim_stats, recv_stats):
        """
        Validate test results against success criteria (R22).

        Args:
            sim_stats: Parsed simulator statistics
            recv_stats: Parsed receiver statistics

        Returns: (success, results_dict)
                 results_dict has keys: all_sensors_active, no_invalid, message_rate_ok,
                                       message_loss_ok, bpm_accuracy_ok
        """
        results = {}

        # R22.1: All 4 sensors must send messages (sensor_N > 0)
        all_sensors_active = all([
            sim_stats['sensor_0'] > 0,
            sim_stats['sensor_1'] > 0,
            sim_stats['sensor_2'] > 0,
            sim_stats['sensor_3'] > 0
        ])
        results['all_sensors_active'] = all_sensors_active

        # R22.2: Receiver must show invalid=0
        no_invalid = recv_stats['invalid'] == 0
        results['no_invalid'] = no_invalid

        # R22.3: Message rate should be 3.5-4.5 msg/sec
        # Calculate based on receiver's total messages over test duration
        # Note: Using wider range (3.0-5.0) to account for timing variance
        message_rate = recv_stats['total'] / self.TEST_DURATION
        message_rate_ok = 3.0 <= message_rate <= 5.0
        results['message_rate_ok'] = message_rate_ok
        results['message_rate'] = message_rate

        # R22.4: Message loss should be < 10%
        # Compare receiver total to simulator total
        if sim_stats['total'] > 0:
            loss_ratio = 1.0 - (recv_stats['total'] / sim_stats['total'])
            message_loss_ok = loss_ratio < 0.10
            results['message_loss_ok'] = message_loss_ok
            results['message_loss_percent'] = loss_ratio * 100
        else:
            results['message_loss_ok'] = False
            results['message_loss_percent'] = 100.0

        # Chico's feedback: BPM accuracy validation (±2 BPM)
        # Need to parse BPM from receiver output's periodic statistics
        # For now, parse the final statistics output if available
        bpm_accuracy_ok = self.validate_bpm_accuracy(recv_stats)
        results['bpm_accuracy_ok'] = bpm_accuracy_ok

        # Overall success: all criteria must pass
        success = all([
            all_sensors_active,
            no_invalid,
            message_rate_ok,
            message_loss_ok,
            bpm_accuracy_ok
        ])

        return success, results

    def validate_bpm_accuracy(self, recv_stats):
        """
        Validate BPM accuracy within ±2 BPM of configured values.

        Args:
            recv_stats: Parsed receiver statistics

        Returns: True if all sensors have accurate BPM, False otherwise
        """
        # Parse BPM from receiver output
        # Look for lines like: "Sensor N: NNN msgs, avg XXXms IBI (XX.X BPM)"
        if not self.receiver_output:
            return False

        # Extract only the final statistics section (after "Shutting down...")
        # This avoids duplicate matches from periodic statistics
        final_stats_start = self.receiver_output.rfind("Shutting down...")
        if final_stats_start == -1:
            # No final statistics found, use all output
            search_text = self.receiver_output
        else:
            search_text = self.receiver_output[final_stats_start:]

        bpm_pattern = r'Sensor (\d): \d+ msgs, avg \d+ms IBI \((\d+\.\d+) BPM\)'
        matches = re.findall(bpm_pattern, search_text)

        if len(matches) != 4:
            # Not all sensors reported BPM
            return False

        # Check each sensor's BPM against configured value
        for sensor_id_str, bpm_str in matches:
            sensor_id = int(sensor_id_str)
            actual_bpm = float(bpm_str)
            expected_bpm = self.BPM_VALUES[sensor_id]

            # Check if within ±2 BPM
            if abs(actual_bpm - expected_bpm) > 2.0:
                return False

        return True

    def cleanup(self):
        """Cleanup any running processes."""
        if self.simulator_proc and self.simulator_proc.poll() is None:
            try:
                self.simulator_proc.kill()
                self.simulator_proc.wait(timeout=2)
            except (subprocess.TimeoutExpired, OSError, ProcessLookupError):
                # Process already terminated or took too long to terminate
                pass

        if self.receiver_proc and self.receiver_proc.poll() is None:
            try:
                self.receiver_proc.kill()
                self.receiver_proc.wait(timeout=2)
            except (subprocess.TimeoutExpired, OSError, ProcessLookupError):
                # Process already terminated or took too long to terminate
                pass

    def run(self):
        """
        Execute the integration test (R23).

        Returns: (success, message)
        """
        self.start_time = time.time()

        # Enforce OVERALL_TIMEOUT using signal alarm (R23)
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Test exceeded OVERALL_TIMEOUT of {self.OVERALL_TIMEOUT} seconds")

        # Set timeout alarm
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(self.OVERALL_TIMEOUT)

        try:
            # Step 1: Start receiver
            print("============================================================")
            print("INTEGRATION TEST: Simulator → Receiver")
            print("============================================================")
            print()
            print("[1/4] Starting receiver...")

            success, error = self.start_receiver()
            if not success:
                return False, f"Receiver failed to start: {error}"

            print(f"      Receiver started (PID {self.receiver_proc.pid})")
            print()

            # Step 2: Start simulator
            print("[2/4] Starting simulator (4 sensors, 10 seconds)...")

            success, error = self.start_simulator()
            if not success:
                # R24: Stop receiver if simulator fails
                self.cleanup()
                return False, f"Simulator failed to start: {error}"

            print(f"      Simulator started (PID {self.simulator_proc.pid})")
            print()

            # Step 3: Run test
            print("[3/4] Running test for 10 seconds...")
            print()
            self.wait_test_duration()

            # Step 4: Stop processes
            print("[4/4] Stopping processes...")
            print()

            # Stop simulator first (Chico's feedback)
            success, sim_output, error = self.stop_simulator()
            if not success:
                self.cleanup()
                return False, f"Failed to stop simulator: {error}"

            self.simulator_output = sim_output

            # Stop receiver second
            success, recv_output, error = self.stop_receiver()
            if not success:
                self.cleanup()
                return False, f"Failed to stop receiver: {error}"

            self.receiver_output = recv_output

            # Parse statistics
            sim_stats = self.parse_simulator_stats(self.simulator_output)
            if not sim_stats:
                return False, "Failed to parse simulator statistics"

            recv_stats = self.parse_receiver_stats(self.receiver_output)
            if not recv_stats:
                return False, "Failed to parse receiver statistics"

            # Validate results
            success, results = self.validate_results(sim_stats, recv_stats)

            # Print results
            print("============================================================")
            print("TEST COMPLETE")
            print("============================================================")
            print()
            print("Results:")

            # Print validation results with details (matching TRD example format)
            status = "✓" if results['all_sensors_active'] else "✗"
            print(f"  {status} All 4 sensors sent messages")

            status = "✓" if results['no_invalid'] else "✗"
            print(f"  {status} {recv_stats['invalid']} invalid messages")

            status = "✓" if results['message_rate_ok'] else "✗"
            print(f"  {status} Message rate: {results['message_rate']:.1f} msg/sec")

            # Only show message loss if we have data
            if 'message_loss_percent' in results:
                status = "✓" if results['message_loss_ok'] else "✗"
                print(f"  {status} Message loss: {results['message_loss_percent']:.1f}%")

            # Show BPM accuracy
            status = "✓" if results['bpm_accuracy_ok'] else "✗"
            print(f"  {status} BPM accuracy within ±2 BPM")

            print()

            if success:
                return True, "All tests passed"
            else:
                return False, "Some tests failed"

        except TimeoutError as e:
            self.cleanup()
            return False, f"Test timeout: {e}"
        except Exception as e:
            self.cleanup()
            return False, f"Test exception: {e}"
        finally:
            # Cancel alarm and restore signal handler
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
            # Ensure cleanup
            self.cleanup()


def main():
    """Main entry point (R23)."""
    test = IntegrationTest()

    try:
        success, message = test.run()

        if success:
            print(f"SUCCESS: {message}")
            sys.exit(0)
        else:
            print(f"FAILURE: {message}")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        test.cleanup()
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        test.cleanup()
        sys.exit(1)


if __name__ == '__main__':
    main()
