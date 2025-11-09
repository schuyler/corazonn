# Project layout guide

This project layout is meant as a GUIDE. Do not follow it blindly. Use
filenames and directory names that make sense for the task you are doing.

```
corazonn/
│
├── README.md                          # Project overview, quick start
├── docs/                              # All design documents
│   ├── heartbeat-installation-prd.md
│   ├── heartbeat-firmware-design.md
│   ├── heartbeat-audio-output-design.md
│   ├── heartbeat-lighting-design.md
│   └── heartbeat-input-hardware-design.md
│
├── config/                            # Shared configuration
│   ├── network.yaml                   # WiFi, IPs, ports
│   ├── sensors.yaml                   # Sensor IDs, pin mappings
│   └── deployment.yaml                # Festival-specific settings
│
├── firmware/                          # ESP32 sensor code
│   ├── README.md
│   ├── platformio.ini                 # PlatformIO configuration
│   ├── src/
│   │   ├── main.cpp
│   │   ├── sensor_config.h
│   │   ├── pulse_detector.cpp/h
│   │   ├── osc_sender.cpp/h
│   │   └── wifi_manager.cpp/h
│   ├── test/
│   │   └── test_pulse_detection.cpp
│   └── scripts/
│       ├── flash_all.sh               # Program all 4 units
│       └── monitor.sh                 # Serial monitoring
│
├── audio/                             # Pure Data system
│   ├── README.md
│   ├── patches/
│   │   ├── heartbeat-main.pd
│   │   ├── subpatches/
│   │   │   ├── osc-input.pd
│   │   │   ├── sensor-process.pd
│   │   │   ├── sound-engine.pd
│   │   │   ├── spatial-mixer.pd
│   │   │   ├── effects-chain.pd
│   │   │   ├── midi-control.pd
│   │   │   └── lighting-output.pd
│   │   └── backup/
│   ├── samples/
│   │   ├── percussion/
│   │   ├── tonal/
│   │   ├── ambient/
│   │   └── oneshots/
│   ├── scripts/
│   │   ├── start-pd.sh                # Launch with correct settings
│   │   └── install-dependencies.sh
│   └── systemd/
│       └── heartbeat-audio.service
│
├── lighting/                          # Python lighting bridge
│   ├── README.md
│   ├── requirements.txt
│   ├── config.yaml
│   ├── src/
│   │   ├── main.py
│   │   ├── osc_receiver.py
│   │   ├── effect_engine.py
│   │   ├── wyze_client.py
│   │   └── modes.py
│   ├── tests/
│   │   ├── test_effects.py
│   │   ├── test_osc.py
│   │   └── mock_wyze.py
│   ├── scripts/
│   │   └── measure-latency.py
│   └── systemd/
│       └── heartbeat-lighting.service
│
├── testing/                           # Testing & simulation tools
│   ├── README.md
│   ├── fake_heartbeat.py              # Simulate 4 sensors sending OSC
│   ├── osc_monitor.py                 # Watch all OSC traffic
│   ├── sensor_simulator/              # Hardware-in-loop testing
│   │   ├── signal_generator.py        # Generate analog pulse waveforms
│   │   └── test_scenarios.yaml
│   └── integration/
│       ├── test_full_system.py
│       └── stress_test.py
│
├── deployment/                        # Installation scripts
│   ├── README.md
│   ├── raspberry-pi-setup.sh          # Initial Pi configuration
│   ├── install-all.sh                 # One-command deploy
│   ├── backup.sh                      # Backup configs/patches
│   └── restore.sh
│
└── tools/                             # Utilities
    ├── network-config.py              # WiFi router setup helper
    ├── bulb-discovery.py              # Find Wyze bulb MAC addresses
    └── launchpad-mapper.py            # Generate MIDI mappings
```
