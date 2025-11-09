#!/usr/bin/env python3
"""
Test-driven validation for sound-engine.pd connections.
Verifies that each audio channel (0-3) has correct connection chains.
"""

def parse_pd_connections(file_path):
    """Parse Pure Data file and extract connections."""
    connections = []
    with open(file_path, 'r') as f:
        for line in f:
            if line.startswith('#X connect'):
                parts = line.strip().split()
                # Format: #X connect FROM FROM_OUTLET TO TO_INLET;
                conn = {
                    'from_obj': int(parts[2]),
                    'from_outlet': int(parts[3]),
                    'to_obj': int(parts[4]),
                    'to_inlet': int(parts[5].rstrip(';')),
                }
                connections.append(conn)
    return connections


def define_expected_connections():
    """Define the expected connection pattern for all 4 channels."""

    # Channel 0 objects (objs 18-32)
    ch0 = {
        'r_valid': 18,      # r ibi-valid-0
        't_bf': 19,         # t b f
        'r_length': 20,     # r sample-0-length
        'div': 21,          # / 48000
        'mul': 22,          # * 1000
        'pack': 23,         # pack f f
        'msg': 24,          # msg 0, $1 $2
        'line': 25,         # line~
        'sig': 26,          # sig~
        'mul_audio': 27,    # *~
        'tabread': 28,      # tabread4~ sample-0
        's_out': 32,        # s audio-out-0
    }

    # Channel 1 objects (objs 33-44)
    ch1 = {
        'r_valid': 33,      # r ibi-valid-1
        't_bf': 34,         # t b f
        'r_length': 35,     # r sample-1-length
        'div': 36,          # / 48000
        'mul': 37,          # * 1000
        'pack': 38,         # pack f f
        'msg': 39,          # msg 170 400 0, $1 $2
        'line': 40,         # line~
        'sig': 41,          # sig~
        'mul_audio': 42,    # *~
        'tabread': 43,      # tabread4~ sample-1
        's_out': 44,        # s audio-out-1
    }

    # Channel 2 objects (objs 45-56)
    ch2 = {
        'r_valid': 45,      # r ibi-valid-2
        't_bf': 46,         # t b f
        'r_length': 47,     # r sample-2-length
        'div': 48,          # / 48000
        'mul': 49,          # * 1000
        'pack': 50,         # pack f f
        'msg': 51,          # msg 320 400 0, $1 $2
        'line': 52,         # line~
        'sig': 53,          # sig~
        'mul_audio': 54,    # *~
        'tabread': 55,      # tabread4~ sample-2
        's_out': 56,        # s audio-out-2
    }

    # Channel 3 objects (objs 57-68)
    ch3 = {
        'r_valid': 57,      # r ibi-valid-3
        't_bf': 58,         # t b f
        'r_length': 59,     # r sample-3-length
        'div': 60,          # / 48000
        'mul': 61,          # * 1000
        'pack': 62,         # pack f f
        'msg': 63,          # msg 470 400 0, $1 $2
        'line': 64,         # line~
        'sig': 65,          # sig~
        'mul_audio': 66,    # *~
        'tabread': 67,      # tabread4~ sample-3
        's_out': 68,        # s audio-out-3
    }

    def channel_connections(ch_name, ch):
        """Generate expected connections for a channel."""
        return [
            # r ibi-valid → t b f
            {'from': ch['r_valid'], 'f_out': 0, 'to': ch['t_bf'], 't_in': 0},
            # t b f outlet 0 → r sample-length
            {'from': ch['t_bf'], 'f_out': 0, 'to': ch['r_length'], 't_in': 0},
            # r sample-length → / 48000
            {'from': ch['r_length'], 'f_out': 0, 'to': ch['div'], 't_in': 0},
            # / 48000 → * 1000
            {'from': ch['div'], 'f_out': 0, 'to': ch['mul'], 't_in': 0},
            # r sample-length → pack (first input)
            {'from': ch['r_length'], 'f_out': 0, 'to': ch['pack'], 't_in': 0},
            # * 1000 → pack (second input)
            {'from': ch['mul'], 'f_out': 0, 'to': ch['pack'], 't_in': 1},
            # pack → msg
            {'from': ch['pack'], 'f_out': 0, 'to': ch['msg'], 't_in': 0},
            # pack outlet 1 → *~ inlet 1
            {'from': ch['pack'], 'f_out': 1, 'to': ch['mul_audio'], 't_in': 1},
            # msg → line~
            {'from': ch['msg'], 'f_out': 0, 'to': ch['line'], 't_in': 0},
            # line~ → sig~
            {'from': ch['line'], 'f_out': 0, 'to': ch['sig'], 't_in': 0},
            # sig~ → *~
            {'from': ch['sig'], 'f_out': 0, 'to': ch['mul_audio'], 't_in': 0},
            # *~ → tabread4~
            {'from': ch['mul_audio'], 'f_out': 0, 'to': ch['tabread'], 't_in': 0},
            # tabread4~ → s audio-out
            {'from': ch['tabread'], 'f_out': 0, 'to': ch['s_out'], 't_in': 0},
        ]

    expected = {}
    expected['ch0'] = channel_connections('ch0', ch0)
    expected['ch1'] = channel_connections('ch1', ch1)
    expected['ch2'] = channel_connections('ch2', ch2)
    expected['ch3'] = channel_connections('ch3', ch3)

    return expected


def test_channel_connections():
    """Test that all 4 channels have correct connections."""
    connections = parse_pd_connections('/home/user/corazonn/audio/patches/sound-engine.pd')
    expected = define_expected_connections()

    # Convert connections to a set for easy lookup
    actual = set()
    for conn in connections:
        key = (conn['from_obj'], conn['from_outlet'], conn['to_obj'], conn['to_inlet'])
        actual.add(key)

    # Check each channel
    all_passed = True
    for ch_name, ch_expected in expected.items():
        print(f"\nValidating {ch_name}:")
        for exp in ch_expected:
            key = (exp['from'], exp['f_out'], exp['to'], exp['t_in'])
            if key in actual:
                print(f"  ✓ {exp['from']} → {exp['to']} (OK)")
            else:
                print(f"  ✗ {exp['from']} → {exp['to']} (MISSING)")
                all_passed = False

    # Check for connections that shouldn't exist
    print("\nChecking for incorrect connections...")
    all_expected_keys = set()
    for ch_expected in expected.values():
        for exp in ch_expected:
            key = (exp['from'], exp['f_out'], exp['to'], exp['t_in'])
            all_expected_keys.add(key)

    extra_conns = actual - all_expected_keys
    if extra_conns:
        print(f"Found {len(extra_conns)} unexpected connections:")
        for conn in sorted(extra_conns):
            print(f"  Extra: {conn[0]} → {conn[2]}")
        all_passed = False
    else:
        print("  No extra connections found (Good!)")

    if all_passed:
        print("\n✓ All tests PASSED!")
        return True
    else:
        print("\n✗ Tests FAILED - connections need fixing")
        return False


if __name__ == '__main__':
    import sys
    success = test_channel_connections()
    sys.exit(0 if success else 1)
