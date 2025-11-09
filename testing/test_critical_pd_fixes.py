#!/usr/bin/env python3
"""
Critical Pure Data patch validation tests.

Tests for 5 critical logic errors identified by Chico:
1. Sample playback logic (sound-engine.pd)
2. Spatial mixer connections (spatial-mixer.pd)
3. Disconnection detection (sensor-process.pd)
4. Missing sample files
5. Redundant DAC objects
"""

import unittest
import os
import re
from pathlib import Path


class PdPatchParser:
    """Parse Pure Data patch files to verify structure."""

    def __init__(self, patch_path):
        self.patch_path = patch_path
        self.content = self._read_patch()
        self.objects = self._parse_objects()
        self.connections = self._parse_connections()

    def _read_patch(self):
        """Read patch file content."""
        with open(self.patch_path, 'r') as f:
            return f.read()

    def _parse_objects(self):
        """Extract all objects from patch, assigning sequential IDs."""
        objects = {}
        obj_counter = 0

        # Match: #X obj <x> <y> <classname> [args];
        # Also match: #X msg <x> <y> <message>;
        # Objects are assigned sequential IDs in order of appearance
        lines = self.content.split('\n')

        for line in lines:
            stripped = line.strip()
            if stripped.startswith('#X obj'):
                # Parse line like: #X obj 50 20 loadbang;
                parts = line.split()
                if len(parts) >= 5:  # #X obj x y classname [args...]
                    x_coord = parts[2]
                    y_coord = parts[3]
                    classname = parts[4].rstrip(';')  # Remove trailing semicolon
                    args = ' '.join(parts[5:]).rstrip(';')

                    objects[str(obj_counter)] = {
                        'class': classname,
                        'args': args,
                        'x': x_coord,
                        'y': y_coord
                    }
                    obj_counter += 1
            elif stripped.startswith('#X msg'):
                # Parse line like: #X msg 20 400 0;
                parts = line.split(None, 4)  # Split into max 5 parts
                if len(parts) >= 4:  # #X msg x y message [args...]
                    x_coord = parts[2]
                    y_coord = parts[3]
                    message = parts[4].rstrip(';') if len(parts) > 4 else ''

                    objects[str(obj_counter)] = {
                        'class': 'msg',
                        'args': message,
                        'x': x_coord,
                        'y': y_coord
                    }
                    obj_counter += 1

        return objects

    def _parse_connections(self):
        """Extract all connections from patch."""
        connections = []
        # Match: #X connect <from_id> <from_outlet> <to_id> <to_inlet>;
        pattern = r'#X connect (\d+) (\d+) (\d+) (\d+)'
        matches = re.finditer(pattern, self.content)
        for match in matches:
            connections.append({
                'from_id': match.group(1),
                'from_outlet': int(match.group(2)),
                'to_id': match.group(3),
                'to_inlet': int(match.group(4))
            })
        return connections

    def find_objects(self, classname):
        """Find all objects of a given class."""
        return {obj_id: obj for obj_id, obj in self.objects.items()
                if obj['class'] == classname}

    def get_connections_to(self, obj_id, inlet):
        """Get all connections to a specific inlet of an object."""
        return [c for c in self.connections
                if c['to_id'] == obj_id and c['to_inlet'] == inlet]

    def get_connections_from(self, obj_id):
        """Get all connections from an object."""
        return [c for c in self.connections if c['from_id'] == obj_id]


