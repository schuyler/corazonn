# Audio Design Document vs Phase 1 TRD Comparison

**Date:** 2025-11-09
**Purpose:** Reconcile differences between original design.md and phase1-trd.md

---

## Executive Summary

The **design.md** represents a comprehensive, production-ready audio system with multiple modes, MIDI control, and advanced features. The **phase1-trd.md** is a focused MVP implementation for Phase 1, deferring advanced features to later phases.

**Key Philosophy Difference:**
- **Design.md**: Full-featured, production-ready system
- **Phase 1 TRD**: Incremental, test-driven development approach (MVP first)

---

## Critical Technical Differences

### 1. OSC Reception Objects

| Aspect | Design.md | Phase 1 TRD | Recommendation |
|--------|-----------|-------------|----------------|
| **Objects** | `[netreceive]` + `[oscparse]` | `[udpreceive]` + `[unpackOSC]` | **Use TRD approach** |
| **Library** | Built-in Pd objects | mrpeach external library | mrpeach is standard |
| **Location** | Lines 83-84, 1136-1143 | Lines 355-358, R17 | |

**Rationale for TRD approach:**
- mrpeach is the de facto standard for OSC in Pure Data
- More reliable and better maintained
- Already specified as dependency (R44)

**Action:** Design.md should be updated to use mrpeach library for consistency.

---

### 2. Sample Playback Method

| Aspect | Design.md | Phase 1 TRD | Recommendation |
|--------|-----------|-------------|----------------|
| **Method** | `[readsf~]` streaming | `[soundfiler]` + `[tabread4~]` table-based | **Use TRD approach for Phase 1** |
| **Memory** | Disk streaming | Pre-loaded into RAM | |
| **Latency** | Variable (disk I/O) | Deterministic (RAM) | |
| **Location** | Lines 102, 229, 1177 | Lines 407-439, R21-R22 | |

**Rationale for TRD approach:**
- Short percussion samples (0.5-2s) fit easily in RAM
- Eliminates disk I/O latency
- More reliable for real-time triggering
- Automatic restart on each heartbeat

**Design.md use case for `[readsf~]`:**
- Better for longer ambient samples (10-30s)
- Relevant for Phase 2+ ambient mode

**Action:** Keep TRD approach for Phase 1 percussion. Consider `[readsf~]` for Phase 2 ambient mode.

---

### 3. Directory Structure

| Aspect | Design.md | Phase 1 TRD | Recommendation |
|--------|-----------|-------------|----------------|
| **Base path** | `/home/pi/heartbeat/` | `$REPO_ROOT/audio/` | **Use TRD structure** |
| **Subpatches** | `pd-subpatches/` | `patches/` | |
| **Samples** | `samples/` (same level) | `samples/` (same level) | ✓ Consistent |
| **Location** | Lines 605-635 | Lines 806-834 | |

**Rationale for TRD approach:**
- Aligns with project structure (docs/firmware pattern)
- Version control friendly
- Portable across development machines

**Design.md assumption:**
- Production deployment path on Raspberry Pi
- Makes sense for systemd service configuration

**Action:** Use TRD structure for development. Document production deployment path separately (systemd configuration can reference repo or install location).

---

### 4. Launchpad MIDI Control

| Aspect | Design.md | Phase 1 TRD | Recommendation |
|--------|-----------|-------------|----------------|
| **Status** | Core feature | Deferred to Phase 3 | **TRD phasing is correct** |
| **Coverage** | 357 lines (lines 20-23, 357-431) | 1 line (known limitation) | |
| **Complexity** | Mode switching, quantization, LED feedback | Not implemented | |

**Rationale for TRD deferral:**
- Launchpad not required to test core OSC → audio pipeline
- Adds significant complexity (MIDI, LED control, state management)
- Can develop and test without hardware dependency

**Design.md value:**
- Comprehensive specification ready for Phase 3 implementation
- Well-thought-out control mapping

**Action:** Keep Launchpad in Phase 3. Use design.md Section "Launchpad Control Mapping" as specification when implementing.

---

### 5. Effects Processing (Reverb, Limiting, EQ)

| Aspect | Design.md | Phase 1 TRD | Recommendation |
|--------|-----------|-------------|----------------|
| **Status** | Core feature | Deferred to Phase 2 | **TRD phasing is correct for MVP** |
| **Reverb** | `[freeverb~]` with parameters | "No reverb or effects" | |
| **Limiting** | `[clip~]` + smoothing | Not mentioned | Consider for Phase 1 |
| **Location** | Lines 114-117, 481-527 | Line 628 (limitation) | |

**Rationale for TRD deferral:**
- Core pipeline (OSC → sample trigger → stereo out) can be tested without effects
- Simplifies Phase 1 debugging

**Important consideration:**
- **Limiting is safety-critical** when 4 sensors trigger simultaneously
- Risk of clipping without limiting

**Recommendation:**
- **Add simple limiting to Phase 1 TRD** for safety:
  ```
  [clip~ -0.95 0.95]  # Prevent clipping
  ```
