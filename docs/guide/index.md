# Amor Configuration Guide

Reference manual for configuring the Amor biofeedback system.

## Contents

- **[Audio Configuration](audio.md)** - Sample mapping, loops, and audio effects
- **[Freesound Sample Library](freesound.md)** - Download and manage audio samples from Freesound.org
- **[Launchpad Control](launchpad.md)** - Novation Launchpad button mappings and control modes
- **[Lighting Configuration](lighting.md)** - Zone assignments, bulb setup, and lighting effects
- **[Firmware Configuration](firmware.md)** - ESP32 sensor unit configuration
- **[Constants Reference](constants.md)** - Tunable constants and port assignments

## Quick Start

### Installation

```bash
# Install with audio support
pip install -e ".[audio]"

# Install with Freesound sample library tools
pip install -e ".[freesound]"

# Install with lighting support
pip install -e ".[lighting]"

# Install development tools
pip install -e ".[dev]"
```

### Required Configuration Files

| File | Location | Purpose |
|------|----------|---------|
| `samples.yaml` | `amor/config/` | Audio sample and effects configuration |
| `lighting.yaml` | `amor/config/` | Smart bulb and lighting effects configuration |
| `config.h` | `firmware/amor/include/` | ESP32 firmware configuration (copy from `config.h.example`) |

### Running the System

```bash
# Audio engine
python -m amor.audio

# Lighting engine
python -m amor.lighting

# Sequencer (Launchpad controller)
python -m amor.sequencer
```

All configuration is loaded at startup. Changes require process restart.
