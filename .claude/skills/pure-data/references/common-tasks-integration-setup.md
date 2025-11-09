# Integration

Quick reference for declaring externals, paths, and audio setup in Pure Data.

## Declare Required Externals

At top of main patch:
```
[declare -lib mrpeach -lib cyclone]
```

## Declare Sample Path

At top of main patch:
```
[declare -path ../samples/percussion/starter]
```

**Relative to**: Patch file location in `audio/patches/`.

## Auto-Start DSP

```
[loadbang]
|
[; pd dsp 1(
```

**Manual**: Pd window → DSP toggle, or Media → Audio ON.

## Connect to Audio Output

```
[r~ mix-left]  [r~ mix-right]
|             |
[dac~ 1 2]
```

**Channels**: 1 = left, 2 = right.

---

**Related documentation**:
- See common-tasks-osc-networking.md for mrpeach library requirements
- See common-tasks-sample-playback.md for sample path declarations
- See common-tasks-creating-patches.md for patch structure
