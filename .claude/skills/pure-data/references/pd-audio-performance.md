# Pure Data Audio Performance

Reference material for performance optimization and block size control in Pure Data.

See also: [Fundamentals](pd-audio-fundamentals.md), [Routing](pd-audio-routing.md)

## Block Size Control

### switch~ and block~ Objects
- One per window (acts on entire window and subwindows)
- Subwindows may have nested `switch~/block~`
- Both take arguments: block size, optional overlap, up/downsample factors
- Example: `block~ 1024 4` = 1024 samples, 4x overlap relative to parent

### switch~ Specifics
- Can turn audio computation on/off
- Adds small computational overhead
- Switched-off outputs generate zeros (small overhead)
- Cheaper output method: `throw~` inside, `catch~` outside

### Block Size Effects

#### Larger Blocks (>64)
- Small increase in runtime efficiency
- `fft~` and related objects: block size = FFT channels
- Larger window for frequency analysis

#### Smaller Blocks (<64)
- Finer message/audio interaction resolution
- Reduced block delay in feedback algorithms
- Block size 1: Enables 1-sample feedback for custom DSP
- Can implement recursive filters, custom algorithms

### Switching Strategies
- Put algorithms in separate subpatches
- Switch off as you switch another on
- Beware of clicks: ramp `line~` to zero before switching off
- Will resume at stuck value when switched back on

## Audio Computation Control

### Global DSP Toggle
- DSP off by default
- Turn on: Computes audio for all open patches
- Turn off: Halts computation, releases audio devices
- Shortcuts: Ctrl+/ (on), Ctrl+. (off)

### Patch-Level Control
Send messages to "pd":
- `dsp 1`: Enable DSP
- `dsp 0`: Disable DSP

### Audio Settings
- Configure via command line or preferences dialog
- Sample rate (default 48000)
- Block size (default 64)
- Audio buffer size (via `-audiobuf` flag)
- Input/output device selection

## Computation and Performance

### Realtime Considerations
- Pd maintains computational lead (buffer ahead of real time)
- Gaps in I/O if Pd gets late
- Disk streaming remains correct (batch mode possible)
- GUI runs as separate process (can compete for CPU)
- Close unused windows to reduce load

### Batch Processing
- Use `-nogui` flag for non-interactive operation
- Use `-send` flag for sending initial messages
- Disk I/O objects work correctly regardless of real-time status

### Monitoring
- Audio input level: Media → Test Audio and MIDI
- Check for buffer under/overruns in console
- DSP load visible in some configurations