- Defer sophisticated reverb/EQ to Phase 2
- Update TRD R25 (master output) to include basic limiting

**Action:** Add Section 6.5.1 "Master Limiter" to TRD with simple `[clip~]` object.

---

### 6. Multiple Sound Modes

| Aspect | Design.md | Phase 1 TRD | Recommendation |
|--------|-----------|-------------|----------------|
| **Modes** | 4 (Percussion, Tonal, Ambient, Breathing) | 1 (Percussion only) | **TRD phasing correct** |
| **Coverage** | 87 lines (lines 217-303) | Single mode | |
| **Scope** | Production-ready variety | MVP validation | |

**Rationale for TRD single mode:**
- Percussion mode sufficient to validate core architecture
- Each mode requires different sound engine implementation
- Incremental development reduces complexity

**Design.md modes map to phases:**
- Phase 1: Percussion ✓ (TRD)
- Phase 2: Add reverb, sample variety → richer percussion
- Phase 3: Tonal/harmonic synthesis
- Phase 4: Ambient soundscapes
- Phase 5: Breathing pattern detection

**Action:** Keep Phase 1 as percussion-only. Use design.md modes as roadmap for Phases 3-5.

---

### 7. Lighting Bridge Integration

| Aspect | Design.md | Phase 1 TRD | Recommendation |
|--------|-----------|-------------|----------------|
| **Status** | Not mentioned | Core feature (OSC output port 8001) | **TRD integration correct** |
| **OSC Output** | None | `/light/N/pulse` messages | |
| **Location** | N/A | Lines 311-329, 515-553, R11-R13, R26-R27 | |

**Key difference:**
- Design.md is audio-only system
- TRD integrates with existing lighting bridge (from lighting TRD)

**Rationale for TRD integration:**
- Project has parallel lighting system development
- Audio and lighting synchronized via heartbeats
- Holistic experience

**Action:** Update design.md to include lighting bridge integration section. This is a valuable addition not in original design.

---

### 8. Disconnection/Reconnection Handling

| Aspect | Design.md | Phase 1 TRD | Recommendation |
|--------|-----------|-------------|----------------|
| **Status** | Specified (5-sec timeout, fade-out) | Not mentioned | **Add to Phase 1 TRD** |
| **Detection** | `current_time - last_message_time > 5000ms` | None | |
| **Behavior** | Fade-out/fade-in on disconnect/reconnect | None | |
| **Location** | Lines 181-196 | Not present | |

**Rationale for including in Phase 1:**
- **This is essential for robustness** during testing
- Sensors frequently disconnect in development
- Without timeout, stale channels continue playing

**Action:** Add to Phase 1 TRD as new requirement:
- **R55**: Detect sensor disconnection (no message for 5 seconds)
- **R56**: Fade out disconnected channel over 2 seconds
- **R57**: Fade in reconnected channel over 1 second

---

### 9. Envelope Complexity

| Aspect | Design.md | Phase 1 TRD | Recommendation |
|--------|-----------|-------------|----------------|
| **Design** | Simple fade-in `[0, 1 50(` | ASR envelope `[1 5, 1 40, 0 5(` | **TRD is better** |
| **Attack** | 50ms linear | 5ms attack | |
| **Sustain** | N/A | 40ms sustain | |
| **Release** | N/A | 5ms release | |
| **Location** | Lines 231, 1173 | Line 403 (R22) | |

**Rationale for TRD approach:**
- ASR envelope prevents clicks and provides natural decay
- Short attack (5ms) maintains punch
- Short release (5ms) prevents cutoff artifacts

**Action:** Keep TRD envelope. Update design.md to match.

---

### 10. Testing Infrastructure

| Aspect | Design.md | Phase 1 TRD | Recommendation |
|--------|-----------|-------------|----------------|
| **Script name** | `fake_heartbeat.py` | `test-osc-sender.py` | **Functionally equivalent** |
| **Spec detail** | Full Python code (lines 682-697) | Requirements R33-R40 | |
| **Test coverage** | 13 numbered tests (lines 676-791) | Basic validation points | |

**Difference in approach:**
- Design.md: Provides complete implementation code
- TRD: Provides requirements, lets implementation vary

**Both are valid.**

**Action:**
- Use TRD requirements (R33-R40) for test-osc-sender.py implementation
- Reference design.md test procedures for comprehensive validation (Tests 1-13)
- Add link to design.md tests in TRD Section 7.3

---

### 11. Production Deployment Features

| Aspect | Design.md | Phase 1 TRD | Recommendation |
|--------|-----------|-------------|----------------|
| **systemd service** | Fully specified (lines 567-582, 843-858) | Mentioned, deferred | **Design.md for production** |
| **Watchdog** | Configured (lines 824-840) | Not mentioned | Production feature |
| **Backup strategies** | Detailed (lines 793-882) | Not mentioned | Production feature |
| **QoS/networking** | WiFi optimization (lines 936-944) | Basic topology only | Production feature |