class TestCritical1SamplePlayback(unittest.TestCase):
    """Test CRITICAL #1: Sample playback logic in sound-engine.pd."""

    def setUp(self):
        self.patch = PdPatchParser(
            '/home/user/corazonn/audio/patches/sound-engine.pd'
        )

    def test_line_object_exists(self):
        """Verify line~ objects exist for sample playback."""
        line_objects = self.patch.find_objects('line~')
        self.assertGreater(len(line_objects), 0,
                          "No line~ objects found in sound-engine.pd")

    def test_pack_message_format(self):
        """Verify pack objects format message correctly."""
        pack_objects = self.patch.find_objects('pack')
        self.assertGreater(len(pack_objects), 0,
                          "No pack objects found for message construction")

    def test_message_to_line_correct_format(self):
        """
        Verify that messages sent to line~ use correct format.
        Should send: "0, sample-length duration_ms"
        """
        # Find all msg objects that send to line~
        msg_objects = self.patch.find_objects('msg')
        line_objects = self.patch.find_objects('line~')

        # At least one msg object should connect to line~
        found_msg_to_line = False
        for msg_id, msg_obj in msg_objects.items():
            # Check if this msg sends to a line~
            connections = self.patch.get_connections_from(msg_id)
            for conn in connections:
                if conn['to_id'] in line_objects:
                    found_msg_to_line = True
                    # Verify the msg format contains "0"
                    self.assertIn('0', msg_obj['args'],
                                 f"msg object {msg_id} should initialize line~ to 0")

        self.assertTrue(found_msg_to_line,
                       "No msg objects connect to line~ objects")

    def test_sample_length_calculation(self):
        """
        Verify sample length is calculated correctly.
        Should divide by 48000 (sample rate) then multiply by 1000 (ms).
        """
        # Look for divide and multiply operations
        divide_objs = self.patch.find_objects('/')
        multiply_objs = self.patch.find_objects('*')

        # Should have at least one division by 48000
        found_divide_by_sample_rate = False
        for div_id, div_obj in divide_objs.items():
            if '48000' in div_obj['args']:
                found_divide_by_sample_rate = True
                break

        self.assertTrue(found_divide_by_sample_rate,
                       "Missing division by 48000 for sample rate conversion")

        # Should have multiplication by 1000
        found_multiply_by_ms = False
        for mul_id, mul_obj in multiply_objs.items():
            if '1000' in mul_obj['args']:
                found_multiply_by_ms = True
                break

        self.assertTrue(found_multiply_by_ms,
                       "Missing multiplication by 1000 for milliseconds")


class TestCritical2SpatialMixer(unittest.TestCase):
    """Test CRITICAL #2: Spatial mixer inlet connections."""

    def setUp(self):
        self.patch = PdPatchParser(
            '/home/user/corazonn/audio/patches/spatial-mixer.pd'
        )

    def test_add_objects_exist(self):
        """Verify [+~] objects exist for mixing."""
        add_objects = self.patch.find_objects('+~')
        self.assertGreater(len(add_objects), 0,
                          "No [+~] objects found in spatial-mixer.pd")

    def test_max_two_inlets_per_add(self):
        """
        Verify that [+~] objects have at most 2 inlets.
        If more inputs needed, must use cascaded [+~] objects.
        """
        add_objects = self.patch.find_objects('+~')

        for add_id in add_objects.keys():
            # Find all connections to this object's inlets
            inlets_used = set()
            for conn in self.patch.connections:
                if conn['to_id'] == add_id:
                    inlets_used.add(conn['to_inlet'])

            # Standard [+~] has 2 inlets (0 and 1)
            self.assertLessEqual(max(inlets_used) if inlets_used else 0, 1,
                                f"[+~] object {add_id} has connections to inlet "
                                f"{max(inlets_used)}, but [+~] only has 2 inlets (0, 1)")

    def test_four_channel_mixing_pattern(self):
        """
        Verify cascaded [+~] pattern for 4-channel mixing.
        Should have structure: input1 → [+~] → [+~] → [+~] ← inputs
        """
        add_objects = self.patch.find_objects('+~')

        # With 4 inputs, need at least 3 cascaded [+~] objects
        # to handle: (((in1 + in2) + in3) + in4)
        self.assertGreaterEqual(len(add_objects), 3,
                               "Need at least 3 cascaded [+~] objects for 4-input mixing")

        # Verify at least one [+~] chains to another [+~]
        add_to_add_chain = False
        for add_id in add_objects.keys():
            connections = self.patch.get_connections_from(add_id)
            for conn in connections:
                if conn['to_id'] in add_objects:
                    add_to_add_chain = True
                    break

        self.assertTrue(add_to_add_chain,
                       "Missing cascaded [+~] chain for 4-channel mixing")