**Clear division:**
- Design.md = production deployment guide
- TRD = Phase 1 development specification

**Action:** Keep separate. When deploying to production (festival), reference design.md deployment sections (systemd, watchdog, backup).

---

## Scope Reconciliation

### Features by Phase (Proposed)

| Feature | Design.md | Phase 1 TRD | Proposed Reconciliation |
|---------|-----------|-------------|------------------------|
| **Core OSC → Audio** | ✓ | ✓ | Phase 1 (current) |
| **Percussion mode** | ✓ | ✓ | Phase 1 (current) |
| **Table-based samples** | ✗ (uses readsf~) | ✓ | Phase 1 (TRD correct) |
| **Lighting bridge OSC** | ✗ | ✓ | Phase 1 (valuable addition) |
| **Disconnection handling** | ✓ | ✗ | **Add to Phase 1** |
| **Basic limiting** | ✓ | ✗ | **Add to Phase 1** |
| **Relative paths** | ✗ | ✓ | Phase 1 (TRD correct) |
| **Reverb/effects** | ✓ | Phase 2 | Phase 2 |
| **Sample banks** | ✓ | Phase 2 | Phase 2 |
| **Tonal/harmonic mode** | ✓ | Phase 3 | Phase 3 |
| **Ambient mode** | ✓ | Phase 3 | Phase 3-4 |
| **Breathing mode** | ✓ | Not planned | Phase 4-5 |
| **Launchpad MIDI** | ✓ | Phase 3 | Phase 3 |
| **Quantization** | ✓ | Not planned | Phase 3 (with Launchpad) |
| **systemd/production** | ✓ | Not planned | Post-Phase 3 (deployment) |

---

## Recommended Actions

### 1. Update Phase 1 TRD (Additions)

Add these from design.md:

**New Section 6.5.1: Master Limiter**
```markdown
**R25a: Prevent clipping with simple limiter**

[r mix-left]  [r mix-right]
|             |
[clip~ -0.95 0.95]  # Hard limit to prevent clipping
|             |
[dac~ 1 2]
```

**New Requirements (Disconnection Handling):**
```markdown
**R55: Detect sensor disconnection**
- IF no message received for 5000ms THEN sensor_connected[N] = false

**R56: Fade out disconnected channel**
- When disconnection detected, fade volume to 0 over 2000ms
- Use [line~] for fade

**R57: Fade in reconnected channel**
- When first message after disconnection, fade volume to 1.0 over 1000ms
```

### 2. Update design.md (Corrections)

**Replace OSC objects:**
- Change `[netreceive]` + `[oscparse]` → `[udpreceive]` + `[unpackOSC]`
- Update code snippets (lines 83-84, 1136-1143)

**Add lighting bridge section:**
```markdown
### Lighting System Integration

**OSC Output:**
- Address: `/light/N/pulse <int32>ibi_ms`
- Port: 8001 (UDP)
- Destination: 127.0.0.1 (Python lighting bridge)
- Behavior: Forward heartbeat messages immediately
```

**Update sample playback for short percussion:**
```markdown
**For percussion samples (<2 seconds):**
Use table-based playback (faster, more reliable):
[soundfiler] + [tabread4~]

**For ambient samples (>10 seconds):**
Use streaming playback (memory-efficient):
[readsf~]
```

### 3. Cross-Reference Documents

**In Phase 1 TRD:**
Add references to design.md:
```markdown
## 12. Next Steps (Phase 2 Preview)

**Full system design:** See `docs/audio/reference/design.md` for:
- Tonal/harmonic synthesis modes
- Ambient soundscape generation
- Breathing pattern sonification
- Launchpad MIDI control mapping
- Production deployment guide (systemd, watchdog, backup)
```

**In design.md:**
Add references to TRD:
```markdown
## Implementation Status

**Phase 1 (Current):** See `docs/audio/reference/phase1-trd.md`
- Basic percussion mode
- OSC reception and validation
- Stereo panning
- Lighting bridge integration

**Phase 2+ (Future):** This document describes the full vision
```

### 4. Create Phase Roadmap Document

**New file:** `docs/audio/reference/phase-roadmap.md`

Map design.md features to implementation phases:
- Phase 1: Core OSC → Percussion → Lighting (TRD v1.2)
- Phase 2: Reverb, sample banks, variety
- Phase 3: Launchpad MIDI, tonal mode, quantization
- Phase 4: Ambient mode, breathing detection
- Phase 5: Production deployment (systemd, monitoring, backup)

---

## Conclusion

**Both documents are valuable:**
- **design.md**: Comprehensive vision, production-ready features
- **phase1-trd.md**: Focused MVP, incremental approach

**Recommendation:**
1. Keep both documents
2. Update Phase 1 TRD with disconnection handling + basic limiting
3. Update design.md with OSC library corrections and lighting integration
4. Create phase-roadmap.md to show progression
5. Cross-reference between documents

**Net result:** Clear development path from MVP (TRD) to full system (design.md).