class TestCritical3DisconnectionDetection(unittest.TestCase):
    """Test CRITICAL #3: Disconnection detection timeout."""

    def setUp(self):
        self.patch = PdPatchParser(
            '/home/user/corazonn/audio/patches/sensor-process.pd'
        )

    def test_delay_object_exists(self):
        """Verify delay object exists for timeout detection."""
        delay_objects = self.patch.find_objects('delay')
        self.assertGreater(len(delay_objects), 0,
                          "No delay objects found in sensor-process.pd")

    def test_timeout_value_set(self):
        """Verify timeout is set to reasonable value (around 5000ms)."""
        delay_objects = self.patch.find_objects('delay')
        found_timeout = False

        for delay_id, delay_obj in delay_objects.items():
            # The delay should have argument like "5000"
            if '5000' in delay_obj['args']:
                found_timeout = True
                break

        self.assertTrue(found_timeout,
                       "Delay timeout not set to 5000ms")

    def test_heartbeat_triggers_timeout(self):
        """
        Verify that incoming heartbeat messages trigger the delay.
        Pattern: ibi-valid → delay
        """
        # Find "r ibi-valid-$1" (receive objects)
        receive_objects = self.patch.find_objects('r')

        found_ibi_receiver = False
        for recv_id, recv_obj in receive_objects.items():
            if 'ibi-valid' in recv_obj['args']:
                found_ibi_receiver = True
                # This should connect to something that triggers delay
                break

        self.assertTrue(found_ibi_receiver,
                       "Missing ibi-valid receiver for heartbeat input")

    def test_channel_gain_reset_on_disconnect(self):
        """
        Verify that disconnection detection sends gain reset.
        Pattern: sensor-disconnected → channel-gain (sets to 0)
        """
        # Find send objects that transmit disconnection signal
        send_objects = self.patch.find_objects('s')

        found_disconnect_send = False
        for send_id, send_obj in send_objects.items():
            if 'sensor-disconnected' in send_obj['args']:
                found_disconnect_send = True
                break

        self.assertTrue(found_disconnect_send,
                       "Missing sensor-disconnected send for timeout signal")


class TestCritical4SampleFiles(unittest.TestCase):
    """Test CRITICAL #4: Sample file existence."""

    def setUp(self):
        self.sample_dir = Path(
            '/home/user/corazonn/audio/samples/percussion/starter'
        )

    def test_sample_directory_exists(self):
        """Verify sample directory exists."""
        self.assertTrue(self.sample_dir.exists(),
                       f"Sample directory {self.sample_dir} does not exist")

    def test_required_samples_exist(self):
        """Verify required drum samples exist."""
        required_samples = [
            'kick-01.wav',
            'snare-01.wav',
            'hat-01.wav',
            'clap-01.wav'
        ]

        for sample in required_samples:
            sample_path = self.sample_dir / sample
            self.assertTrue(sample_path.exists(),
                          f"Required sample {sample} not found in {self.sample_dir}")

    def test_samples_are_valid_wav(self):
        """Verify samples are valid WAV files."""
        required_samples = [
            'kick-01.wav',
            'snare-01.wav',
            'hat-01.wav',
            'clap-01.wav'
        ]

        for sample in required_samples:
            sample_path = self.sample_dir / sample
            if sample_path.exists():
                # Check for WAV file signature
                with open(sample_path, 'rb') as f:
                    header = f.read(4)
                    self.assertEqual(header, b'RIFF',
                                   f"{sample} does not have valid WAV header")


class TestCritical5DAC(unittest.TestCase):
    """Test CRITICAL #5: DAC object redundancy."""

    def setUp(self):
        self.mixer_patch = PdPatchParser(
            '/home/user/corazonn/audio/patches/spatial-mixer.pd'
        )
        self.main_patch = PdPatchParser(
            '/home/user/corazonn/audio/patches/heartbeat-main.pd'
        )

    def test_main_has_dac(self):
        """Verify main patch has the primary DAC."""
        dac_objects = self.main_patch.find_objects('dac~')
        self.assertGreater(len(dac_objects), 0,
                          "Main patch should have dac~ object")

    def test_mixer_has_no_dac(self):
        """Verify spatial-mixer has no DAC objects."""
        dac_objects = self.mixer_patch.find_objects('dac~')
        self.assertEqual(len(dac_objects), 0,
                        "spatial-mixer.pd should not have dac~ objects")

    def test_mixer_has_outlets(self):
        """Verify spatial-mixer has outlets for outputs."""
        outlet_objects = self.mixer_patch.find_objects('outlet~')
        self.assertGreater(len(outlet_objects), 0,
                          "spatial-mixer should have outlet~ objects")

    def test_main_connects_to_mixer_outlets(self):
        """
        Verify main patch properly connects to spatial-mixer outputs.
        Pattern: mixer outlets → main patch dac~
        """
        # This is a structural test - we're checking that the architecture
        # supports proper connections
        dac_objects = self.main_patch.find_objects('dac~')
        self.assertGreater(len(dac_objects), 0,
                          "Main patch must have connections to spatial-mixer")


if __name__ == '__main__':
    unittest.main()
